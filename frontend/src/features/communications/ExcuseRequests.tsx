import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ParentExcuseRequests({ studentId }: { studentId: string }) {
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const canSend = useAuthStore((state) => state.can("parent.send_excuse"));
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get<ApiResponse<DataRecord[]>>(`/parent/child/${studentId}/excuse-requests`);
      setRows(response.data.data || []);
      setError("");
    } catch (err) { setError(apiMessage(err)); }
    finally { setLoading(false); }
  }, [studentId]);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    setError("");
    try {
      await api.post(`/parent/child/${studentId}/excuse-request`, Object.fromEntries(form.entries()));
      formElement.reset();
      await load();
    } catch (err) { setError(apiMessage(err)); }
    finally { setBusy(false); }
  }
  return <section className="card card-pad" style={{ marginBottom: 20 }} aria-label="Mazeret talepleri">
    <h2>Mazeret talepleri</h2>
    {canSend && <form onSubmit={submit} style={{ display: "grid", gap: 12, margin: "16px 0" }}>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <label>Başlangıç tarihi<input className="filter-select" style={{ width: "100%" }} type="date" name="start_date" required /></label>
        <label>Bitiş tarihi<input className="filter-select" style={{ width: "100%" }} type="date" name="end_date" required /></label>
        <label>Mazeret türü<select className="filter-select" style={{ width: "100%" }} name="reason_type"><option value="ILLNESS">Hastalık</option><option value="FAMILY">Ailevi neden</option><option value="TRAVEL">Seyahat</option><option value="OTHER">Diğer</option></select></label>
      </div>
      <label>Mazeret açıklaması<textarea name="description" className="filter-select" style={{ display: "block", width: "100%" }} required maxLength={2000} /></label>
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Gönderiliyor…" : "Mazeret talebi gönder"}</button>
    </form>}
    {error && <ErrorState message={error} retry={load} />}
    {loading ? <LoadingState /> : rows.length === 0 ? <p>Henüz mazeret talebi bulunmuyor.</p> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Tarih</th><th>Açıklama</th><th>Durum</th><th>Okul yanıtı</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{shortDate(row.start_date)} – {shortDate(row.end_date)}</td><td>{String(row.description)}</td><td><Badge value={String(row.status)} /></td><td>{String(row.review_comment || "—")}</td></tr>)}</tbody></table></div>}
  </section>;
}

export function ExcuseReviewPanel() {
  const sequence = useRef(0);
  const [branches, setBranches] = useState<DataRecord[]>([]);
  const [branchId, setBranchId] = useState("");
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const load = useCallback(async () => {
    const request = ++sequence.current;
    if (!branchId) return;
    try {
      const result = await api.get("/dashboard/pending-actions", { params: { branch_id: branchId } });
      if (request !== sequence.current) return;
      setRows(result.data.data.excuse_requests.items);
      setCount(result.data.data.excuse_requests.count);
      setError("");
    } catch (err) { if (request === sequence.current) setError(apiMessage(err)); }
  }, [branchId]);
  useEffect(() => {
    let active = true;
    api.get("/branches", { params: { page: 1, page_size: 100 } }).then((response) => {
      if (!active) return;
      const value = response.data.data;
      const items = Array.isArray(value) ? value : value?.items || [];
      setBranches(items);
      setBranchId(items[0]?.id || "");
    }).catch((err) => { if (active) setError(apiMessage(err)); });
    return () => { active = false; };
  }, []);
  useEffect(() => { setRows([]); setCount(0); void load(); return () => { ++sequence.current; }; }, [load]);
  async function review(id: string, status: "APPROVED" | "REJECTED") {
    setBusy(id);
    try {
      await api.put(`/dashboard/excuse-requests/${id}`, { status });
      await load();
    } catch (err) { setError(apiMessage(err)); }
    finally { setBusy(""); }
  }
  return <section className="card card-pad" style={{ marginBottom: 20 }} aria-label="Bekleyen mazeret talepleri">
    <div className="toolbar" style={{ justifyContent: "space-between", flexWrap: "wrap" }}><h2>Bekleyen mazeret talepleri ({count})</h2><select aria-label="Mazeret şubesi" className="filter-select" value={branchId} disabled={Boolean(busy)} onChange={(event) => setBranchId(event.target.value)}><option value="">Şube seçin</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{String(branch.name)}</option>)}</select></div>
    {error && <ErrorState message={error} retry={load} />}
    {!rows.length ? <p>Bekleyen mazeret talebi bulunmuyor.</p> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Öğrenci</th><th>Tarih</th><th>Açıklama</th><th>İşlem</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{String(row.student_name)}</td><td>{shortDate(row.start_date)} – {shortDate(row.end_date)}</td><td>{String(row.description)}</td><td><div className="table-actions"><button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => review(row.id, "APPROVED")}>Onayla</button><button className="btn btn-secondary" disabled={Boolean(busy)} onClick={() => review(row.id, "REJECTED")}>Reddet</button></div></td></tr>)}</tbody></table></div>}
  </section>;
}

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
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
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const institution = user?.is_super_admin ? (workspace?.operatorId === user.id ? workspace.id : null) : user?.organization_id;
  if (!user || user.is_super_admin && !institution || !["students.write", "branch.read", "dashboard.view"].every((code) => hasPermission(user, code))) return null;
  return <ScopedExcuseReviewPanel key={JSON.stringify([session, user.id, institution, user.branch_ids])} actorId={user.id} />;
}

type PendingExcuses = { count: number; items: DataRecord[] };
type ReviewResult = { key: string; data: PendingExcuses } | { key: string; error: string };

function ScopedExcuseReviewPanel({ actorId }: { actorId: string }) {
  const [branches, setBranches] = useState<DataRecord[] | null>(null);
  const [branchError, setBranchError] = useState("");
  const [branchAttempt, setBranchAttempt] = useState(0);
  const [branchId, setBranchId] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const pending = useRef<AbortController | null>(null);
  const [reviewing, setReviewing] = useState<{ branchId: string; controller: AbortController } | null>(null);
  const [feedback, setFeedback] = useState<{ branchId: string; text: string; error: boolean } | null>(null);
  const busy = reviewing?.branchId === branchId && !reviewing.controller.signal.aborted;
  const key = JSON.stringify([branchId, attempt]);
  const current = result?.key === key ? result : null;
  const data = current && "data" in current ? current.data : null;
  useLayoutEffect(() => () => {
    pending.current?.abort();
    pending.current = null;
  }, [branchId]);
  useEffect(() => {
    const controller = new AbortController();
    api.get("/branches", { params: { page: 1, page_size: 100 }, signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return;
      const items: DataRecord[] | undefined = Array.isArray(response.data.data) ? response.data.data : response.data.data?.items;
      if (!Array.isArray(items)) {
        setBranchError("Şube listesi doğrulanamadı.");
        return;
      }
      setBranches(items);
      setBranchId(items[0]?.id || "");
    }).catch((err) => { if (!controller.signal.aborted) setBranchError(apiMessage(err)); });
    return () => controller.abort();
  }, [branchAttempt]);
  useEffect(() => {
    if (!branchId) return;
    const controller = new AbortController();
    api.get<ApiResponse<{ branch_id: string; excuse_requests: PendingExcuses }>>("/dashboard/pending-actions", {
      params: { branch_id: branchId }, signal: controller.signal,
    }).then(({ data: { data: response } }) => {
      if (controller.signal.aborted) return;
      const rows = response?.excuse_requests;
      if (response?.branch_id !== branchId || !rows || !Array.isArray(rows.items) || !Number.isInteger(rows.count) ||
        rows.count < rows.items.length || rows.items.some((row) => !row?.id || !row.student_id || row.status !== "PENDING")) {
        setResult({ key, error: "Bekleyen mazeretler seçili şubeyle eşleşmiyor." });
        return;
      }
      setResult({ key, data: rows });
    }).catch((err) => { if (!controller.signal.aborted) setResult({ key, error: apiMessage(err) }); });
    return () => controller.abort();
  }, [branchId, key]);
  async function review(event: FormEvent<HTMLFormElement>, row: DataRecord, status: "APPROVED" | "REJECTED") {
    event.preventDefault();
    if (pending.current) return;
    const comment = String(new FormData(event.currentTarget).get("comment") ?? "").trim() || null;
    const controller = new AbortController();
    pending.current = controller;
    setReviewing({ branchId, controller });
    setFeedback(null);
    try {
      const response = await api.put<ApiResponse<DataRecord>>(`/dashboard/excuse-requests/${encodeURIComponent(row.id)}`,
        { status, comment }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      const saved = response.data.data;
      if (saved?.id !== row.id || saved.student_id !== row.student_id || saved.status !== status ||
        saved.reviewed_by !== actorId || saved.review_comment !== comment) {
        setFeedback({ branchId, text: "Sunucu yanıtı seçili mazeret veya karar bilgileriyle eşleşmiyor.", error: true });
        return;
      }
      setFeedback({ branchId, text: "Mazeret kararı kaydedildi.", error: false });
      setAttempt((value) => value + 1);
    } catch (err) {
      if (!controller.signal.aborted) {
        if (isAxiosError(err) && err.response?.status === 409) {
          setFeedback({ branchId, text: "Talep daha önce değerlendirilmiş. Liste yeniden okunuyor.", error: true });
          setAttempt((value) => value + 1);
        } else {
          setFeedback({ branchId, text: apiMessage(err), error: true });
        }
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setReviewing(null);
      }
    }
  }
  return <section className="card card-pad" style={{ marginBottom: 20 }} aria-label="Bekleyen mazeret talepleri">
    <div className="toolbar" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
      <h2>Bekleyen mazeret talepleri{data ? ` (${data.count})` : ""}</h2>
      <select aria-label="Mazeret şubesi" className="filter-select" value={branchId} disabled={!branches || busy} onChange={(event) => {
        setFeedback(null);
        setBranchId(event.target.value);
      }}><option value="">Şube seçin</option>{branches?.map((branch) => <option key={branch.id} value={branch.id}>{String(branch.name)}</option>)}</select>
    </div>
    {feedback?.branchId === branchId && <p role={feedback.error ? "alert" : "status"}>{feedback.text}</p>}
    {branchError ? <ErrorState message={branchError} retry={() => { setBranchError(""); setBranchAttempt((value) => value + 1); }} /> :
      !branches ? <LoadingState label="Şubeler yükleniyor" /> : !branchId ? <p>Mazeretleri görmek için bir şube seçin.</p> :
        current && "error" in current ? <ErrorState message={current.error} retry={() => setAttempt((value) => value + 1)} /> :
          !data ? <LoadingState label="Mazeret talepleri yükleniyor" /> : data.items.length === 0 ? <p>Bekleyen mazeret talebi bulunmuyor.</p> :
            <div className="table-wrap"><table className="data-table"><thead><tr><th>Öğrenci</th><th>Tarih</th><th>Açıklama</th><th>İşlem</th></tr></thead>
              <tbody>{data.items.map((row) => <tr key={row.id}><td>{String(row.student_name)}</td><td>{shortDate(row.start_date)} – {shortDate(row.end_date)}</td><td>{String(row.description)}</td>
                <td><form aria-label={`Mazeret kararı ${row.student_name}`} onSubmit={(event) => {
                  const choice = (event.nativeEvent as SubmitEvent).submitter?.getAttribute("value");
                  if (choice === "APPROVED" || choice === "REJECTED") void review(event, row, choice);
                  else event.preventDefault();
                }}><fieldset disabled={busy} style={{ border: 0, padding: 0 }}>
                  <label>Değerlendirme notu<textarea className="filter-select" name="comment" maxLength={2000} /></label>
                  <div className="table-actions"><button className="btn btn-primary" value="APPROVED">Onayla</button><button className="btn btn-secondary" value="REJECTED">Reddet</button></div>
                </fieldset></form></td></tr>)}</tbody>
            </table></div>}
  </section>;
}

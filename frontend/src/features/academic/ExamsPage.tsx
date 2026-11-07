import { useEffect, useState } from "react";
import { Award, Plus } from "lucide-react";
import { Badge, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { getAnalysis } from "../../lib/analysis";
import { api, apiMessage } from "../../lib/api";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import { hasPermission } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { ExamEditor } from "./ExamEditor";
import { ExamGrades } from "./ExamGrades";

export function ExamsPage() {
  const viewer = useWorkspaceUser(), writable = hasPermission(viewer, "exam.write");
  const [list, setList] = useState<Paginated<DataRecord> | null>(null), [loading, setLoading] = useState(true);
  const [error, setError] = useState(""), [actionError, setActionError] = useState(""), [message, setMessage] = useState("");
  const [page, setPage] = useState(1), [search, setSearch] = useState(""), [status, setStatus] = useState("");
  const [revision, setRevision] = useState(0), [selected, setSelected] = useState<DataRecord | null>(null);
  const [editor, setEditor] = useState<{ exam: DataRecord | null } | null>(null), [cancelling, setCancelling] = useState<DataRecord | null>(null);
  const [busy, setBusy] = useState(false), [summary, setSummary] = useState<DataRecord | null>(null), [summaryError, setSummaryError] = useState("");
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get<ApiResponse<Paginated<DataRecord>>>("/exams", { params: { page, page_size: 25, search: search || undefined, status: status || undefined }, signal: controller.signal })
      .then((reply) => { if (!controller.signal.aborted) setList(reply.data.data); })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, search, status, revision]);
  useEffect(() => {
    const controller = new AbortController(); setSummary(null); setSummaryError("");
    getAnalysis("/ai/academic-performance", { signal: controller.signal }).then((reply) => { if (!controller.signal.aborted) setSummary(reply.data.data); })
      .catch(() => { if (!controller.signal.aborted) setSummaryError("Akademik özet şu anda alınamadı."); });
    return () => controller.abort();
  }, [revision]);
  async function cancel() {
    if (!cancelling || busy) return; setBusy(true); setActionError(""); setMessage("");
    try {
      await api.delete(`/exams/${cancelling.id}`);
      if (selected?.id === cancelling.id) setSelected({ ...selected, status: "CANCELLED" });
      setCancelling(null); setMessage("Sınav iptal edildi. Not geçmişi korundu."); setRevision((value) => value + 1);
    } catch (reason) { setActionError(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <>
    <PageHeader eyebrow="Akademik" title="Sınavlar & Karne" description="Sınav takvimi, not girişi ve yayımlanan karneler.">
      {writable && <button className="btn btn-primary" onClick={() => setEditor({ exam: null })}><Plus size={16} />Yeni sınav</button>}
    </PageHeader>
    {message && <p role="status">{message}</p>}
    {summary && <section className="card" style={{ padding: 18, marginBottom: 18 }}>
      <h2><Award size={18} /> Kayıtlı akademik performans</h2>
      <p>Son 30 gün · Ortalama: {typeof summary.average_grade === "number" ? summary.average_grade.toFixed(1) : "Veri yok"} / 100 ·
        Geçme oranı: {typeof summary.passing_rate === "number" ? `%${summary.passing_rate}` : "Veri yok"} · Değerlendirilen öğrenci: {String(summary.total_analyzed ?? 0)}</p>
      <p>Farklı tam puanlar 100 üzerinden karşılaştırılır. Değerlendirmeler eşit ağırlıklıdır; iptal edilen ve puansız notlar hesaba katılmaz.</p>
    </section>}
    {summaryError && <p>{summaryError}</p>}
    <section className="card">
      <div className="card-head"><h2>Sınavlar</h2><span>{list?.total ?? 0} kayıt</span></div>
      <div className="card-pad">
        <div className="form-grid" style={{ marginBottom: 16 }}>
          <Field label="Sınav ara"><input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></Field>
          <Field label="Sınav durumu"><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
            <option value="">Tümü</option><option value="SCHEDULED">Planlandı</option><option value="COMPLETED">Tamamlandı</option><option value="CANCELLED">İptal</option>
          </select></Field>
        </div>
        {loading ? <LoadingState label="Sınavlar yükleniyor" /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> :
          !list?.items.length ? <EmptyState title="Sınav bulunamadı" description="Arama koşullarını değiştirebilir veya yeni sınav oluşturabilirsiniz." /> :
          <div className="table-wrap" style={{ overflowX: "auto" }}><table className="data-table" style={{ minWidth: 800 }}><thead><tr><th style={{ position: "sticky", left: 0, zIndex: 2 }}>Sınav adı</th><th>Tarih ve saat</th><th>Sınıf</th><th>Tam puan</th><th>Durum</th><th>İşlemler</th></tr></thead>
            <tbody>{list.items.map((exam) => <tr key={exam.id}>
              <td style={{ position: "sticky", left: 0, zIndex: 1, background: "white", minWidth: 140 }}>{String(exam.title)}</td><td>{String(exam.exam_date)} {String(exam.start_time ?? "").slice(0, 5)}</td>
              <td>{String(exam.class_name ?? "—")}</td><td>{String(exam.max_score ?? "—")}</td><td><Badge value={exam.status} /></td>
              <td><div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <button className="btn btn-secondary" style={{ whiteSpace: "nowrap" }} onClick={() => setSelected(exam)}>Notlar ve karne</button>
                {writable && exam.status !== "CANCELLED" && <>
                  <button className="btn btn-secondary" onClick={() => setEditor({ exam })}>Sınavı düzenle</button>
                  <button className="btn btn-danger" onClick={() => { setCancelling(exam); setActionError(""); }}>Sınavı iptal et</button>
                </>}
              </div></td></tr>)}</tbody></table></div>}
        {(list?.total_pages ?? 0) > 1 && <div className="pagination"><button className="btn btn-secondary" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}>Önceki sınavlar</button>
          <span>{page} / {list?.total_pages}</span><button className="btn btn-secondary" disabled={loading || page >= (list?.total_pages ?? 1)} onClick={() => setPage((value) => value + 1)}>Sonraki sınavlar</button></div>}
      </div>
    </section>
    {selected && <ExamGrades key={selected.id} exam={selected} writable={writable} onChanged={() => setRevision((value) => value + 1)} onClose={() => setSelected(null)} />}
    {editor && <ExamEditor key={editor.exam?.id ?? "new"} exam={editor.exam} onClose={() => setEditor(null)} onSaved={() => { if (editor.exam?.id === selected?.id) setSelected(null); setEditor(null); setMessage("Sınav kaydedildi."); setRevision((value) => value + 1); }} />}
    {cancelling && <Modal open title="Sınav iptal edilsin mi?" onClose={() => { if (!busy) setCancelling(null); }}
      actions={<><button className="btn btn-secondary" disabled={busy} onClick={() => setCancelling(null)}>Vazgeç</button><button className="btn btn-danger" disabled={busy} onClick={cancel}>{busy ? "İptal ediliyor…" : "İptali onayla"}</button></>}>
      <p>{String(cancelling.title)} iptal edilir. Not geçmişi korunur ve akademik hesaplamalara katılmaz.</p>{actionError && <p role="alert">{actionError}</p>}
    </Modal>}
  </>;
}

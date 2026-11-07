import { useEffect, useState } from "react";
import { EmptyState, ErrorState, Field, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { StudentReportCards } from "./StudentReportCards";

type Draft = { score: string; grade_scale: string; notes: string };
function fields(row: DataRecord): Draft { return { score: row.score == null ? "" : String(row.score), grade_scale: String(row.grade_scale ?? ""), notes: String(row.notes ?? "") }; }
export function ExamGrades({ exam, writable, onChanged, onClose }: {
  exam: DataRecord; writable: boolean; onChanged: () => void; onClose: () => void;
}) {
  const [page, setPage] = useState(1), [search, setSearch] = useState(""), [revision, setRevision] = useState(0);
  const [data, setData] = useState<Paginated<DataRecord> | null>(null), [loading, setLoading] = useState(true);
  const [error, setError] = useState(""), [message, setMessage] = useState(""), [saving, setSaving] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({}), [student, setStudent] = useState<{ id: string; name: string } | null>(null);
  const validMaximum = typeof exam.max_score === "number" && Number.isFinite(exam.max_score) && exam.max_score > 0;
  const editable = writable && exam.status !== "CANCELLED" && validMaximum;
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get<ApiResponse<Paginated<DataRecord>>>(`/exams/${exam.id}/roster`, {
      params: { page, page_size: 50, search: search || undefined }, signal: controller.signal,
    }).then((reply) => { if (!controller.signal.aborted) setData(reply.data.data); })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [exam.id, page, search, revision]);
  function change(row: DataRecord, key: keyof Draft, value: string) {
    setDrafts((previous) => ({ ...previous, [row.id]: { ...(previous[row.id] || fields(row)), [key]: value } })); setMessage("");
  }
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (saving || !Object.keys(drafts).length) return;
    setSaving(true); setError(""); setMessage("");
    try {
      await api.post("/exams/bulk-grade-entry", { exam_id: exam.id, grades: Object.entries(drafts).map(([id, row]) => ({
        student_id: id, score: row.score === "" ? null : Number(row.score), grade_scale: row.grade_scale.trim() || null, notes: row.notes.trim() || null,
      })) });
      setDrafts({}); setMessage("Notlar kaydedildi."); setRevision((value) => value + 1); onChanged();
    } catch (reason) { setError(apiMessage(reason)); } finally { setSaving(false); }
  }
  return <section className="card" style={{ marginTop: 20 }} aria-label={`${exam.title} notları`}>
    <div className="card-head"><div><h2>{String(exam.title)} · Notlar</h2><p>Tam puan: {String(exam.max_score ?? "—")}. Boş not değerlendirmeye alınmaz; sıfır gerçek bir nottur.</p></div>
      <button className="btn btn-secondary" disabled={saving} onClick={() => { if (!Object.keys(drafts).length || window.confirm("Kaydedilmemiş notlar var. Kapatılsın mı?")) onClose(); }}>Notları kapat</button></div>
    <div className="card-pad">
      {message && <p role="status">{message}</p>}
      {error && <div role="alert"><ErrorState message={error} retry={() => setRevision((value) => value + 1)} /></div>}
      {exam.status === "CANCELLED" && <p>Sınav iptal edildi. Geçmiş notlar korunur; not girişi kapalıdır.</p>}
      {!validMaximum && <p role="alert">Sınavın eski tam puan kaydı incelenmeli; not girişi kapalıdır.</p>}
      <Field label="Öğrenci ara"><input type="search" value={search} disabled={saving} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></Field>
      {loading ? <LoadingState label="Sınav öğrencileri yükleniyor" /> : !error && data?.items.length === 0 ? <EmptyState title="Sınav öğrencisi bulunamadı" /> : !error && data &&
        <form onSubmit={save}>
          <div className="table-wrap" style={{ overflowX: "auto" }}><table className="data-table" style={{ minWidth: 800 }}><thead><tr><th style={{ position: "sticky", left: 0, zIndex: 2 }}>Öğrenci</th><th>Not / {String(exam.max_score)}</th><th>Harf notu</th><th>Açıklama</th><th>Karne</th></tr></thead>
            <tbody>{data.items.map((row) => {
              const value = drafts[row.id] || fields(row), name = String(row.name), disabled = saving || Boolean(row.duplicate_results);
              return <tr key={row.id}><td style={{ position: "sticky", left: 0, zIndex: 1, background: "white", minWidth: 140 }}>{name}{row.historical && <small> · Önceki sınıf kaydı</small>}{row.duplicate_results && <p role="alert">Yinelenen eski notlar incelenmeli.</p>}{row.invalid_numeric_score && <p role="alert">Eski not sayısal değil; kayıt incelenmeli.</p>}</td>
                <td>{editable ? <div className="field"><input type="number" aria-label={`${name} notu`} min={0} max={Number(exam.max_score)} step="0.01" value={value.score} disabled={disabled} onChange={(event) => change(row, "score", event.target.value)} /></div> : row.score == null ? "—" : String(row.score)}</td>
                <td>{editable ? <div className="field"><input aria-label={`${name} harf notu`} maxLength={10} value={value.grade_scale} disabled={disabled} onChange={(event) => change(row, "grade_scale", event.target.value)} /></div> : String(row.grade_scale ?? "—")}</td>
                <td>{editable ? <div className="field"><input aria-label={`${name} not açıklaması`} maxLength={1000} value={value.notes} disabled={disabled} onChange={(event) => change(row, "notes", event.target.value)} /></div> : String(row.notes ?? "—")}</td>
                <td><button type="button" className="btn btn-secondary" disabled={saving} onClick={() => setStudent({ id: row.id, name })}>Karneler</button></td></tr>;
            })}</tbody></table></div>
          {editable && <div className="head-actions" style={{ marginTop: 16 }}><span>{Object.keys(drafts).length} değişen öğrenci</span>
            <button className="btn btn-primary" disabled={saving || !Object.keys(drafts).length || Object.keys(drafts).length > 1000}>{saving ? "Kaydediliyor…" : "Notları kaydet"}</button></div>}
        </form>}
      {(data?.total_pages ?? 0) > 1 && <div className="pagination"><button className="btn btn-secondary" disabled={loading || saving || page <= 1} onClick={() => setPage((value) => value - 1)}>Önceki öğrenciler</button>
        <span>{page} / {data?.total_pages} · {data?.total} öğrenci</span><button className="btn btn-secondary" disabled={loading || saving || page >= (data?.total_pages ?? 1)} onClick={() => setPage((value) => value + 1)}>Sonraki öğrenciler</button></div>}
      {student && <StudentReportCards key={student.id} student={student} writable={writable} onClose={() => setStudent(null)} />}
    </div>
  </section>;
}

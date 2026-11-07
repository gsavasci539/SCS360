import { useEffect, useState, type FormEvent } from "react";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { shortDate } from "../../lib/format";
import type { DataRecord } from "../../types/api";

function SurveyCard({ row, studentId, canRespond, onChange }: { row: DataRecord; studentId?: string; canRespond: boolean; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const questions = (row.questions || []) as DataRecord[];
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const answers = Object.fromEntries(questions.map((question) => {
      const value = String(form.get(String(question.id)) || "");
      return [question.id, question.question_type === "RATING" && value ? Number(value) : value];
    }));
    setBusy(true); setError("");
    try { await api.post(studentId ? `/parent/child/${studentId}/surveys/${row.id}/respond` : "/surveys/responses", { response_data: answers, ...(!studentId ? { survey_id: row.id } : {}) }); onChange(); }
    catch (reason) { setError(apiMessage(reason)); }
    finally { setBusy(false); }
  }
  return <article style={{ border: "1px solid #dce6e0", borderRadius: 12, padding: 18, overflowWrap: "anywhere" }}>
    <h3>{String(row.title)}</h3>{row.description && <p style={{ whiteSpace: "pre-wrap" }}>{String(row.description)}</p>}
    <p>Son katılım: {shortDate(row.end_date)} · {row.is_anonymous ? "Anonim yanıt" : "Adınızla yanıt"}</p>
    <p>Her katılımcı ankete bir kez yanıt verebilir.{row.is_anonymous && " Yanıtınıza kimlik bilgilerinizi yazmayın."}</p>
    {row.submitted ? <p role="status">Yanıtınız kaydedildi.</p> : !canRespond ? <p>Bu hesap için anket yanıtlama yetkisi tanımlı değil.</p> : !questions.length ? <p>Anketin soruları henüz hazır değil.</p> :
      <form onSubmit={submit} aria-label={`${String(row.title)} yanıt formu`}><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 16 }}>
        {questions.map((question) => <label key={question.id} style={{ display: "grid", gap: 8 }}>{String(question.question_text)}{question.is_required && " *"}
          {question.question_type === "TEXT" ? <textarea className="filter-select" name={String(question.id)} required={Boolean(question.is_required)} maxLength={2000} rows={3} /> :
            <select className="filter-select" aria-label={String(question.question_text)} name={String(question.id)} required={Boolean(question.is_required)}>
              <option value="">Yanıt seçin</option>{question.question_type === "RATING" ? [1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value} / 5</option>) : ((question.options || []) as unknown as string[]).map((value) => <option key={value} value={value}>{value}</option>)}
            </select>}
        </label>)}
        <button className="btn btn-primary" type="submit">{busy ? "Gönderiliyor…" : "Anketi yanıtla"}</button>
      </fieldset></form>}
    {error && <ErrorState message={error} />}
  </article>;
}

export function ParentSurveys({ studentId }: { studentId?: string }) {
  const canRespond = useAuthStore((state) => state.can(studentId ? "parent.respond_survey" : "surveys.respond"));
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(1);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    api.get(studentId ? `/parent/child/${studentId}/surveys` : "/surveys/my-surveys", { params: { limit: 21, offset: (page - 1) * 20 }, signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) { setRows(response.data.data || []); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, page, revision]);
  return <section className="card card-pad" aria-label="Veli anketleri"><h2>Katılımınıza açık anketler</h2>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : rows.length === 0 ? <p>Şu anda katılımınıza açık bir anket yok.</p> : <div style={{ display: "grid", gap: 16 }}>{rows.slice(0, 20).map((row) => <SurveyCard key={`${row.id}-${row.submitted}`} row={row} studentId={studentId} canRespond={canRespond} onChange={() => setRevision((value) => value + 1)} />)}</div>}
    {!loading && !error && (rows.length > 20 || page > 1) && <div className="toolbar" aria-label="Veli anket sayfaları"><button className="btn btn-secondary" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Önceki</button><span>Sayfa {page}</span><button className="btn btn-secondary" disabled={rows.length <= 20} onClick={() => setPage((value) => value + 1)}>Sonraki</button></div>}
  </section>;
}

export function StaffSurveysPage() {
  return <><PageHeader title="Katılabileceğim anketler" description="Kurumunuzun personel katılımına açtığı anketleri yanıtlayın." /><ParentSurveys /></>;
}

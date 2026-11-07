import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate, formatTime } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import type { DataRecord } from "../../types/api";

function SurveyDetail({ id, canWrite, onChange }: { id: string; canWrite: boolean; onChange: () => void }) {
  const [row, setRow] = useState<DataRecord | null>(null);
  const [questions, setQuestions] = useState<DataRecord[]>([]);
  const [results, setResults] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState("RATING");
  const [revision, setRevision] = useState(0);
  const { showToast } = useToast();
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    Promise.all([api.get(`/surveys/surveys/${id}`, { signal: controller.signal }),
      api.get("/surveys/questions", { params: { survey_id: id, limit: 100 }, signal: controller.signal }),
      api.get(`/surveys/surveys/${id}/results`, { signal: controller.signal })])
      .then(([survey, items, stats]) => { if (!controller.signal.aborted) { setRow(survey.data.data); setQuestions(items.data.data || []); setResults(stats.data.data?.question_results || []); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [id, revision]);
  async function action(path: string, method: "post" | "delete", payload?: unknown) {
    setBusy(true);
    try { if (method === "delete") await api.delete(path); else await api.post(path, payload); setRevision((value) => value + 1); onChange(); showToast("Anket güncellendi"); }
    catch (reason) { showToast("İşlem tamamlanamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function addQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    await action("/surveys/questions", "post", { survey_id: id, question_text: String(data.get("question_text")), question_type: kind,
      options: kind === "MULTIPLE_CHOICE" ? String(data.get("options") || "").split("\n").map((value) => value.trim()).filter(Boolean) : null,
      is_required: data.get("is_required") === "on", order_index: questions.length });
  }
  if (loading) return <div className="card card-pad"><LoadingState /></div>;
  if (error || !row) return <div className="card card-pad"><ErrorState message={error || "Anket bulunamadı"} retry={() => setRevision((value) => value + 1)} /></div>;
  return <section className="card card-pad" aria-label="Anket ayrıntısı" style={{ marginTop: 18 }}>
    <div className="toolbar"><h2>{String(row.title)}</h2><Badge value={row.status} /><Link className="btn btn-secondary" to="/surveys">Anket listesine dön</Link></div>
    <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{String(row.description || "")}</p><p>{shortDate(row.start_date)} – {shortDate(row.end_date)} · {row.is_anonymous ? "Anonim yanıtlar" : "Adla yanıtlar"}</p>
    <h3>Sorular</h3>{questions.length === 0 ? <p>Henüz soru eklenmedi.</p> : <ol>{questions.map((question) => <li key={question.id} style={{ marginBottom: 14, overflowWrap: "anywhere" }}>
      {String(question.question_text)}{question.is_required && " (zorunlu)"}<p>{question.question_type === "RATING" ? "1–5 puan" : question.question_type === "TEXT" ? "Yazılı yanıt" : ((question.options || []) as unknown as string[]).join(" · ")}</p>
      {canWrite && row.status === "DRAFT" && <button className="btn btn-secondary" disabled={busy} onClick={() => action(`/surveys/questions/${question.id}`, "delete")}>Soruyu kaldır: {String(question.question_text)}</button>}
    </li>)}</ol>}
    {canWrite && row.status === "DRAFT" && <form onSubmit={addQuestion} aria-label="Ankete soru ekle"><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
      <label>Soru metni<textarea className="filter-select" name="question_text" required maxLength={2000} /></label>
      <label>Soru türü<select className="filter-select" aria-label="Soru türü" value={kind} onChange={(event) => setKind(event.target.value)}><option value="RATING">1–5 puan</option><option value="MULTIPLE_CHOICE">Tek seçenek</option><option value="TEXT">Yazılı yanıt</option></select></label>
      {kind === "MULTIPLE_CHOICE" && <label>Seçenekler (her satıra bir seçenek)<textarea className="filter-select" name="options" required rows={4} placeholder={"Evet\nHayır"} /></label>}
      <label><input type="checkbox" name="is_required" defaultChecked />Zorunlu soru</label>
      <button className="btn btn-primary" disabled={questions.length >= 100}>Soruyu ekle</button>
    </fieldset></form>}
    {canWrite && <div className="toolbar" style={{ marginTop: 16 }}>
      {row.status === "DRAFT" && <button className="btn btn-primary" disabled={busy || !questions.length} onClick={() => action(`/surveys/surveys/${id}/publish`, "post")}>Anketi yayımla</button>}
      {row.status === "ACTIVE" && <button className="btn btn-secondary" disabled={busy} onClick={() => action(`/surveys/surveys/${id}/close`, "post")}>Yanıt alımını kapat</button>}
    </div>}
    <h3 style={{ marginTop: 24 }}>Soru sonuçları</h3>{results.map((result) => <article key={String(result.question_id)} style={{ borderTop: "1px solid #dce6e0", padding: "12px 0" }}>
      <strong>{String(result.question_text)}</strong><p>Geçerli yanıt: {Number(result.response_count || 0)}{result.average_rating != null && ` · Ortalama: ${String(result.average_rating)} / 5`}</p>
      {result.option_counts && <ul>{Object.entries(result.option_counts as unknown as Record<string, number>).map(([option, count]) => <li key={option}>{option}: {count}</li>)}</ul>}
      {Number(result.invalid_count || 0) > 0 && <p>İncelenmesi gereken eski yanıt: {Number(result.invalid_count)}</p>}
    </article>)}
  </section>;
}

export function SurveysPage() {
  const canWrite = useAuthStore((state) => state.can("surveys.write"));
  const userOrg = useWorkspaceUser()?.organization_id;
  const [params, setParams] = useSearchParams(); const selectedId = params.get("survey") || "";
  const [surveys, setSurveys] = useState<DataRecord[]>([]);
  const [responses, setResponses] = useState<DataRecord[]>([]);
  const [stats, setStats] = useState<DataRecord>({ id: "stats" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(1);
  const [responsePage, setResponsePage] = useState(1);
  const [organizations, setOrganizations] = useState<{ id: string; name: string }[]>([]);
  const [organization, setOrganization] = useState(userOrg || "");
  const [optionsError, setOptionsError] = useState("");
  const [busy, setBusy] = useState(false);
  const { showToast } = useToast();
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    Promise.all([api.get("/surveys/surveys", { params: { limit: 21, offset: (page - 1) * 20 }, signal: controller.signal }),
      api.get("/surveys/responses", { params: { limit: 21, offset: (responsePage - 1) * 20, survey_id: selectedId || undefined }, signal: controller.signal }),
      api.get("/surveys/summary", { signal: controller.signal })])
      .then(([rows, answers, summary]) => { if (!controller.signal.aborted) { setSurveys(rows.data.data || []); setResponses(answers.data.data || []); setStats(summary.data.data); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, responsePage, selectedId, revision]);
  useEffect(() => {
    if (!canWrite) return;
    const controller = new AbortController();
    api.get("/surveys/options", { signal: controller.signal }).then((response) => { if (!controller.signal.aborted) { setOrganizations(response.data.data.organizations); setOptionsError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); });
    return () => controller.abort();
  }, [canWrite, revision]);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); setBusy(true);
    try {
      const response = await api.post("/surveys/surveys", { ...Object.fromEntries(data), organization_id: organization, is_anonymous: data.get("is_anonymous") === "on" });
      form.reset(); setParams({ survey: response.data.data.id }); setPage(1); setResponsePage(1); setRevision((value) => value + 1); showToast("Anket taslağı oluşturuldu; soruları ekleyebilirsiniz");
    } catch (reason) { showToast("Anket oluşturulamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  const refresh = () => setRevision((value) => value + 1);
  return <>
    <PageHeader eyebrow="Anketler" title="Anket ve Geri Bildirim" description="Anket taslaklarını, yayımlanan soruları ve gerçek yanıtları yönetin." />
    <div className="card card-pad" style={{ marginTop: 18 }}>Toplam anket: {Number(stats.total_surveys || 0)} · Aktif: {Number(stats.active_surveys || 0)} · Yanıt: {Number(stats.total_responses || 0)}</div>
    {canWrite && !selectedId && <section className="card card-pad" aria-label="Yeni anket" style={{ marginTop: 18 }}><h2>Yeni anket taslağı</h2>
      {optionsError && <ErrorState message={optionsError} retry={refresh} />}
      <form onSubmit={create}><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
        <label>Anket kurumu<select className="filter-select" aria-label="Anket kurumu" value={organization} onChange={(event) => setOrganization(event.target.value)} required><option value="">Kurum seçin</option>{organizations.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        <label>Anket başlığı<input className="filter-select" name="title" required maxLength={255} /></label>
        <label>Anket açıklaması<textarea className="filter-select" name="description" maxLength={5000} /></label>
        <label>Hedef kitle<select className="filter-select" name="target_audience" aria-label="Hedef kitle"><option value="PARENTS">Veliler</option><option value="STAFF">Personel</option><option value="ALL">Tüm katılımcılar</option></select></label>
        <label>Başlangıç tarihi<input className="filter-select" name="start_date" type="date" required /></label>
        <label>Bitiş tarihi<input className="filter-select" name="end_date" type="date" required /></label>
        <label><input type="checkbox" name="is_anonymous" />Anonim yanıt topla</label>
        <button className="btn btn-primary" disabled={!organizations.some((row) => row.id === organization)}>Anket taslağını oluştur</button>
      </fieldset></form>
    </section>}
    {selectedId && <SurveyDetail key={selectedId} id={selectedId} canWrite={canWrite} onChange={refresh} />}
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Anket listesi"><h2>Anketler</h2>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={refresh} /> : surveys.length === 0 ? <p>Henüz anket oluşturulmadı.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Başlık</th><th>Hedef kitle</th><th>Tarih</th><th>Durum</th><th>Yanıt</th></tr></thead><tbody>{surveys.slice(0, 20).map((row) => <tr key={row.id}><td><Link to={`/surveys?survey=${row.id}`} onClick={() => setResponsePage(1)}>{String(row.title)}</Link></td><td>{row.target_audience === "PARENTS" ? "Veliler" : row.target_audience === "STAFF" ? "Personel" : row.target_audience === "ALL" ? "Tümü" : "Tanımlanmamış"}</td><td>{shortDate(row.start_date)} – {shortDate(row.end_date)}</td><td><Badge value={row.status} /></td><td>{Number(row.response_count || 0)}</td></tr>)}</tbody></table></div>}
      <div className="toolbar" aria-label="Anket sayfaları"><button className="btn btn-secondary" disabled={loading || page === 1} onClick={() => setPage((value) => value - 1)}>Önceki</button><span>Sayfa {page}</span><button className="btn btn-secondary" disabled={loading || surveys.length <= 20} onClick={() => setPage((value) => value + 1)}>Sonraki</button></div>
    </section>
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Anket yanıtları"><h2>{selectedId ? "Seçili anketin yanıtları" : "Son yanıtlar"}</h2>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={refresh} /> : responses.length === 0 ? <p>Henüz yanıt yok.</p> : responses.slice(0, 20).map((row) => <article key={row.id} style={{ borderTop: "1px solid #dce6e0", padding: "12px 0" }}>
        <Link to={`/surveys?survey=${row.survey_id}`}>{String(row.survey_title || "Anket")}</Link><p>{row.is_anonymous ? "Anonim katılımcı" : String(row.respondent_name || "Katılımcı")} · {shortDate(row.submitted_at)} {formatTime(row.submitted_at)}</p>
        <details><summary>Yanıtı göster</summary><ul>{((row.answers || []) as Record<string, unknown>[]).map((answer, index) => <li key={index} style={{ overflowWrap: "anywhere" }}>{String(answer.question_text || "Soru")}: {typeof answer.value === "string" || typeof answer.value === "number" ? String(answer.value) : "Eski yanıt incelenmeli"}</li>)}</ul></details>
      </article>)}
      <div className="toolbar" aria-label="Yanıt sayfaları"><button className="btn btn-secondary" disabled={loading || responsePage === 1} onClick={() => setResponsePage((value) => value - 1)}>Önceki</button><span>Sayfa {responsePage}</span><button className="btn btn-secondary" disabled={loading || responses.length <= 20} onClick={() => setResponsePage((value) => value + 1)}>Sonraki</button></div>
    </section>
  </>;
}

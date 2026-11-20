import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { DataRecord } from "../../types/api";

type Kind = "sessions" | "incidents" | "notes";
interface Summary { total_sessions: number; total_notes: number; total_incidents: number; active_cases: number; student_id?: string }
type RecordLoad = { key: string; rows: Record<Kind, DataRecord[]>; stats: Summary } | { key: string; error: string };
interface Choice { id: string; name: string }
interface Options { students: Choice[]; counselors: Choice[]; more_students?: boolean; more_counselors?: boolean; today: string }
const empty: Options = { students: [], counselors: [], today: "" };
const firstPages = { sessions: 1, incidents: 1, notes: 1 };
const kinds = ["sessions", "incidents", "notes"] as const;

export function GuidancePage() {
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const institution = user?.is_super_admin ? (workspace?.operatorId === user.id ? workspace.id : null) : user?.organization_id;
  if (user?.is_super_admin && !institution) return <p>Rehberlik kayıtlarını açmak için bir kurum seçin.</p>;
  if (!hasPermission(user, "guidance.read")) return <p>Rehberlik kayıtlarını görüntüleme yetkiniz yok.</p>;
  const canWrite = hasPermission(user, "guidance.write");
  const canReadPrivate = hasPermission(user, "guidance.read_confidential");
  return <GuidanceRecords key={JSON.stringify([session, user?.id, institution, user?.branch_ids, canReadPrivate, canWrite])}
    userId={user?.id} canWrite={canWrite} canReadPrivate={canReadPrivate} />;
}

function GuidanceRecords({ userId, canWrite, canReadPrivate }: { userId?: string; canWrite: boolean; canReadPrivate: boolean }) {
  const [params, setParams] = useSearchParams(); const studentId = params.get("student") || "";
  const [result, setResult] = useState<RecordLoad | null>(null);
  const [pages, setPages] = useState(firstPages);
  const [options, setOptions] = useState<Options>(empty);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [optionsError, setOptionsError] = useState("");
  const [counselor, setCounselor] = useState("");
  const [search, setSearch] = useState("");
  const [counselorSearch, setCounselorSearch] = useState("");
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const { showToast } = useToast();
  const requestKey = JSON.stringify([studentId, pages, revision]);
  const current = result?.key === requestKey ? result : null;
  useEffect(() => {
    const controller = new AbortController();
    const request = { student_id: studentId || undefined };
    const lists = kinds.map((kind) => api.get<{ data: DataRecord[] }>(`/guidance/${kind}`, {
      params: { ...request, limit: 21, offset: (pages[kind] - 1) * 20 }, signal: controller.signal,
    }));
    Promise.all([Promise.all(lists), api.get<{ data: Summary }>("/guidance/summary", { params: request, signal: controller.signal })])
      .then(([[sessions, incidents, notes], summary]) => {
        if (controller.signal.aborted) return;
        const stats = summary.data.data;
        const rows = { sessions: sessions.data.data, incidents: incidents.data.data, notes: notes.data.data };
        if (!stats || [stats.total_sessions, stats.total_notes, stats.total_incidents, stats.active_cases]
          .some((count) => !Number.isInteger(count) || count < 0) ||
          (stats.student_id ?? "") !== studentId || Object.values(rows).some((records) =>
            !Array.isArray(records) || Boolean(studentId && records.some((row) => row.student_id !== studentId)))) {
          setResult({ key: requestKey, error: "Rehberlik verileri seçili öğrenci kapsamıyla eşleşmiyor." });
          return;
        }
        setResult({ key: requestKey, rows, stats });
      }).catch((reason) => { if (!controller.signal.aborted) setResult({ key: requestKey, error: apiMessage(reason) }); });
    return () => controller.abort();
  }, [studentId, pages, requestKey]);
  useEffect(() => {
    const controller = new AbortController(); setOptionsLoading(true);
    const timer = window.setTimeout(() => {
      api.get("/guidance/options", { params: { student_id: studentId || undefined, search, counselor_search: counselorSearch }, signal: controller.signal })
        .then((response) => {
          if (controller.signal.aborted) return;
          const data = response.data.data as Options; setOptions(data); setOptionsError("");
          setCounselor((current) => data.counselors.some((row) => row.id === current) ? current : data.counselors.some((row) => row.id === userId) ? userId || "" : "");
        }).catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); })
        .finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    }, search || counselorSearch ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [studentId, search, counselorSearch, userId, revision]);
  async function save(event: FormEvent<HTMLFormElement>, kind: Kind) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    const payload: Record<string, unknown> = Object.fromEntries([...data].map(([key, value]) => [key, value === "" ? null : value]));
    payload.student_id = studentId;
    if (kind === "sessions" || kind === "notes") payload.counselor_id = counselor;
    if (kind === "notes") payload.tags = String(data.get("tags") || "").split(",").map((value) => value.trim()).filter(Boolean);
    if (kind === "incidents") payload.parent_notified = data.get("parent_notified") === "on";
    setBusy(true);
    try { await api.post(`/guidance/${kind}`, payload); form.reset(); setPages(firstPages); setRevision((value) => value + 1); showToast("Rehberlik kaydı oluşturuldu"); }
    catch (reason) { showToast("Kayıt oluşturulamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function resolve(event: FormEvent<HTMLFormElement>, id: string) {
    event.preventDefault(); const note = String(new FormData(event.currentTarget).get("resolution_notes") || ""); setBusy(true);
    try { await api.put(`/guidance/incidents/${id}/resolve`, { resolution_notes: note || null }); setRevision((value) => value + 1); showToast("Olay çözümü kaydedildi"); }
    catch (reason) { showToast("Çözüm kaydedilemedi", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  function confidentiality() {
    return <label>Gizlilik düzeyi<select className="filter-select" name="confidentiality_level" aria-label="Gizlilik düzeyi"><option value="STANDARD">Standart</option><option value="RESTRICTED">Kısıtlı</option><option value="CONFIDENTIAL">Gizli</option></select></label>;
  }
  function table(kind: Kind, title: string) {
    const rows = current && "rows" in current ? current.rows[kind] : [];
    return <section className="card card-pad" style={{ marginTop: 18 }} aria-label={title}><h2>{title}</h2>
      {!current ? <LoadingState /> : "error" in current ? <ErrorState message={current.error} retry={() => setRevision((value) => value + 1)} /> : rows.length === 0 ? <p>Bu kapsamda kayıt bulunmuyor.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>Tarih</th><th>{kind === "incidents" ? "Bildirici" : "Danışman"}</th><th>Tür / düzey</th><th>Ayrıntı</th></tr></thead><tbody>{rows.slice(0, 20).map((row) => <tr key={row.id}>
        <td><Link to={`/guidance?student=${row.student_id}`}>{String(row.student_name || "Öğrenci")}</Link></td>
        <td>{shortDate(kind === "sessions" ? row.session_date : kind === "incidents" ? row.incident_date : row.created_at)}</td>
        <td>{String(row.counselor_name || row.reported_by_name || "—")}</td>
        <td>{kind === "incidents" ? <><Badge value={row.severity} /> · {row.resolved ? "Çözüldü" : "Açık"}</> : <Badge value={row.confidentiality_level} />}</td>
        <td style={{ minWidth: 210, maxWidth: 440, overflowWrap: "anywhere" }}><details><summary>{kind === "sessions" ? "Görüşme ayrıntısı" : kind === "notes" ? "Notu oku" : "Olay ayrıntısı"}</summary>
          <p style={{ whiteSpace: "pre-wrap" }}>{String(kind === "sessions" ? row.summary || "Özet eklenmedi" : kind === "notes" ? row.content : row.description)}</p>
          {row.action_plan && <p>Takip planı: {String(row.action_plan)}</p>}{row.follow_up_date && <p>Takip tarihi: {shortDate(row.follow_up_date)}</p>}
          {row.resolution_notes && <p>Çözüm: {String(row.resolution_notes)}</p>}
          {kind === "incidents" && !row.resolved && canWrite && <form onSubmit={(event) => resolve(event, String(row.id))} style={{ display: "grid", gap: 10 }}>
            <label>Çözüm notu<textarea className="filter-select" name="resolution_notes" maxLength={2000} disabled={busy} /></label><button className="btn btn-primary" disabled={busy}>Çözüldü olarak kaydet</button>
          </form>}
        </details></td>
      </tr>)}</tbody></table></div>}
      <div className="toolbar" aria-label={`${title} sayfaları`}><button className="btn btn-secondary" disabled={!current || pages[kind] === 1} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] - 1 }))}>Önceki</button><span>Sayfa {pages[kind]}</span><button className="btn btn-secondary" disabled={rows.length <= 20} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] + 1 }))}>Sonraki</button></div>
    </section>;
  }
  const counselorReady = options.counselors.some((row) => row.id === counselor);
  return <>
    <PageHeader eyebrow="Rehberlik" title="Rehberlik Servisi" description="Öğrenci görüşmeleri, danışman notları ve davranış kayıtları." />
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Rehberlik özeti">
      {!current ? <p role="status">Rehberlik özeti yükleniyor…</p> : "error" in current ?
        <ErrorState message={current.error} retry={() => setRevision((value) => value + 1)} /> :
        <p>Erişime açık görüşme: {current.stats.total_sessions} · Not: {current.stats.total_notes} · Olay: {current.stats.total_incidents} · Açık olay: {current.stats.active_cases}</p>}
    </section>
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Rehberlik kapsamı">
      <p>{canReadPrivate ? "Gizli kayıtları görme yetkiniz, kurum ve şube kapsamınızda geçerlidir." : "Standart kayıtlar ve danışmanı olduğunuz gizli kayıtlar gösterilir."}</p>
      {optionsError && <ErrorState message={optionsError} retry={() => setRevision((value) => value + 1)} />}
      <div className="toolbar" style={{ flexWrap: "wrap" }}><label>Öğrenci ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => { setSearch(event.target.value); setParams({}); setCounselor(""); setPages(firstPages); setOptions(empty); }} /></label>
        <label>Rehberlik öğrencisi<select className="filter-select" aria-label="Rehberlik öğrencisi" value={studentId} disabled={busy} onChange={(event) => { setParams(event.target.value ? { student: event.target.value } : {}); setCounselor(""); setPages(firstPages); }}><option value="">Tüm öğrenciler</option>{options.students.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        {canWrite && studentId && <><label>Danışman ara<input className="filter-select" value={counselorSearch} disabled={busy} onChange={(event) => { setCounselorSearch(event.target.value); setCounselor(""); }} /></label><label>Kayıt danışmanı<select className="filter-select" aria-label="Kayıt danışmanı" value={counselor} disabled={busy || optionsLoading} onChange={(event) => setCounselor(event.target.value)}><option value="">Danışman seçin</option>{options.counselors.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label></>}
      </div>{options.more_students && <p>İlk 100 öğrenci gösterilir; diğer öğrencileri arayarak bulun.</p>}{options.more_counselors && <p>Diğer danışmanları adla arayabilirsiniz.</p>}
    </section>
    {canWrite && studentId && <section className="card card-pad guidance-workspace" style={{ marginTop: 18 }} aria-label="Rehberlik işlemleri" key={studentId}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 24 }}>
        <form aria-label="Görüşme oluştur" onSubmit={(event) => save(event, "sessions")}><h2>Yeni görüşme</h2><fieldset disabled={busy || optionsLoading} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          <label>Görüşme tarihi<input className="filter-select" type="date" name="session_date" defaultValue={options.today} required /></label>
          <label>Görüşme türü<select className="filter-select" name="session_type"><option value="INDIVIDUAL">Bireysel</option><option value="GROUP">Grup</option><option value="FAMILY">Aile</option><option value="CRISIS">Kriz</option></select></label>
          {confidentiality()}<label>Görüşme özeti<textarea className="filter-select" name="summary" maxLength={2000} rows={4} /></label>
          <label>Takip planı<textarea className="filter-select" name="action_plan" maxLength={2000} /></label><label>Takip tarihi<input className="filter-select" type="date" name="follow_up_date" /></label>
          <button className="btn btn-primary" disabled={!counselorReady}>Görüşmeyi kaydet</button>
        </fieldset></form>
        <form aria-label="Danışman notu oluştur" onSubmit={(event) => save(event, "notes")}><h2>Danışman notu</h2><fieldset disabled={busy || optionsLoading} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          {confidentiality()}<label>Not türü<select className="filter-select" name="note_type"><option value="OBSERVATION">Gözlem</option><option value="ASSESSMENT">Değerlendirme</option><option value="INTERVENTION">Müdahale</option></select></label>
          <label>Danışman notu<textarea className="filter-select" name="content" required maxLength={5000} rows={5} /></label><label>Etiketler<input className="filter-select" name="tags" placeholder="Virgülle ayırın" maxLength={1000} /></label>
          <button className="btn btn-primary" disabled={!counselorReady}>Notu kaydet</button>
        </fieldset></form>
        <form aria-label="Davranış olayı oluştur" onSubmit={(event) => save(event, "incidents")}><h2>Davranış olayı</h2><fieldset disabled={busy || optionsLoading} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          <label>Olay tarihi<input className="filter-select" type="date" name="incident_date" defaultValue={options.today} required /></label>
          <label>Olay yeri<input className="filter-select" name="location" maxLength={255} /></label><label>Olay açıklaması<textarea className="filter-select" name="description" required maxLength={2000} rows={4} /></label>
          <label>Olay düzeyi<select className="filter-select" name="severity"><option value="MINOR">Düşük</option><option value="MODERATE">Orta</option><option value="SEVERE">Yüksek</option><option value="CRITICAL">Kritik</option></select></label>
          <label><input type="checkbox" name="parent_notified" />Veli bilgilendirildi</label><button className="btn btn-primary">Olayı kaydet</button>
        </fieldset></form>
      </div>
    </section>}
    {table("sessions", "Görüşmeler")}{table("notes", "Danışman notları")}{table("incidents", "Davranış olayları")}
  </>;
}

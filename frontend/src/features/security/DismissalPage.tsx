import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";

interface Choice { id: string; name: string; active?: boolean }
const text = (value: unknown) => String(value ?? "");
const mask = (value: unknown) => value ? `•••• ${text(value).slice(-4)}` : "Kimlik bilgisi eksik";
const firstPages = { authorizations: 1, logs: 1 };

export function DismissalPage() {
  const canWrite = useAuthStore((state) => state.can("dismissal.write")), canSecurity = useAuthStore((state) => state.can("security.read"));
  const [params, setParams] = useSearchParams(); const studentId = params.get("student") || "";
  const [students, setStudents] = useState<Choice[]>([]), [search, setSearch] = useState(""), [more, setMore] = useState(false);
  const [today, setToday] = useState(""), [day, setDay] = useState("");
  const [authorizations, setAuthorizations] = useState<DataRecord[]>([]), [logs, setLogs] = useState<DataRecord[]>([]), [stats, setStats] = useState<DataRecord>({ id: "stats" });
  const [pages, setPages] = useState(firstPages), [revision, setRevision] = useState(0), [editing, setEditing] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [optionsLoading, setOptionsLoading] = useState(true), [optionsError, setOptionsError] = useState("");
  const [busy, setBusy] = useState(false), [result, setResult] = useState<DataRecord | null>(null);
  const [grantId, setGrantId] = useState(() => newRequestId()), [deliveryId, setDeliveryId] = useState(() => newRequestId());
  const { showToast } = useToast(); const refresh = () => setRevision((value) => value + 1);
  useEffect(() => {
    setGrantId(newRequestId()); setDeliveryId(newRequestId()); setResult(null);
    setEditing((row) => row && row.student_id === studentId ? row : null);
  }, [studentId]);
  useEffect(() => {
    const controller = new AbortController(); setOptionsLoading(true);
    const load = () => api.get("/dismissal/options", { params: { student_id: studentId || undefined, search }, signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return; const data = response.data.data; setStudents(data.students || []); setMore(Boolean(data.more_students)); setToday(data.today); setDay((value) => value || data.today); setOptionsError("");
    }).catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); }).finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    const timer = search ? window.setTimeout(load, 250) : undefined; if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [studentId, search, revision]);
  useEffect(() => {
    if (!day) return;
    const controller = new AbortController(); setLoading(true); const scope = { student_id: studentId || undefined };
    Promise.all([api.get("/dismissal/authorizations", { params: { ...scope, limit: 21, offset: (pages.authorizations - 1) * 20 }, signal: controller.signal }),
      api.get("/dismissal/logs", { params: { ...scope, start_date: day, end_date: day, limit: 21, offset: (pages.logs - 1) * 20 }, signal: controller.signal }),
      api.get("/dismissal/summary", { params: { ...scope, date: day }, signal: controller.signal })])
      .then(([grants, records, summary]) => { if (!controller.signal.aborted) { setAuthorizations(grants.data.data || []); setLogs(records.data.data || []); setStats(summary.data.data); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, day, pages, revision]);
  function scope(id: string) { setParams(id ? { student: id } : {}); setPages(firstPages); setDeliveryId(newRequestId()); setGrantId(newRequestId()); setResult(null); }
  function payload(form: HTMLFormElement) { return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, value === "" ? null : value])); }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget; setBusy(true);
    const body = { ...payload(form), student_id: studentId, request_id: grantId };
    try {
      if (editing) await api.put(`/dismissal/authorizations/${editing.id}`, body); else await api.post("/dismissal/authorizations", body);
      form.reset(); setEditing(null); setGrantId(newRequestId()); setPages(firstPages); refresh(); showToast("Teslim yetkisi kaydedildi");
    } catch (reason) { showToast("Teslim yetkisi kaydedilemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget; setBusy(true);
    try {
      const response = await api.post("/dismissal/verify-pickup", { ...payload(form), student_id: studentId, request_id: deliveryId }); const data = response.data.data;
      setResult(data); if (data.authorized) { form.reset(); setDeliveryId(newRequestId()); setPages((value) => ({ ...value, logs: 1 })); refresh(); }
    } catch (reason) { showToast("Teslim tamamlanamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function revoke(row: DataRecord) {
    setBusy(true); try { await api.delete(`/dismissal/authorizations/${row.id}`); if (editing?.id === row.id) setEditing(null); refresh(); showToast("Teslim yetkisi iptal edildi"); }
    catch (reason) { showToast("Yetki iptal edilemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  function edit(row: DataRecord) { scope(text(row.student_id)); setEditing(row); document.getElementById("pickup-grant-form")?.scrollIntoView?.({ behavior: "smooth", block: "start" }); }
  function field(label: string, name: string, length: number, required = false) { return <label>{label}<input className="filter-select" name={name} maxLength={length} required={required} defaultValue={text(editing?.[name])} /></label>; }
  function pager(kind: keyof typeof firstPages, count: number) { return <div className="toolbar" aria-label={`${kind === "logs" ? "Teslim geçmişi" : "Teslim yetkileri"} sayfaları`}><button className="btn btn-secondary" disabled={loading || pages[kind] === 1} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] - 1 }))}>Önceki</button><span>Sayfa {pages[kind]}</span><button className="btn btn-secondary" disabled={loading || count <= 20} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] + 1 }))}>Sonraki</button></div>; }
  const ready = students.some((row) => row.id === studentId && row.active !== false) && !optionsLoading && !optionsError;
  return <>
    <PageHeader eyebrow="Güvenlik" title="Öğrenci Teslim Masası" description="Yetkili yetişkinler, kimlik kontrolü ve kaydedilmiş öğrenci teslimleri.">{canSecurity && <Link className="btn btn-secondary" to="/security">Öğrenci kimliği ve kapı</Link>}</PageHeader>
    <section className="card card-pad dismissal-workspace" style={{ marginTop: 18 }} aria-label="Teslim kapsamı"><div className="toolbar" style={{ flexWrap: "wrap" }}>
      <label>Teslim öğrencisi ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => setSearch(event.target.value)} /></label><label>Teslim öğrencisi<select className="filter-select" aria-label="Teslim öğrencisi" value={studentId} disabled={busy || optionsLoading} onChange={(event) => { scope(event.target.value); setEditing(null); }}><option value="">Tüm öğrenciler</option>{students.map((row) => <option key={row.id} value={row.id}>{row.name}{row.active === false ? " (Pasif)" : ""}</option>)}</select></label>
      <label>Teslim geçmişi günü<input className="filter-select" type="date" value={day} max={today} disabled={busy} onChange={(event) => { if (event.target.value) { setDay(event.target.value); setPages((value) => ({ ...value, logs: 1 })); } }} /></label>
    </div>{more && <p>İlk 100 öğrenci gösterilir; diğer öğrencileri ad veya numarayla arayın.</p>}{optionsError && <ErrorState message={optionsError} retry={refresh} />}</section>
    <div className="card card-pad" style={{ marginTop: 18 }} aria-label="Teslim özeti">Bugün geçerli yetki: {Number(stats.valid_authorizations || 0)} · Seçili gün teslim kaydı: {Number(stats.total_pickups || 0)} · Teslim edilen öğrenci: {Number(stats.unique_students || 0)}{Number(stats.duplicate_identity_groups || 0) > 0 && <p>Çakışan eski kimlik/yetki grubu: {Number(stats.duplicate_identity_groups)}. Yetki kayıtlarını inceleyin.</p>}</div>
    {canWrite && <section className="card card-pad dismissal-workspace" style={{ marginTop: 18 }} aria-label="Teslim işlemleri"><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 24 }}>
      <form id="pickup-grant-form" aria-label="Teslim yetkisi oluştur" key={`${studentId}-${editing?.id || "new"}-${today}`} onSubmit={save} onChange={() => setGrantId(newRequestId())}><h2>{editing ? "Yetkiyi düzenle" : "Teslim yetkisi"}</h2>{!ready && <p>Kayıt için aktif öğrenci seçin.</p>}<fieldset disabled={busy || !ready} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
        {field("Yetkili yetişkin adı", "authorized_person_name", 255, true)}{field("Yetkili kimlik belgesi numarası", "authorized_person_id", 50, true)}{field("Öğrenciye yakınlığı", "relationship", 100)}{field("Yetkili telefonu", "phone", 20)}{field("Yetkili fotoğraf bağlantısı", "photo_url", 500)}
        <label>Yetki başlangıcı<input className="filter-select" type="date" name="valid_from" defaultValue={text(editing?.valid_from) || today} required /></label><label>Yetki bitişi<input className="filter-select" type="date" name="valid_until" defaultValue={text(editing?.valid_until)} /></label><label>Yetki notu<textarea className="filter-select" name="notes" maxLength={1000} defaultValue={text(editing?.notes)} /></label><button className="btn btn-primary">{editing ? "Yetki değişikliğini kaydet" : "Teslim yetkisini kaydet"}</button>
      </fieldset>{editing && <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => { setEditing(null); setGrantId(newRequestId()); }}>Yeni yetki taslağı</button>}</form>
      <form aria-label="Öğrenci teslimini kaydet" key={`delivery-${studentId}`} onSubmit={verify} onChange={() => { setDeliveryId(newRequestId()); setResult(null); }}><h2>Kimlik ile teslim</h2><p>Kimlik belgesindeki numarayı kontrol ederek girin. Kayıtlı yetişkinin adı teslim sonucunda gösterilir.</p><fieldset disabled={busy || !ready} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}><label>Teslim alanın kimlik belgesi numarası<input className="filter-select" name="pickup_person_id" maxLength={50} autoComplete="off" required /></label><button className="btn btn-primary">Kimliği doğrula ve teslimi kaydet</button></fieldset>
        {result && <p role={result.authorized ? "status" : "alert"}>{result.authorized ? `${text(result.student_name)} · ${text(result.pickup_person_name)} · ${result.repeated_request ? "Önceki teslim kaydı doğrulandı" : "Teslim kaydedildi"} · ${result.pickup_time ? new Date(text(result.pickup_time)).toLocaleString("tr-TR") : ""}` : text(result.message) || "Geçerli teslim yetkisi bulunamadı"}</p>}
      </form>
    </div></section>}
    <section className="card card-pad dismissal-workspace" style={{ marginTop: 18 }} aria-label="Teslim yetkileri" aria-busy={loading}><h2>Teslim yetkileri</h2>{loading && !authorizations.length ? <LoadingState /> : error ? <ErrorState message={error} retry={refresh} /> : !authorizations.length ? <p>Bu kapsamda teslim yetkisi yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci / yetişkin</th><th>Kimlik</th><th>Geçerlilik</th><th>Durum</th><th>Ayrıntı ve işlemler</th></tr></thead><tbody>{authorizations.slice(0, 20).map((row) => <tr key={row.id}><td><Link to={`/dismissal?student=${row.student_id}`} onClick={(event) => { if (busy) { event.preventDefault(); return; } setEditing(null); setPages(firstPages); }}>{text(row.student_name) || "Öğrenci"}</Link><br />{text(row.authorized_person_name)}</td><td>{mask(row.authorized_person_id)}</td><td>{shortDate(row.valid_from)} – {row.valid_until ? shortDate(row.valid_until) : "Bitiş girilmedi"}</td><td><Badge value={row.effective_status || row.status} /></td><td><details><summary>Yetkiyi aç</summary><p className="dismissal-notes">Kimlik: {text(row.authorized_person_id) || "Eksik"}</p><p>Yakınlık: {text(row.relationship) || "Belirtilmedi"}</p><p>Telefon: {text(row.phone) || "Belirtilmedi"}</p>{row.photo_url && <p className="dismissal-notes">Fotoğraf bağlantısı: {text(row.photo_url)}</p>}{row.notes && <p className="dismissal-notes">{text(row.notes)}</p>}<p>Oluşturan: {text(row.created_by_name) || "Kayıtlı yetkili / eski kayıt"}</p>{canWrite && row.status === "ACTIVE" && <div style={{ display: "grid", gap: 8 }}><button className="btn btn-secondary" disabled={busy || loading} onClick={() => edit(row)}>Yetkiyi düzenle</button><button className="btn btn-secondary" disabled={busy || loading} onClick={() => revoke(row)}>Teslim yetkisini iptal et</button></div>}</details></td></tr>)}</tbody></table></div>}{pager("authorizations", authorizations.length)}</section>
    <section className="card card-pad dismissal-workspace" style={{ marginTop: 18 }} aria-label="Teslim geçmişi" aria-busy={loading}><h2>Teslim geçmişi</h2>{loading && !logs.length ? <LoadingState /> : error ? <ErrorState message={error} retry={refresh} /> : !logs.length ? <p>Seçili günde teslim kaydı yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>Teslim alan</th><th>Zaman</th><th>Ayrıntı</th></tr></thead><tbody>{logs.slice(0, 20).map((row) => <tr key={row.id}><td>{text(row.student_name)}</td><td>{text(row.pickup_person_name)}</td><td>{new Date(text(row.pickup_time)).toLocaleString("tr-TR")}</td><td><details><summary>Teslimi aç</summary><p className="dismissal-notes">Kimlik: {text(row.pickup_person_id) || "Eski kayıtta belirtilmemiş"}</p><p>Kaydeden: {text(row.verified_by_name) || "Yetkili kullanıcı"}</p><p>Yöntem: {text(row.verification_method)}</p>{row.notes && <p className="dismissal-notes">{text(row.notes)}</p>}</details></td></tr>)}</tbody></table></div>}{pager("logs", logs.length)}</section>
  </>;
}

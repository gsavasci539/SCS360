import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { downloadFile } from "../../lib/download";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";

interface Choice { id: string; name: string; active?: boolean }
const text = (value: unknown) => String(value ?? "");
const instant = (value: unknown) => value ? new Date(text(value)).toLocaleString("tr-TR") : "Belirtilmedi";

export function SecurityPage() {
  const canWrite = useAuthStore((state) => state.can("security.write"));
  const canDismissal = useAuthStore((state) => state.can("dismissal.read"));
  const [params, setParams] = useSearchParams(); const studentId = params.get("student") || "";
  const [students, setStudents] = useState<Choice[]>([]), [search, setSearch] = useState(""), [more, setMore] = useState(false);
  const [today, setToday] = useState(""), [day, setDay] = useState("");
  const [tokens, setTokens] = useState<DataRecord[]>([]), [logs, setLogs] = useState<DataRecord[]>([]), [stats, setStats] = useState<DataRecord>({ id: "stats" });
  const [pages, setPages] = useState({ tokens: 1, logs: 1 }), [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [optionsLoading, setOptionsLoading] = useState(true), [optionsError, setOptionsError] = useState("");
  const [busy, setBusy] = useState(false), [downloading, setDownloading] = useState("");
  const [issueId, setIssueId] = useState(() => newRequestId()), [gateId, setGateId] = useState(() => newRequestId());
  const [result, setResult] = useState<DataRecord | null>(null); const { showToast } = useToast();
  useEffect(() => { setIssueId(newRequestId()); setGateId(newRequestId()); setResult(null); }, [studentId]);
  useEffect(() => {
    const controller = new AbortController(); setOptionsLoading(true);
    const load = () => api.get("/security/options", { params: { student_id: studentId || undefined, search }, signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return; const data = response.data.data; setStudents(data.students || []); setMore(Boolean(data.more_students)); setToday(data.today); setDay((value) => value || data.today); setOptionsError("");
    }).catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); }).finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    const timer = search ? window.setTimeout(load, 250) : undefined; if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [studentId, search, revision]);
  useEffect(() => {
    if (!day) return;
    const controller = new AbortController(); setLoading(true); const scope = { student_id: studentId || undefined };
    Promise.all([api.get("/security/digital-ids", { params: { ...scope, limit: 21, offset: (pages.tokens - 1) * 20 }, signal: controller.signal }),
      api.get("/security/gate-logs", { params: { ...scope, start_date: day, end_date: day, limit: 21, offset: (pages.logs - 1) * 20 }, signal: controller.signal }),
      api.get("/security/gate-logs/stats", { params: { ...scope, date: day }, signal: controller.signal })])
      .then(([ids, events, counts]) => { if (!controller.signal.aborted) { setTokens(ids.data.data || []); setLogs(events.data.data || []); setStats(counts.data.data); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, day, pages, revision]);
  function refresh() { setRevision((value) => value + 1); }
  async function issue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget; setBusy(true);
    try { await api.post("/security/digital-id/generate", { student_id: studentId, expires_hours: Number(new FormData(form).get("expires_hours")), request_id: issueId }); setIssueId(newRequestId()); setPages({ tokens: 1, logs: 1 }); refresh(); showToast("Öğrenci kimliği oluşturuldu"); }
    catch (reason) { showToast("Kimlik oluşturulamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget; setBusy(true);
    const body = Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, value === "" ? null : value]));
    try {
      const response = await api.post("/security/gate-logs/verify-qr", { ...body, request_id: gateId }); const data = response.data.data;
      setResult(data); if (data.authorized) { form.reset(); setGateId(newRequestId()); setPages((value) => ({ ...value, logs: 1 })); refresh(); }
    } catch (reason) { showToast("Kapı kaydı tamamlanamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function revoke(row: DataRecord) {
    setBusy(true); try { await api.post(`/security/digital-ids/${row.id}/revoke`); refresh(); showToast("Kimlik iptal edildi"); }
    catch (reason) { showToast("Kimlik iptal edilemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function download(row: DataRecord) {
    setDownloading(row.id); try { await downloadFile(`/security/digital-ids/${row.id}/qr-code`, `SCS360-kimlik-${row.student_id}.svg`); }
    catch (reason) { showToast("QR indirilemedi", apiMessage(reason), "error"); } finally { setDownloading(""); }
  }
  function pagination(kind: "tokens" | "logs", count: number) { return <div className="toolbar" aria-label={`${kind === "tokens" ? "Kimlik" : "Kapı kaydı"} sayfaları`}><button className="btn btn-secondary" disabled={loading || pages[kind] === 1} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] - 1 }))}>Önceki</button><span>Sayfa {pages[kind]}</span><button className="btn btn-secondary" disabled={loading || count <= 20} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] + 1 }))}>Sonraki</button></div>; }
  const ready = students.some((row) => row.id === studentId && row.active !== false) && !optionsLoading && !optionsError;
  return <>
    <PageHeader eyebrow="Güvenlik" title="Öğrenci Kimliği ve Kapı Kayıtları" description="Öğrenciye ait QR/barkod kimliği, kimlik yenileme ve gerçek giriş/çıkış geçmişi.">{canDismissal && <Link className="btn btn-secondary" to="/dismissal">Öğrenci teslim masası</Link>}</PageHeader>
    <section className="card card-pad security-workspace" style={{ marginTop: 18 }} aria-label="Güvenlik kapsamı"><div className="toolbar" style={{ flexWrap: "wrap" }}>
      <label>Kimlik öğrencisi ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => setSearch(event.target.value)} /></label>
      <label>Kimlik öğrencisi<select className="filter-select" aria-label="Kimlik öğrencisi" value={studentId} disabled={busy || optionsLoading} onChange={(event) => { setParams(event.target.value ? { student: event.target.value } : {}); setIssueId(newRequestId()); setPages({ tokens: 1, logs: 1 }); }}><option value="">Tüm öğrenciler</option>{students.map((row) => <option key={row.id} value={row.id}>{row.name}{row.active === false ? " (Pasif)" : ""}</option>)}</select></label>
      <label>Kapı kaydı günü<input className="filter-select" type="date" value={day} disabled={busy} max={today} onChange={(event) => { if (event.target.value) { setDay(event.target.value); setPages((value) => ({ ...value, logs: 1 })); } }} /></label>
    </div>{more && <p>İlk 100 öğrenci gösterilir; diğer öğrencileri ad veya numarayla arayın.</p>}{optionsError && <ErrorState message={optionsError} retry={refresh} />}</section>
    <div className="card card-pad" style={{ marginTop: 18 }} aria-label="Kapı özeti">Seçili gün giriş kaydı: {Number(stats.total_entries || 0)} · Çıkış kaydı: {Number(stats.total_exits || 0)} · Son kayda göre içeride: {Number(stats.currently_in_school || 0)}{Number(stats.presence_review_required || 0) > 0 && <p>Zamanı eşit eski giriş/çıkış kayıtları: {Number(stats.presence_review_required)} öğrenci için fiziksel durum kontrol edilmeli.</p>}</div>
    {canWrite && <section className="card card-pad security-workspace" style={{ marginTop: 18 }} aria-label="Güvenlik işlemleri"><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 24 }}>
      <form aria-label="Öğrenci kimliği oluştur" onSubmit={issue}><h2>Kimlik oluştur / yenile</h2><p>Seçili öğrencinin önceki etkin kimlikleri iptal edilir. Okuma işlemi yeni kimlik oluşturmaz.</p>{!ready && <p>Kimlik için aktif öğrenci seçin.</p>}<fieldset disabled={busy || !ready} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}><label>Geçerlilik süresi (saat)<input className="filter-select" type="number" name="expires_hours" min={1} max={8760} defaultValue={24} required onChange={() => setIssueId(newRequestId())} /></label><button className="btn btn-primary">Öğrenci kimliğini oluştur</button></fieldset></form>
      <form aria-label="Kapı geçişi kaydet" key={`gate-${studentId}`} onSubmit={verify} onChange={() => { setGateId(newRequestId()); setResult(null); }}><h2>Kapı geçişi</h2><p>Okunan kod öğrenciyi belirler. Yetişkin tesliminde kimlik ve geçerli teslim yetkisi ayrıca kontrol edilir.</p><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
        <label>QR / barkod değeri<input className="filter-select" name="token" maxLength={255} autoComplete="off" required /></label><label>Kod türü<select className="filter-select" aria-label="Kod türü" name="verification_method"><option value="QR">QR</option><option value="BARCODE">Barkod</option><option value="MANUAL">Elle girilen QR değeri</option></select></label><label>Geçiş yönü<select className="filter-select" aria-label="Geçiş yönü" name="direction"><option value="IN">Giriş</option><option value="OUT">Çıkış</option></select></label><label>Kapı / konum<input className="filter-select" name="gate_location" maxLength={100} /></label><label>Kapı notu<textarea className="filter-select" name="notes" maxLength={1000} /></label><button className="btn btn-primary">Kodu doğrula ve geçişi kaydet</button>
      </fieldset>{result && <p role={result.authorized ? "status" : "alert"}>{result.authorized ? `${text(result.student_name)} · ${result.repeated_request ? "Önceki kayıt doğrulandı" : "Geçiş kaydedildi"} · ${instant(result.timestamp)}` : text(result.message) || "Kimlik eşleşmedi"}</p>}</form>
    </div></section>}
    <section className="card card-pad security-workspace" style={{ marginTop: 18 }} aria-label="Öğrenci kimlikleri" aria-busy={loading}><h2>Öğrenci kimlikleri</h2>{loading && !tokens.length ? <LoadingState /> : error ? <ErrorState message={error} retry={refresh} /> : !tokens.length ? <p>Bu kapsamda kimlik yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>Durum</th><th>Geçerlilik</th><th>Kimlik ve işlemler</th></tr></thead><tbody>{tokens.slice(0, 20).map((row) => <tr key={row.id}><td><Link to={`/security?student=${row.student_id}`} onClick={(event) => { if (busy) event.preventDefault(); else setPages({ tokens: 1, logs: 1 }); }}>{text(row.student_name)}</Link></td><td><Badge value={row.status} /></td><td>{instant(row.expires_at)}</td><td><details><summary>Kimliği aç</summary><p>Oluşturulma: {instant(row.issued_at)}</p><p>Son kullanım: {instant(row.last_used_at)}</p><p className="security-code">QR değeri: {text(row.token)}</p><p className="security-code">Barkod: {text(row.barcode_number)}</p><div style={{ display: "grid", gap: 8 }}>{row.qr_code_url && <button className="btn btn-secondary" disabled={Boolean(downloading)} onClick={() => download(row)}>QR kodunu indir</button>}{canWrite && (row.stored_status || row.status) === "ACTIVE" && <button className="btn btn-secondary" disabled={busy || loading} onClick={() => revoke(row)}>Kimliği iptal et</button>}</div></details></td></tr>)}</tbody></table></div>}{pagination("tokens", tokens.length)}</section>
    <section className="card card-pad security-workspace" style={{ marginTop: 18 }} aria-label="Kapı kayıtları" aria-busy={loading}><h2>Kapı kayıtları</h2>{loading && !logs.length ? <LoadingState /> : error ? <ErrorState message={error} retry={refresh} /> : !logs.length ? <p>Seçili günde kapı kaydı yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci / kişi</th><th>Yön</th><th>Zaman</th><th>Ayrıntı</th></tr></thead><tbody>{logs.slice(0, 20).map((row) => <tr key={row.id}><td>{text(row.student_name || row.user_name) || "Eski kayıt"}</td><td><Badge value={row.direction} /></td><td>{instant(row.created_at)}</td><td><details><summary>Geçişi aç</summary><p>Kapı: {text(row.gate_location) || "Belirtilmedi"} · Şube: {text(row.branch_name) || "Eski kayıt"}</p><p>Doğrulayan: {text(row.verified_by_name) || "Eski kayıtta belirtilmemiş"}</p><p>Yöntem: {text(row.verification_method)}</p><p className="security-code">{text(row.notes)}</p></details></td></tr>)}</tbody></table></div>}{pagination("logs", logs.length)}</section>
  </>;
}

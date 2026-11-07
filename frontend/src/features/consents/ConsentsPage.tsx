import { useEffect, useState, type FormEvent } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate, formatTime } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import type { DataRecord } from "../../types/api";

interface Choice { id: string; name: string }
interface Options { organizations: Choice[]; students: Choice[]; parents: Choice[]; more_students?: boolean }
const empty: Options = { organizations: [], students: [], parents: [] };

export function ConsentsPage() {
  const canWrite = useAuthStore((state) => state.can("consents.write"));
  const userOrg = useWorkspaceUser()?.organization_id;
  const [documents, setDocuments] = useState<DataRecord[]>([]);
  const [consents, setConsents] = useState<DataRecord[]>([]);
  const [summary, setSummary] = useState<DataRecord>({ id: "summary" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [docPage, setDocPage] = useState(1);
  const [consentPage, setConsentPage] = useState(1);
  const [active, setActive] = useState(true);
  const [selected, setSelected] = useState<DataRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [organization, setOrganization] = useState(userOrg || "");
  const [student, setStudent] = useState("");
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<Options>(empty);
  const [optionsError, setOptionsError] = useState("");
  const { showToast } = useToast();
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setSelected(null);
    Promise.all([
      api.get("/consents/documents", { params: { limit: 21, offset: (docPage - 1) * 20, is_active: active }, signal: controller.signal }),
      api.get("/consents/student-consents", { params: { limit: 21, offset: (consentPage - 1) * 20 }, signal: controller.signal }),
      api.get("/consents/consent-summary", { signal: controller.signal }),
    ]).then(([docs, records, stats]) => {
      if (!controller.signal.aborted) { setDocuments(docs.data.data || []); setConsents(records.data.data || []); setSummary(stats.data.data || {}); setError(""); }
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [docPage, consentPage, active, revision]);
  useEffect(() => {
    if (!canWrite) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.get("/consents/options", { params: { organization_id: organization || undefined, student_id: student || undefined, search }, signal: controller.signal })
        .then((response) => { if (!controller.signal.aborted) { setOptions(response.data.data); setOptionsError(""); } })
        .catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); });
    }, search ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [canWrite, organization, student, search, revision]);
  async function createDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form));
    setBusy(true);
    try {
      await api.post("/consents/documents", { ...payload, organization_id: organization });
      form.reset(); setDocPage(1); setActive(true); setRevision((value) => value + 1); showToast("Onay belgesi oluşturuldu");
    } catch (reason) { showToast("Belge oluşturulamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function manualDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return; const form = event.currentTarget;
    setBusy(true);
    try {
      await api.post("/consents/student-consents", { ...Object.fromEntries(new FormData(form)), student_id: student, consent_document_id: selected.id });
      form.reset(); setConsentPage(1); setRevision((value) => value + 1); showToast("Veli kararı kaydedildi");
    } catch (reason) { showToast("Karar kaydedilemedi", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function toggle(doc: DataRecord) {
    setBusy(true);
    try { await api.patch(`/consents/documents/${doc.id}/status`, { is_active: !doc.is_active }); setRevision((value) => value + 1); }
    catch (reason) { showToast("Belge durumu değiştirilemedi", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  function pages(label: string, page: number, more: boolean, change: (value: number) => void) {
    return <div className="toolbar" aria-label={label} style={{ marginTop: 12 }}><button className="btn btn-secondary" disabled={loading || page === 1} onClick={() => change(page - 1)}>Önceki</button><span>Sayfa {page}</span><button className="btn btn-secondary" disabled={loading || !more} onClick={() => change(page + 1)}>Sonraki</button></div>;
  }
  return <>
    <PageHeader eyebrow="Veli kararları" title="Veli Onay Masası" description="Belge metinlerini, sürümlerini ve kayıtlı veli kararlarını yönetin." />
    <div className="card card-pad" style={{ marginTop: 18 }}>Kayıtlı karar: {Number(summary.total || 0)} · Onaylanan: {Number(summary.approved || 0)} · Reddedilen: {Number(summary.rejected || 0)} · Bekleyen kayıt: {Number(summary.pending || 0)}</div>
    {canWrite && <section className="card card-pad" aria-label="Onay belgesi oluştur" style={{ marginTop: 18 }}>
      <h2>Yeni belge</h2>{optionsError && <ErrorState message={optionsError} retry={() => setRevision((value) => value + 1)} />}
      <label>Belge kurumu<select aria-label="Belge kurumu" className="filter-select" value={organization} onChange={(event) => { setOrganization(event.target.value); setStudent(""); setSelected(null); setOptions(empty); }}><option value="">Kurum seçin</option>{options.organizations.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <form onSubmit={createDocument} style={{ display: "grid", gap: 12, marginTop: 12 }}>
        <fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
          <label>Belge başlığı<input className="filter-select" name="title" required maxLength={255} /></label>
          <label>Belge türü<select aria-label="Belge türü" className="filter-select" name="document_type"><option value="TRIP_CONSENT">Gezi izni</option><option value="PHOTO_CONSENT">Fotoğraf izni</option><option value="KVKK">KVKK belgesi</option><option value="OTHER">Diğer</option></select></label>
          <label>Sürüm<input className="filter-select" name="version" required maxLength={20} defaultValue="1.0" /></label>
          <label>Yürürlük tarihi<input className="filter-select" name="effective_date" type="date" required /></label>
          <label>Belgenin tam metni<textarea className="filter-select" name="content" required maxLength={100000} rows={7} /></label>
          <p>Karar verilmiş bir belgenin metni değiştirilemez. Yeni koşullar için yeni sürüm ve yeni belge oluşturun.</p>
          <button className="btn btn-primary" disabled={!options.organizations.some((row) => row.id === organization) || loading}>Belgeyi oluştur</button>
        </fieldset>
      </form>
    </section>}
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Onay belgeleri">
      <div className="toolbar"><h2>Onay belgeleri</h2><label>Belge durumu<select aria-label="Belge durumu" className="filter-select" value={String(active)} onChange={(event) => { setActive(event.target.value === "true"); setDocPage(1); }}><option value="true">Aktif</option><option value="false">Arşiv</option></select></label></div>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : documents.length === 0 ? <p>Bu görünümde belge yok.</p> : documents.slice(0, 20).map((doc) => <article key={doc.id} style={{ borderBottom: "1px solid #dce6e0", padding: "16px 0" }}>
        <h3>{String(doc.title)} · v{String(doc.version)}</h3><p>{String(doc.document_type)} · {shortDate(doc.effective_date)}</p>
        <details><summary>Belge metnini oku</summary><p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{String(doc.content || "Metin bulunamadı")}</p></details>
        {canWrite && <div className="toolbar" style={{ marginTop: 10 }}><button className="btn btn-secondary" disabled={busy} onClick={() => toggle(doc)}>{doc.is_active ? "Arşivle" : "Etkinleştir"}</button>{doc.is_active && <button className="btn btn-primary" disabled={busy} onClick={() => { setSelected(doc); setOrganization(String(doc.organization_id || "")); setStudent(""); setSearch(""); }}>Yazılı veli kararı kaydet</button>}</div>}
      </article>)}
      {pages("Belge sayfaları", docPage, documents.length > 20, setDocPage)}
    </section>
    {canWrite && selected && <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Yazılı veli kararı">
      <h2>{String(selected.title)} · v{String(selected.version)}</h2><p>Kayıtlı velinin ilettiği karar, işlemi yapan kullanıcı bilgisiyle kaydedilir.</p>
      <label>Öğrenci ara<input className="filter-select" value={search} onChange={(event) => { setSearch(event.target.value); setStudent(""); setOptions((value) => ({ ...value, students: [], parents: [] })); }} /></label>
      <label>Öğrenci<select aria-label="Öğrenci" className="filter-select" value={student} onChange={(event) => { setStudent(event.target.value); setOptions((value) => ({ ...value, parents: [] })); }}><option value="">Öğrenci seçin</option>{options.students.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      {options.more_students && <p>İlk 100 öğrenci gösteriliyor; diğer öğrencileri arayarak bulun.</p>}
      {optionsError && <ErrorState message={optionsError} retry={() => setRevision((value) => value + 1)} />}
      <form onSubmit={manualDecision} style={{ display: "grid", gap: 12, marginTop: 12 }}><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
        <label>Kararı veren veli<select aria-label="Kararı veren veli" className="filter-select" name="parent_id" required key={student}><option value="">Veli seçin</option>{options.parents.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        <label>Veli kararı<select aria-label="Veli kararı" className="filter-select" name="consent_status"><option value="APPROVED">Onaylandı</option><option value="REJECTED">Reddedildi</option></select></label>
        <label>Kayıt yöntemi<select aria-label="Kayıt yöntemi" className="filter-select" name="consent_method"><option value="PAPER">Yazılı belge</option><option value="MANUAL">Manuel kayıt</option></select></label>
        <label>Karar notu<textarea className="filter-select" name="notes" maxLength={2000} /></label>
        <button className="btn btn-primary" disabled={!student || !options.parents.length}>Veli kararını kaydet</button>
      </fieldset></form>
    </section>}
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Kayıtlı veli kararları"><h2>Veli kararları</h2>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : consents.length === 0 ? <p>Henüz karar kaydı yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>Belge / sürüm</th><th>Veli</th><th>Tarih</th><th>Karar</th><th>Yöntem</th></tr></thead><tbody>{consents.slice(0, 20).map((row) => <tr key={row.id}><td>{String(row.student_name || "—")}</td><td>{String(row.document_title || "—")} · {String(row.document_version || "—")}</td><td>{String(row.parent_name || "—")}</td><td>{shortDate(row.consented_at)} {formatTime(row.consented_at)}</td><td><Badge value={String(row.consent_status)} /></td><td>{row.consent_method === "PARENT_PORTAL" ? "Veli portalı" : row.consent_method === "PAPER" ? "Yazılı belge" : "Manuel kayıt"}</td></tr>)}</tbody></table></div>}
      {pages("Karar sayfaları", consentPage, consents.length > 20, setConsentPage)}
    </section>
  </>;
}

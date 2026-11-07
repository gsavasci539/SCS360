import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { dateInputValue, shortDate, money } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";

type Kind = "records" | "timesheets" | "additional-hours";
interface Choice { id: string; name: string; organization_name: string }
const firstPages = { records: 1, timesheets: 1, "additional-hours": 1 };

export function PayrollPage() {
  const canWrite = useAuthStore((state) => state.can("payroll.write"));
  const [params, setParams] = useSearchParams(); const staffId = params.get("staff") || "";
  const [staff, setStaff] = useState<Choice[]>([]);
  const [search, setSearch] = useState(""); const [moreStaff, setMoreStaff] = useState(false);
  const [today, setToday] = useState(""); const [year, setYear] = useState(""); const [month, setMonth] = useState(""); const [period, setPeriod] = useState("MONTHLY");
  const [rows, setRows] = useState<Record<Kind, DataRecord[]>>({ records: [], timesheets: [], "additional-hours": [] });
  const [summary, setSummary] = useState<DataRecord>({ id: "summary" }); const [pages, setPages] = useState(firstPages);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const [optionsLoading, setOptionsLoading] = useState(true); const [optionsError, setOptionsError] = useState("");
  const [busy, setBusy] = useState(false); const [revision, setRevision] = useState(0);
  const { showToast } = useToast();
  useEffect(() => {
    const controller = new AbortController(); setOptionsLoading(true);
    const load = () => api.get("/payroll/options", { params: { search, staff_id: staffId || undefined }, signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return;
      const data = response.data.data; setStaff(data.staff || []); setMoreStaff(Boolean(data.more_staff)); setToday(data.today); setOptionsError("");
      setYear((value) => value || data.today.slice(0, 4)); setMonth((value) => value || String(Number(data.today.slice(5, 7))));
    }).catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    const timer = search ? window.setTimeout(load, 250) : undefined; if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [search, staffId, revision]);
  useEffect(() => {
    if (!year || !month) return;
    if (Number(year) < 2020 || Number(year) > 2100) {
      setRows({ records: [], timesheets: [], "additional-hours": [] }); setSummary({ id: "summary" }); setError("2020–2100 arasında geçerli bir yıl seçin"); setLoading(false); return;
    }
    const controller = new AbortController(); setLoading(true);
    const scope = { year: Number(year), month: Number(month), period, staff_id: staffId || undefined };
    const start = `${year}-${month.padStart(2, "0")}-01`;
    const end = dateInputValue(new Date(Number(year), Number(month) - 1 + (period === "QUARTERLY" ? 3 : 1), 0));
    Promise.all([api.get("/payroll/records", { params: { ...scope, limit: 21, offset: (pages.records - 1) * 20 }, signal: controller.signal }),
      api.get("/payroll/timesheets", { params: { staff_id: staffId || undefined, start_date: start, end_date: end, limit: 21, offset: (pages.timesheets - 1) * 20 }, signal: controller.signal }),
      api.get("/payroll/additional-hours", { params: { ...scope, limit: 21, offset: (pages["additional-hours"] - 1) * 20 }, signal: controller.signal }),
      api.get("/payroll/summary", { params: scope, signal: controller.signal })])
      .then(([records, timesheets, extra, stats]) => { if (!controller.signal.aborted) { setRows({ records: records.data.data || [], timesheets: timesheets.data.data || [], "additional-hours": extra.data.data || [] }); setSummary(stats.data.data); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [year, month, period, staffId, pages, revision]);
  async function save(event: FormEvent<HTMLFormElement>, kind: Kind) {
    event.preventDefault(); const form = event.currentTarget;
    const data = Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, value === "" ? null : value]));
    const payload = { ...data, staff_id: staffId, ...(kind !== "timesheets" ? { year: Number(year), month: Number(month), period } : {}) };
    setBusy(true);
    try { await api.post(`/payroll/${kind}`, payload); form.reset(); setPages(firstPages); setRevision((value) => value + 1); showToast("Personel kaydı kaydedildi"); }
    catch (reason) { showToast("Kayıt tamamlanamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function approve(id: string) {
    setBusy(true);
    try { await api.post(`/payroll/records/${id}/approve`); setRevision((value) => value + 1); showToast("Bordro onaylandı"); }
    catch (reason) { showToast("Bordro onaylanamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  const ready = staff.some((row) => row.id === staffId) && Boolean(year && month) && Number(year) >= 2020 && Number(year) <= 2100;
  const periodStart = `${year}-${month.padStart(2, "0")}-01`;
  const periodEnd = year && month ? dateInputValue(new Date(Number(year), Number(month) - 1 + (period === "QUARTERLY" ? 3 : 1), 0)) : "";
  const defaultDay = today >= periodStart && today <= periodEnd ? today : periodStart;
  function numeric(name: string, label: string, max = "9999999999999.99") {
    return <label>{label}<input className="filter-select" type="number" step="0.01" min="0" max={max} name={name} defaultValue="0" required /></label>;
  }
  function table(kind: Kind, title: string) {
    return <section className="card card-pad" style={{ marginTop: 18 }} aria-label={title}><h2>{title}</h2>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : rows[kind].length === 0 ? <p>Seçili dönemde kayıt yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Personel</th><th>Dönem / tarih</th><th>{kind === "timesheets" ? "Saat" : "Tutar"}</th><th>Durum</th><th>Ayrıntı</th></tr></thead><tbody>{rows[kind].slice(0, 20).map((row) => <tr key={row.id}>
        <td><Link to={`/payroll?staff=${row.staff_id}`} onClick={() => setPages(firstPages)}>{String(row.staff_name || "Personel")}</Link></td>
        <td>{kind === "timesheets" ? shortDate(row.date) : `${String(row.month || "Belirsiz")} / ${String(row.year)}`}</td>
        <td>{kind === "timesheets" ? `${String(row.work_hours || 0)} saat` : money(kind === "records" ? row.net_salary : row.total_amount)}</td>
        <td>{kind === "records" ? <Badge value={row.status} /> : kind === "timesheets" ? <Badge value={row.status} /> : row.approved_at ? "Onaylı" : "Kayıtlı"}</td>
        <td><details><summary>Kaydı aç</summary>{kind === "records" && <><p>Temel tutar: {money(row.base_salary)}</p><p>Ek ders: {money(row.additional_course_payment)} · Prim: {money(row.bonus)}</p><p>Avans: {money(row.advance_payment)} · Kesinti: {money(row.deductions)}</p>{row.approved_at && <p>Onay: {String(row.approved_by_name || "Kayıtlı yetkili")} · {shortDate(row.approved_at)}</p>}</>}
          {kind === "additional-hours" && <p>{String(row.total_hours)} saat × {money(row.hourly_rate)}</p>}{row.notes && <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{String(row.notes)}</p>}
          {kind === "records" && canWrite && row.status === "DRAFT" && <button className="btn btn-primary" disabled={busy} onClick={() => approve(String(row.id))}>Bordroyu onayla</button>}
        </details></td>
      </tr>)}</tbody></table></div>}
      <div className="toolbar" aria-label={`${title} sayfaları`}><button className="btn btn-secondary" disabled={loading || pages[kind] === 1} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] - 1 }))}>Önceki</button><span>Sayfa {pages[kind]}</span><button className="btn btn-secondary" disabled={loading || rows[kind].length <= 20} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] + 1 }))}>Sonraki</button></div>
    </section>;
  }
  return <>
    <PageHeader eyebrow="Personel" title="Bordro ve Puantaj" description="Dönem bazında çalışma kayıtları, ek ders ve bordro taslakları." />
    <section className="card card-pad payroll-filters" style={{ marginTop: 18 }} aria-label="Bordro dönemi"><div className="toolbar" style={{ flexWrap: "wrap" }}>
      <label>Yıl<input className="filter-select" type="number" min={2020} max={2100} value={year} disabled={busy} onChange={(event) => { setYear(event.target.value); setPages(firstPages); }} /></label>
      <label>Dönem ayı<select className="filter-select" aria-label="Dönem ayı" value={month} disabled={busy} onChange={(event) => { setMonth(event.target.value); setPages(firstPages); }}>{!month && <option value="">Ay seçin</option>}{Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}</select></label>
      <label>Dönem türü<select className="filter-select" aria-label="Dönem türü" value={period} disabled={busy} onChange={(event) => { setPeriod(event.target.value); setPages(firstPages); }}><option value="MONTHLY">Aylık</option><option value="QUARTERLY">Üç aylık</option></select></label>
      <label>Personel ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => { setSearch(event.target.value); setParams({}); setStaff([]); setPages(firstPages); }} /></label>
      <label>Bordro personeli<select className="filter-select" aria-label="Bordro personeli" value={staffId} disabled={busy || optionsLoading} onChange={(event) => { setParams(event.target.value ? { staff: event.target.value } : {}); setPages(firstPages); }}><option value="">Tüm personel</option>{staff.map((row) => <option key={row.id} value={row.id}>{row.name} · {row.organization_name}</option>)}</select></label>
    </div>{period === "QUARTERLY" && <p>Üç aylık kayıtta dönem ayı başlangıç ayıdır.</p>}{moreStaff && <p>İlk 100 personel gösterilir; diğer personeli adla arayın.</p>}{optionsError && <ErrorState message={optionsError} retry={() => setRevision((value) => value + 1)} />}</section>
    <div className="card card-pad" style={{ marginTop: 18 }}>Bordro: {Number(summary.total_payroll || 0)} · Onay bekleyen: {Number(summary.pending_approvals || 0)} · Net dönem toplamı: {money(summary.net_salary_total)} · Puantaj: {Number(summary.total_timesheets || 0)} · Ortalama saat: {Number(summary.average_hours || 0)}</div>
    {canWrite && <section className="card card-pad payroll-workspace" style={{ marginTop: 18 }} aria-label="Bordro işlemleri" key={`${staffId}-${year}-${month}-${period}`}>
      {!ready ? <p>Kayıt oluşturmak için personel ve geçerli bir dönem seçin.</p> : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 24 }}>
        <form aria-label="Puantaj oluştur" onSubmit={(event) => save(event, "timesheets")}><h2>Puantaj kaydı</h2><fieldset disabled={busy || optionsLoading} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          <label>Puantaj tarihi<input className="filter-select" type="date" name="timesheet_date" defaultValue={defaultDay} required /></label>{numeric("work_hours", "Çalışma saati", "24")}
          <label>Devam durumu<select className="filter-select" name="status"><option value="PRESENT">Çalıştı</option><option value="ABSENT">Gelmedi</option><option value="LEAVE">İzinli</option><option value="SICK">Raporlu</option></select></label>
          <label>Puantaj notu<textarea className="filter-select" name="notes" maxLength={2000} /></label><button className="btn btn-primary">Puantajı kaydet</button>
        </fieldset></form>
        <form aria-label="Ek ders kaydı oluştur" onSubmit={(event) => save(event, "additional-hours")}><h2>Ek ders kaydı</h2><fieldset disabled={busy || optionsLoading} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          {numeric("total_hours", "Ek ders saati", "999.99")}{numeric("hourly_rate", "Saat ücreti", "99999999.99")}<label>Ek ders notu<textarea className="filter-select" name="notes" maxLength={2000} /></label><button className="btn btn-primary">Ek dersi kaydet</button>
        </fieldset></form>
        <form aria-label="Bordro taslağı oluştur" onSubmit={(event) => save(event, "records")}><h2>Bordro taslağı</h2><fieldset disabled={busy || optionsLoading} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          {numeric("base_salary", "Temel tutar")}{numeric("additional_course_payment", "Bordro ek ders tutarı")}{numeric("bonus", "Prim")}{numeric("advance_payment", "Avans")}{numeric("deductions", "Kesinti")}
          <label>Bordro notu<textarea className="filter-select" name="notes" maxLength={2000} /></label><button className="btn btn-primary">Bordro taslağını kaydet</button>
        </fieldset></form>
      </div>}
    </section>}
    {table("records", "Bordro kayıtları")}{table("additional-hours", "Ek ders kayıtları")}{table("timesheets", "Puantaj kayıtları")}
  </>;
}

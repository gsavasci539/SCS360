import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";

type Kind = "records" | "visits" | "schedules" | "logs";
interface Choice { id: string; name: string }
const firstPages = { records: 1, visits: 1, schedules: 1, logs: 1 };
const text = (value: unknown) => String(value ?? "");
const fields = { records: "Sağlık dosyaları", visits: "Revir ziyaretleri", schedules: "İlaç programları ve talepler", logs: "Günlük doz kayıtları" };

export function HealthPage() {
  const canWrite = useAuthStore((state) => state.can("health.write"));
  const [params, setParams] = useSearchParams(); const studentId = params.get("student") || "";
  const [students, setStudents] = useState<Choice[]>([]), [search, setSearch] = useState(""), [moreStudents, setMoreStudents] = useState(false);
  const [today, setToday] = useState(""), [clock, setClock] = useState(""), [day, setDay] = useState("");
  const [rows, setRows] = useState<Record<Kind, DataRecord[]>>({ records: [], visits: [], schedules: [], logs: [] });
  const [pages, setPages] = useState(firstPages), [summary, setSummary] = useState<DataRecord>({ id: "summary" });
  const [optionsLoading, setOptionsLoading] = useState(true), [optionsError, setOptionsError] = useState("");
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [revision, setRevision] = useState(0), [busy, setBusy] = useState(false);
  const { showToast } = useToast();
  useEffect(() => {
    const controller = new AbortController(); setOptionsLoading(true);
    const load = () => api.get("/infirmary/options", { params: { student_id: studentId || undefined, search }, signal: controller.signal })
      .then((response) => { if (controller.signal.aborted) return; const data = response.data.data;
        setStudents(data.students || []); setMoreStudents(Boolean(data.more_students)); setToday(data.today); setClock(data.time); setDay((value) => value || data.today); setOptionsError("");
      }).catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    const timer = search ? window.setTimeout(load, 250) : undefined; if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [studentId, search, revision]);
  useEffect(() => {
    if (!day) return;
    const controller = new AbortController(); setLoading(true);
    const scope = { student_id: studentId || undefined };
    Promise.all([api.get("/infirmary/health-records", { params: { ...scope, limit: 21, offset: (pages.records - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/infirmary-visits", { params: { ...scope, start_date: day, end_date: day, limit: 21, offset: (pages.visits - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/medicine-requests", { params: { ...scope, limit: 21, offset: (pages.schedules - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/medication-logs", { params: { ...scope, date: day, limit: 21, offset: (pages.logs - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/summary", { params: scope, signal: controller.signal })])
      .then(([records, visits, schedules, logs, stats]) => { if (!controller.signal.aborted) { setRows({ records: records.data.data || [], visits: visits.data.data || [], schedules: schedules.data.data || [], logs: logs.data.data || [] }); setSummary(stats.data.data); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, day, pages, revision]);
  function payload(form: HTMLFormElement) { return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, value === "" ? null : value])); }
  async function save(event: FormEvent<HTMLFormElement>, kind: "records" | "visits" | "schedules") {
    event.preventDefault(); const form = event.currentTarget; const body = { ...payload(form), student_id: studentId };
    setBusy(true);
    try {
      if (kind === "records") await api.put(`/infirmary/health-records/${studentId}`, body);
      else if (kind === "schedules") await api.post("/infirmary/medication-schedules", body);
      else { const values = new FormData(form); await api.post("/infirmary/infirmary-visits", { ...body, follow_up_required: values.has("follow_up_required"), parent_notified: values.has("parent_notified") }); }
      if (kind !== "records") form.reset(); setPages(firstPages); setRevision((value) => value + 1); showToast("Sağlık kaydı kaydedildi");
    } catch (reason) { showToast("Sağlık kaydı kaydedilemedi", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function action(path: string, body: unknown, put = false) {
    setBusy(true);
    try { if (put) await api.put(path, body); else await api.post(path, body); setRevision((value) => value + 1); showToast("İşlem kaydedildi"); }
    catch (reason) { showToast("İşlem tamamlanamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  const ready = students.some((row) => row.id === studentId) && !optionsLoading && !optionsError && !loading && !error;
  const fileRows = rows.records.filter((row) => row.student_id === studentId), file = fileRows[0];
  function input(label: string, name: string, maxLength: number, value: unknown = "") { return <label>{label}<input className="filter-select" name={name} maxLength={maxLength} defaultValue={text(value)} /></label>; }
  function note(label: string, name: string, value: unknown = "", required = false) { return <label>{label}<textarea className="filter-select" name={name} maxLength={1000} defaultValue={text(value)} required={required} /></label>; }
  function table(kind: Kind) {
    return <section className="card card-pad health-workspace" style={{ marginTop: 18 }} aria-label={fields[kind]} aria-busy={loading}><h2>{fields[kind]}</h2>
      {(kind === "visits" || kind === "logs") && <p>Görüntülenen gün: {shortDate(day)}</p>}
      {loading && !rows[kind].length ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : !rows[kind].length ? <p>Bu kapsamda kayıt yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>{kind === "records" ? "Sağlık bilgisi" : kind === "visits" ? "Ziyaret" : "İlaç / doz"}</th><th>{kind === "records" ? "Güncelleme" : "Tarih / durum"}</th><th>Ayrıntı ve işlemler</th></tr></thead><tbody>{rows[kind].slice(0, 20).map((row) => <tr key={row.id}>
        <td><Link to={`/health?student=${row.student_id}`} onClick={() => setPages(firstPages)}>{text(row.student_name) || "Öğrenci"}</Link></td>
        <td>{kind === "records" ? <>Kan grubu: {text(row.blood_type) || "Belirtilmedi"}<p className="health-notes">Alerji: {text(row.allergies) || "Bilgi girilmedi"}</p></> : kind === "visits" ? <><p className="health-notes">{text(row.complaint) || "Açıklama girilmedi"}</p>{text(row.visit_time)}</> : kind === "schedules" ? <>{text(row.medicine_name)}<br />{text(row.dosage)} · {text(row.time_to_give)}</> : <>{text(row.medication_name) || "İlaç programı"}<br />Plan saati: {text(row.scheduled_time)}<br />{text(row.notes)}</>}</td>
        <td>{kind === "records" ? shortDate(row.updated_at) : kind === "visits" ? <>{shortDate(row.visit_date)}<br /><Badge value={row.severity} /></> : kind === "logs" ? <>{shortDate(row.scheduled_date || row.given_time || row.created_at)}<br /><Badge value={row.status} /></> : <Badge value={row.status} />}</td>
        <td><details><summary>Kaydı aç</summary>
          {kind === "records" && <><p className="health-notes">Kronik durum: {text(row.chronic_conditions) || "Bilgi girilmedi"}</p><p>Acil kişi: {text(row.emergency_contact_name) || "Belirtilmedi"} · {text(row.emergency_contact_phone)}</p><p>Yakınlık: {text(row.emergency_contact_relation) || "Belirtilmedi"}</p><p>Son kontrol: {shortDate(row.last_checkup_date)}</p>{row.insurance_info && <pre className="health-notes">{JSON.stringify(row.insurance_info, null, 2)}</pre>}<p>Güncelleyen: {text(row.updated_by_name) || "Eski kayıt"}</p></>}
          {kind === "visits" && <><p>Kaydeden: {text(row.examined_by_name) || "Eski kayıt"}</p>{row.temperature != null && <p>Ateş: {text(row.temperature)} °C</p>}{row.blood_pressure_systolic != null && <p>Tansiyon: {text(row.blood_pressure_systolic)} / {text(row.blood_pressure_diastolic)}</p>}<p className="health-notes">İşlem: {text(row.treatment_given) || "Bilgi girilmedi"}</p><p className="health-notes">Takip: {text(row.follow_up_notes) || "Not girilmedi"}</p><p>{row.follow_up_required ? "Takip bekliyor" : "Bekleyen takip yok"}</p><p>Manuel veli bilgisi: {row.parent_notified ? text(row.notification_method) : "Kaydedilmedi"}</p>
            {canWrite && row.follow_up_required && <form aria-label={`Revir takibini tamamla ${row.student_name}`} onSubmit={(event) => { event.preventDefault(); action(`/infirmary/infirmary-visits/${row.id}/follow-up`, payload(event.currentTarget)); }}><fieldset disabled={busy || loading} style={{ border: 0, padding: 0 }}>{note("Takip sonuç notu", "follow_up_notes", "", true)}<button className="btn btn-primary">Takibi tamamla</button></fieldset></form>}</>}
          {kind === "logs" && <><p>Kaydeden: {text(row.given_by_name) || "Eski kayıt"}</p><p>Uygulama zamanı: {row.given_time ? new Date(text(row.given_time)).toLocaleString("tr-TR") : "Uygulandı kaydı yok"}</p>{!row.scheduled_date && <p>Eski kayıtta doz günü ayrı tutulmamış; tarih mevcut zaman bilgisinden okunur.</p>}</>}
          {kind === "schedules" && <><p>{shortDate(row.start_date)} – {row.end_date ? shortDate(row.end_date) : "Bitiş girilmedi"}</p><p className="health-notes">Talimat: {text(row.instructions) || "Belirtilmedi"}</p><p>Karar veren: {text(row.updated_by_name) || "Henüz karar yok / eski kayıt"}</p>
            {canWrite && row.status === "PENDING" && <div className="toolbar"><button className="btn btn-primary" disabled={busy || loading} onClick={() => action(`/infirmary/medicine-requests/${row.id}`, { status: "APPROVED" }, true)}>İlaç talebini onayla</button><button className="btn btn-secondary" disabled={busy || loading} onClick={() => action(`/infirmary/medicine-requests/${row.id}`, { status: "REJECTED" }, true)}>İlaç talebini reddet</button></div>}
            {canWrite && row.status === "APPROVED" && <><form aria-label={`Doz kaydı ${row.medicine_name}`} onSubmit={(event) => { event.preventDefault(); action("/infirmary/medication/mark-given", { ...payload(event.currentTarget), student_id: row.student_id, schedule_id: row.id }); }}><fieldset disabled={busy || loading} style={{ border: 0, padding: 0, display: "grid", gap: 8 }}>
              <label>Doz günü<input className="filter-select" type="date" name="scheduled_date" value={today} readOnly /></label><label>Planlanan doz saati<input className="filter-select" type="time" name="scheduled_time" required /></label><label>Doz sonucu<select className="filter-select" aria-label="Doz sonucu" name="status"><option value="GIVEN">Uygulandı</option><option value="SKIPPED">Atlandı</option><option value="CANCELLED">İptal edildi</option></select></label>{note("Doz kayıt notu", "notes")}<button className="btn btn-primary">Doz sonucunu kaydet</button>
            </fieldset></form><button className="btn btn-secondary" disabled={busy || loading} onClick={() => action(`/infirmary/medicine-requests/${row.id}`, { status: "COMPLETED" }, true)}>Programı kapat</button></>}
          </>}
        </details></td>
      </tr>)}</tbody></table></div>}
      <div className="toolbar" aria-label={`${fields[kind]} sayfaları`}><button className="btn btn-secondary" disabled={loading || pages[kind] === 1} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] - 1 }))}>Önceki</button><span>Sayfa {pages[kind]}</span><button className="btn btn-secondary" disabled={loading || rows[kind].length <= 20} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] + 1 }))}>Sonraki</button></div>
    </section>;
  }
  return <>
    <PageHeader eyebrow="Sağlık" title="Revir & İlaç Kayıtları" description="Öğrenci sağlık dosyası, revir ziyaretleri, talep incelemesi ve günlük doz geçmişi." />
    <section className="card card-pad health-workspace" style={{ marginTop: 18 }} aria-label="Sağlık kapsamı"><div className="toolbar" style={{ flexWrap: "wrap" }}>
      <label>Sağlık öğrencisi ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => setSearch(event.target.value)} /></label>
      <label>Sağlık öğrencisi<select className="filter-select" aria-label="Sağlık öğrencisi" value={studentId} disabled={busy || optionsLoading} onChange={(event) => { setParams(event.target.value ? { student: event.target.value } : {}); setPages(firstPages); }}><option value="">Tüm öğrenciler</option>{students.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <label>Ziyaret ve doz günü<input className="filter-select" type="date" value={day} disabled={busy} required onChange={(event) => { if (event.target.value) { setDay(event.target.value); setPages(firstPages); } }} /></label>
    </div>{moreStudents && <p>İlk 100 öğrenci gösterilir; diğer öğrencileri adla arayın.</p>}{optionsError && <ErrorState message={optionsError} retry={() => setRevision((value) => value + 1)} />}</section>
    <div className="card card-pad" style={{ marginTop: 18 }} aria-label="Revir özeti">Sağlık dosyası: {Number(summary.total_records || 0)} · Bu ay ziyaret: {Number(summary.recent_visits || 0)} · Bekleyen takip: {Number(summary.follow_up_visits || 0)} · Bugün aktif program: {Number(summary.active_schedules || 0)} · Bekleyen ilaç talebi: {Number(summary.pending_requests || 0)}</div>
    {canWrite && <section className="card card-pad health-workspace" style={{ marginTop: 18 }} aria-label="Revir işlemleri">{!studentId && <p>Kayıt oluşturmak veya sağlık dosyasını düzenlemek için öğrenci seçin.</p>}<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 24 }}>
      <form aria-label="Sağlık dosyasını düzenle" key={`file-${studentId}-${file?.id}-${file?.updated_at}`} onSubmit={(event) => save(event, "records")}><h2>Sağlık dosyası</h2>{fileRows.length > 1 && <p>Birden fazla eski dosya var; birleştirme yapılmadan incelenmeli.</p>}<fieldset disabled={busy || !ready || fileRows.length > 1} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
        {input("Kan grubu", "blood_type", 5, file?.blood_type)}{note("Alerji bilgisi", "allergies", file?.allergies)}{note("Kronik durum bilgisi", "chronic_conditions", file?.chronic_conditions)}{input("Acil kişi adı", "emergency_contact_name", 255, file?.emergency_contact_name)}{input("Acil kişi telefonu", "emergency_contact_phone", 20, file?.emergency_contact_phone)}{input("Yakınlık", "emergency_contact_relation", 50, file?.emergency_contact_relation)}<label>Son kontrol tarihi<input className="filter-select" type="date" name="last_checkup_date" defaultValue={text(file?.last_checkup_date)} /></label><button className="btn btn-primary">Sağlık dosyasını kaydet</button>
      </fieldset></form>
      <form aria-label="Revir ziyareti oluştur" key={`visit-${studentId}-${day}`} onSubmit={(event) => save(event, "visits")}><h2>Revir ziyareti</h2><fieldset disabled={busy || !ready} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
        <label>Ziyaret tarihi<input className="filter-select" type="date" name="visit_date" defaultValue={day} required /></label><label>Ziyaret saati<input className="filter-select" type="time" name="visit_time" defaultValue={clock} required /></label>{note("Şikâyet", "complaint", "", true)}<label>Öncelik<select className="filter-select" aria-label="Öncelik" name="severity"><option value="LOW">Düşük</option><option value="MEDIUM">Orta</option><option value="HIGH">Yüksek</option><option value="EMERGENCY">Acil</option></select></label>
        <label>Ateş (°C)<input className="filter-select" type="number" min={35} max={42} step="0.1" name="temperature" /></label>{note("Kaydedilen işlem", "treatment_given")}<label className="health-checkbox"><input type="checkbox" name="follow_up_required" />Takip gerekli</label>{note("Takip notu", "follow_up_notes")}<label className="health-checkbox"><input type="checkbox" name="parent_notified" />Veliye manuel bilgi verildi</label>{input("Manuel bilgilendirme yöntemi", "notification_method", 50)}<button className="btn btn-primary">Revir ziyaretini kaydet</button>
      </fieldset></form>
      <form aria-label="İlaç programı oluştur" key={`schedule-${studentId}-${today}`} onSubmit={(event) => save(event, "schedules")}><h2>İlaç programı</h2><p>Kayıt, okul ekibinin incelediği talimata göre oluşturulur. Veli talepleri aşağıda ayrıca onaylanır.</p><fieldset disabled={busy || !ready} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
        <label>Program ilaç adı<input className="filter-select" name="medication_name" maxLength={255} required /></label><label>Kayıtlı doz<input className="filter-select" name="dosage" maxLength={100} required /></label><label>Saat / sıklık talimatı<input className="filter-select" name="frequency" maxLength={100} required /></label><label>Başlangıç günü<input className="filter-select" type="date" name="start_date" defaultValue={today} required /></label><label>Bitiş günü<input className="filter-select" type="date" name="end_date" /></label>
        <label>Öğün talimatı<select className="filter-select" aria-label="Öğün talimatı" name="instruction"><option value="NOT_SPECIFIED">Belirtilmedi</option><option value="BEFORE_MEAL">Yemekten önce</option><option value="AFTER_MEAL">Yemekten sonra</option><option value="WITH_MEAL">Yemekle birlikte</option><option value="EMPTY_STOMACH">Aç karnına</option></select></label>{note("Program ek notu", "parent_notes")}<button className="btn btn-primary">İlaç programını kaydet</button>
      </fieldset></form>
    </div></section>}
    {table("records")}{table("visits")}{table("schedules")}{table("logs")}
  </>;
}

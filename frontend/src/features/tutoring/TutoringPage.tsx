import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";

type Kind = "sessions" | "requests" | "availability";
interface Choice { id: string; name: string }
const firstPages = { sessions: 1, requests: 1, availability: 1 };
const week = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
const text = (value: unknown) => String(value ?? "");

export function TutoringPage() {
  const canWrite = useAuthStore((state) => state.can("tutoring.write"));
  const [params, setParams] = useSearchParams(); const studentId = params.get("student") || "", teacherId = params.get("teacher") || "";
  const [students, setStudents] = useState<Choice[]>([]), [teachers, setTeachers] = useState<Choice[]>([]);
  const [search, setSearch] = useState(""), [teacherSearch, setTeacherSearch] = useState("");
  const [moreStudents, setMoreStudents] = useState(false), [moreTeachers, setMoreTeachers] = useState(false);
  const [today, setToday] = useState(""), [optionsLoading, setOptionsLoading] = useState(true), [optionsError, setOptionsError] = useState("");
  const [rows, setRows] = useState<Record<Kind, DataRecord[]>>({ sessions: [], requests: [], availability: [] });
  const [pages, setPages] = useState(firstPages), [summary, setSummary] = useState<DataRecord>({ id: "summary" });
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [revision, setRevision] = useState(0), [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<DataRecord | null>(null), [editId, setEditId] = useState("");
  const { showToast } = useToast();
  useEffect(() => {
    const controller = new AbortController(); setOptionsLoading(true);
    const load = () => api.get("/tutoring/options", { params: { student_id: studentId || undefined, teacher_id: teacherId || undefined, search, teacher_search: teacherSearch }, signal: controller.signal })
      .then((response) => { if (controller.signal.aborted) return; const data = response.data.data;
        setStudents(data.students || []); setTeachers(data.teachers || []); setToday(data.today);
        setMoreStudents(Boolean(data.more_students)); setMoreTeachers(Boolean(data.more_teachers)); setOptionsError("");
      }).catch((reason) => { if (!controller.signal.aborted) setOptionsError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    const timer = search || teacherSearch ? window.setTimeout(load, 250) : undefined; if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [studentId, teacherId, search, teacherSearch, revision]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    const scope = { student_id: studentId || undefined, teacher_id: teacherId || undefined };
    Promise.all([api.get("/tutoring/sessions", { params: { ...scope, limit: 21, offset: (pages.sessions - 1) * 20 }, signal: controller.signal }),
      api.get("/tutoring/requests", { params: { ...scope, limit: 21, offset: (pages.requests - 1) * 20 }, signal: controller.signal }),
      api.get("/tutoring/availability", { params: { teacher_id: teacherId || undefined, limit: 21, offset: (pages.availability - 1) * 20 }, signal: controller.signal }),
      api.get("/tutoring/summary", { params: scope, signal: controller.signal })])
      .then(([sessions, requests, availability, stats]) => { if (!controller.signal.aborted) {
        setRows({ sessions: sessions.data.data || [], requests: requests.data.data || [], availability: availability.data.data || [] }); setSummary(stats.data.data); setError("");
      } }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, teacherId, pages, revision]);
  function scope(student: string, teacher: string) { setParams({ ...(student ? { student } : {}), ...(teacher ? { teacher } : {}) }); setPages(firstPages); }
  function payload(form: HTMLFormElement) {
    return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, value === "" ? null : value]));
  }
  async function save(event: FormEvent<HTMLFormElement>, kind: Kind) {
    event.preventDefault(); const form = event.currentTarget;
    const body = { ...payload(form), teacher_id: teacherId || null, ...(kind !== "availability" ? { student_id: studentId } : {}) };
    setBusy(true);
    try {
      if (kind === "sessions" && editId) await api.put(`/tutoring/sessions/${editId}`, body); else await api.post(`/tutoring/${kind}`, body);
      form.reset(); if (kind === "sessions") { setEditId(""); setDraft(null); }
      setRevision((value) => value + 1); setPages(firstPages); showToast("Etüt kaydı kaydedildi");
    } catch (reason) { showToast("Etüt kaydedilemedi", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  async function action(path: string, body?: unknown, remove = false) {
    setBusy(true);
    try { if (remove) await api.delete(path); else await api.post(path, body); setRevision((value) => value + 1); showToast("İşlem kaydedildi"); }
    catch (reason) { showToast("İşlem tamamlanamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  function plan(row: DataRecord, editing = false) {
    scope(text(row.student_id), text(row.teacher_id)); setEditId(editing ? row.id : "");
    setDraft(editing ? row : { ...row, session_date: row.requested_date, start_time: row.preferred_time_start || "09:00", end_time: row.preferred_time_end || "10:00", notes: row.reason });
    document.getElementById("tutoring-session-form")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }
  const studentReady = students.some((row) => row.id === studentId), teacherReady = teachers.some((row) => row.id === teacherId);
  function dateTimeFields(request = false) {
    return <><label>{request ? "İstenen tarih" : "Etüt tarihi"}<input className="filter-select" type="date" name={request ? "requested_date" : "session_date"} defaultValue={request ? today : text(draft?.session_date) || today} required /></label>
      <label>{request ? "Tercih başlangıcı" : "Başlangıç saati"}<input className="filter-select" type="time" name={request ? "preferred_time_start" : "start_time"} defaultValue={request ? "" : text(draft?.start_time) || "09:00"} required={!request} /></label>
      <label>{request ? "Tercih bitişi" : "Bitiş saati"}<input className="filter-select" type="time" name={request ? "preferred_time_end" : "end_time"} defaultValue={request ? "" : text(draft?.end_time) || "10:00"} required={!request} /></label></>;
  }
  function table(kind: Kind, title: string) {
    return <section className="card card-pad tutoring-workspace" style={{ marginTop: 18 }} aria-label={title} aria-busy={loading}><h2>{title}</h2>
      {kind === "requests" && <p>Talep onayı ders oluşturmaz. Onaylanan talep için ayrıca saat seçip ders planlayın.</p>}
      {loading && !rows[kind].length ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : !rows[kind].length ? <p>Bu kapsamda kayıt yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>{kind === "availability" ? "Öğretmen" : "Öğrenci / öğretmen"}</th><th>{kind === "availability" ? "Gün" : "Ders / tarih"}</th><th>Saat</th><th>Durum</th><th>Ayrıntı ve işlemler</th></tr></thead><tbody>{rows[kind].slice(0, 20).map((row) => <tr key={row.id}>
        <td>{kind !== "availability" && <><Link to={`/tutoring?student=${row.student_id}`} onClick={() => setPages(firstPages)}>{text(row.student_name) || "Öğrenci"}</Link><br /></>}{text(row.teacher_name) || "Öğretmen seçilmedi"}</td>
        <td>{kind === "availability" ? week[Number(row.day_of_week)] : <>{text(row.subject) || "Etüt"}<br />{shortDate(kind === "sessions" ? row.session_date : row.requested_date)}</>}</td>
        <td>{kind === "requests" ? `${text(row.preferred_time_start) || "Belirtilmedi"} – ${text(row.preferred_time_end) || "Belirtilmedi"}` : `${text(row.start_time)} – ${text(row.end_time)}`}</td>
        <td>{kind === "availability" ? row.is_available ? "Açık" : "Kapalı" : <Badge value={row.status} />}</td>
        <td><details><summary>Kaydı aç</summary>{row.location && <p>Yer: {text(row.location)}</p>}{row.notes && <p className="tutoring-notes">{text(row.notes)}</p>}{row.reason && <p className="tutoring-notes">{text(row.reason)}</p>}
          {row.approved_at && <p>Onay: {text(row.approved_by_name) || "Kayıtlı yetkili"} · {shortDate(row.approved_at)}</p>}{row.rejection_reason && <p className="tutoring-notes">Ret: {text(row.rejection_reason)}</p>}
          {kind === "availability" && <p>Kapasite: {Number(row.max_students)} öğrenci · Mevcut dersler kapatmadan etkilenmez.</p>}
          {kind === "sessions" && row.attendance_status && <p>Devam: {text(row.attendance_status)} · İlerleme: {row.progress_score == null ? "Belirtilmedi" : `${row.progress_score}/100`}</p>}
          {canWrite && <div style={{ display: "grid", gap: 10, minWidth: 190 }}>
            {kind === "sessions" && row.status === "SCHEDULED" && <><button className="btn btn-secondary" disabled={busy} onClick={() => plan(row, true)}>Dersi düzenle</button><button className="btn btn-secondary" disabled={busy} onClick={() => action(`/tutoring/sessions/${row.id}/cancel`)}>Dersi iptal et</button></>}
            {kind === "sessions" && row.status !== "CANCELLED" && <form aria-label={`Devam kaydı ${row.student_name}`} onSubmit={(event) => { event.preventDefault(); action(`/tutoring/sessions/${row.id}/attendance`, payload(event.currentTarget)); }}><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 8 }}>
              <label>Etüt devamı<select className="filter-select" aria-label="Etüt devamı" name="attendance_status" defaultValue={text(row.attendance_status) || "PRESENT"}><option value="PRESENT">Katıldı</option><option value="ABSENT">Katılmadı</option><option value="LATE">Geç geldi</option></select></label>
              <label>İlerleme puanı<input className="filter-select" type="number" name="progress_score" min={0} max={100} defaultValue={text(row.progress_score)} /></label><label>Ders notu<textarea className="filter-select" name="notes" maxLength={4000} defaultValue={text(row.notes)} /></label><button className="btn btn-primary">Devamı kaydet</button>
            </fieldset></form>}
            {kind === "requests" && row.status === "PENDING" && <><button className="btn btn-primary" disabled={busy || (!row.teacher_id && !teacherReady)} onClick={() => action(`/tutoring/requests/${row.id}/approve`, { teacher_id: row.teacher_id || teacherId })}>Talebi onayla</button>{!row.teacher_id && <p>Onay için üstten öğretmen seçin.</p>}
              <form aria-label={`Talebi reddet ${row.student_name}`} onSubmit={(event) => { event.preventDefault(); action(`/tutoring/requests/${row.id}/reject`, payload(event.currentTarget)); }}><fieldset disabled={busy} style={{ border: 0, padding: 0 }}><label>Ret gerekçesi<textarea className="filter-select" name="rejection_reason" maxLength={2000} required /></label><button className="btn btn-secondary">Talebi reddet</button></fieldset></form></>}
            {kind === "requests" && row.status === "APPROVED" && <button className="btn btn-primary" disabled={busy} onClick={() => plan(row)}>Bu talep için ders planla</button>}
            {kind === "availability" && row.is_available && <button className="btn btn-secondary" disabled={busy} onClick={() => action(`/tutoring/availability/${row.id}`, undefined, true)}>Müsaitliği kapat</button>}
          </div>}
        </details></td>
      </tr>)}</tbody></table></div>}
      <div className="toolbar" aria-label={`${title} sayfaları`}><button className="btn btn-secondary" disabled={loading || pages[kind] === 1} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] - 1 }))}>Önceki</button><span>Sayfa {pages[kind]}</span><button className="btn btn-secondary" disabled={loading || rows[kind].length <= 20} onClick={() => setPages((value) => ({ ...value, [kind]: value[kind] + 1 }))}>Sonraki</button></div>
    </section>;
  }
  return <>
    <PageHeader eyebrow="Etüt ve Birebir Ders" title="Etüt Yönetimi" description="Öğretmen müsaitliği, ders planı, talepler ve devam kayıtları." />
    <section className="card card-pad tutoring-workspace" style={{ marginTop: 18 }} aria-label="Etüt kapsamı"><div className="toolbar" style={{ flexWrap: "wrap" }}>
      <label>Öğrenci ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => setSearch(event.target.value)} /></label>
      <label>Etüt öğrencisi<select className="filter-select" aria-label="Etüt öğrencisi" value={studentId} disabled={busy || optionsLoading} onChange={(event) => { scope(event.target.value, ""); setDraft(null); setEditId(""); }}><option value="">Tüm öğrenciler</option>{students.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <label>Öğretmen ara<input className="filter-select" value={teacherSearch} disabled={busy} onChange={(event) => setTeacherSearch(event.target.value)} /></label>
      <label>Etüt öğretmeni<select className="filter-select" aria-label="Etüt öğretmeni" value={teacherId} disabled={busy || optionsLoading} onChange={(event) => { scope(studentId, event.target.value); setDraft(null); setEditId(""); }}><option value="">Tüm öğretmenler</option>{teachers.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
    </div>{moreStudents && <p>İlk 100 öğrenci gösterilir; diğer öğrencileri adla arayın.</p>}{moreTeachers && <p>İlk 100 öğretmen gösterilir; diğer öğretmenleri adla arayın.</p>}{optionsError && <ErrorState message={optionsError} retry={() => setRevision((value) => value + 1)} />}</section>
    <div className="card card-pad" style={{ marginTop: 18 }} aria-label="Etüt özeti">Toplam ders: {Number(summary.total_sessions || 0)} · Planlanan: {Number(summary.scheduled_sessions || 0)} · Tamamlanan: {Number(summary.completed_sessions || 0)} · Bekleyen talep: {Number(summary.pending_requests || 0)} · Açık müsaitlik: {Number(summary.available_windows || 0)}</div>
    {canWrite && <section className="card card-pad tutoring-workspace" style={{ marginTop: 18 }} aria-label="Etüt işlemleri"><p>Öğretmen seçiminde öğrencinin sınıf ve bireysel öğretmen atamaları kullanılır. Ders, açık müsaitlik ve kapasiteye göre planlanır. Saatler okulun yerel saatidir.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 24 }}>
        <form id="tutoring-session-form" aria-label="Etüt planla" key={`session-${studentId}-${teacherId}-${draft?.id || "new"}-${editId}-${today}`} onSubmit={(event) => save(event, "sessions")}><h2>{editId ? "Dersi düzenle" : "Ders planla"}</h2>{(!studentReady || !teacherReady) && <p>Öğrenci ve atanmış öğretmen seçin.</p>}<fieldset disabled={busy || optionsLoading || Boolean(optionsError) || !studentReady || !teacherReady} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          <label>Ders adı<input className="filter-select" name="subject" maxLength={100} defaultValue={text(draft?.subject)} /></label>{dateTimeFields()}<label>Ders yeri<input className="filter-select" name="location" maxLength={255} defaultValue={text(draft?.location)} /></label><label>Plan notu<textarea className="filter-select" name="notes" maxLength={4000} defaultValue={text(draft?.notes)} /></label><button className="btn btn-primary">{editId ? "Ders değişikliğini kaydet" : "Dersi planla"}</button>
        </fieldset>{draft && <button className="btn btn-secondary" disabled={busy} type="button" onClick={() => { setDraft(null); setEditId(""); }}>Yeni ders taslağı</button>}</form>
        <form aria-label="Etüt talebi oluştur" key={`request-${studentId}-${teacherId}-${today}`} onSubmit={(event) => save(event, "requests")}><h2>Ders talebi</h2>{!studentReady && <p>Talep için öğrenci seçin.</p>}<fieldset disabled={busy || optionsLoading || Boolean(optionsError) || !studentReady} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}><label>Talep ders adı<input className="filter-select" name="subject" maxLength={100} /></label>{dateTimeFields(true)}<label>Talep gerekçesi<textarea className="filter-select" name="reason" maxLength={4000} /></label><button className="btn btn-primary">Talep oluştur</button></fieldset></form>
        <form aria-label="Müsaitlik oluştur" key={`availability-${teacherId}-${today}`} onSubmit={(event) => save(event, "availability")}><h2>Öğretmen müsaitliği</h2>{!teacherReady && <p>Müsaitlik için öğretmen seçin.</p>}<fieldset disabled={busy || optionsLoading || Boolean(optionsError) || !teacherReady} style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
          <label>Müsait gün<select className="filter-select" aria-label="Müsait gün" name="day_of_week" defaultValue={today ? (new Date(`${today}T12:00:00`).getDay() + 6) % 7 : 0}>{week.map((day, index) => <option key={day} value={index}>{day}</option>)}</select></label><label>Müsait başlangıç<input className="filter-select" type="time" name="start_time" defaultValue="09:00" required /></label><label>Müsait bitiş<input className="filter-select" type="time" name="end_time" defaultValue="12:00" required /></label><label>Eşzamanlı öğrenci kapasitesi<input className="filter-select" type="number" name="max_students" defaultValue={1} min={1} max={100} required /></label><button className="btn btn-primary">Müsaitliği kaydet</button>
        </fieldset></form>
      </div>
    </section>}
    {table("sessions", "Etüt oturumları")}{table("requests", "Ders talepleri")}{table("availability", "Öğretmen müsaitlikleri")}
  </>;
}

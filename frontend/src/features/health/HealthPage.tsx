import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { DataRecord } from "../../types/api";

type Kind = "records" | "visits" | "schedules" | "logs";
interface Choice { id: string; name: string }
interface Options { students: Choice[]; more_students: boolean; today: string; time: string }
interface Summary { student_id?: string; total_records: number; recent_visits: number; follow_up_visits: number; active_schedules: number; pending_requests: number }
type Result<T> = { key: string; data: T } | { key: string; error: string };
interface Write { scope: string; controller: AbortController }
const firstPages = { records: 1, visits: 1, schedules: 1, logs: 1 };
const emptyRows: Record<Kind, DataRecord[]> = { records: [], visits: [], schedules: [], logs: [] };
const text = (value: unknown) => String(value ?? "");
const fields = { records: "Sağlık dosyaları", visits: "Revir ziyaretleri", schedules: "İlaç programları ve talepler", logs: "Günlük doz kayıtları" };

export function HealthPage() {
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const institution = user?.is_super_admin ? (workspace?.operatorId === user.id ? workspace.id : null) : user?.organization_id;
  if (user?.is_super_admin && !institution) return <p>Revir kayıtlarını açmak için bir kurum seçin.</p>;
  if (!user || !hasPermission(user, "health.read")) return <p>Revir kayıtlarını görüntüleme yetkiniz yok.</p>;
  const canWrite = hasPermission(user, "health.write");
  return <HealthRecords key={JSON.stringify([session, user.id, institution, user.branch_ids, canWrite])}
    actorId={user.id} canWrite={canWrite} />;
}

function HealthRecords({ actorId, canWrite }: { actorId: string; canWrite: boolean }) {
  const [params, setParams] = useSearchParams(); const studentId = params.get("student") || "";
  const [search, setSearch] = useState("");
  const [filterDay, setDay] = useState("");
  const [optionResult, setOptionResult] = useState<Result<Options> | null>(null);
  const [schoolClock, setSchoolClock] = useState<{ today: string; time: string } | null>(null);
  const [snapshot, setSnapshot] = useState<Result<{ rows: Record<Kind, DataRecord[]>; summary: Summary }> | null>(null);
  const [pages, setPages] = useState(firstPages);
  const [revision, setRevision] = useState(0);
  const [optionRevision, setOptionRevision] = useState(0);
  const pending = useRef<Write | null>(null);
  const [write, setWrite] = useState<Write | null>(null);
  const busy = write?.scope === studentId && !write.controller.signal.aborted;
  const { showToast } = useToast();
  const optionsKey = JSON.stringify([studentId, search, optionRevision]);
  const currentOptions = optionResult?.key === optionsKey ? optionResult : null;
  const options = currentOptions && "data" in currentOptions ? currentOptions.data : null;
  const today = schoolClock?.today ?? "";
  const clock = schoolClock?.time ?? "";
  const day = filterDay || today;
  const verifiedScope = !studentId || Boolean(options?.students.some((row) => row.id === studentId));
  const optionError = currentOptions && "error" in currentOptions ? currentOptions.error : null;
  const scopeError = studentId && options && !verifiedScope ? "Seçili öğrenci revir erişim kapsamınızda bulunamadı." : null;
  const dataKey = JSON.stringify([studentId, day, pages, revision]);
  const current = verifiedScope && snapshot?.key === dataKey ? snapshot : null;
  const rows = current && "data" in current ? current.data.rows : emptyRows;
  const summary = current && "data" in current ? current.data.summary : null;
  const error = scopeError || (current && "error" in current ? current.error : null) || (!day ? optionError : null);
  const loading = !current && !error;
  useLayoutEffect(() => () => {
    pending.current?.controller.abort();
    pending.current = null;
  }, [studentId]);
  useEffect(() => {
    const controller = new AbortController();
    const load = () => api.get<{ data: Options }>("/infirmary/options", { params: { student_id: studentId || undefined, search }, signal: controller.signal })
      .then(({ data: { data } }) => {
        if (controller.signal.aborted) return;
        if (!data || !Array.isArray(data.students) || !data.today || !data.time) {
          setOptionResult({ key: optionsKey, error: "Öğrenci seçenekleri doğrulanamadı." });
          return;
        }
        setOptionResult({ key: optionsKey, data });
        setSchoolClock({ today: data.today, time: data.time });
      }).catch((reason) => { if (!controller.signal.aborted) setOptionResult({ key: optionsKey, error: apiMessage(reason) }); });
    const timer = search ? window.setTimeout(load, 250) : undefined; if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [studentId, search, optionsKey]);
  useEffect(() => {
    if (!day || !verifiedScope) return;
    const controller = new AbortController();
    const scope = { student_id: studentId || undefined };
    Promise.all([api.get("/infirmary/health-records", { params: { ...scope, limit: 21, offset: (pages.records - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/infirmary-visits", { params: { ...scope, start_date: day, end_date: day, limit: 21, offset: (pages.visits - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/medicine-requests", { params: { ...scope, limit: 21, offset: (pages.schedules - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/medication-logs", { params: { ...scope, date: day, limit: 21, offset: (pages.logs - 1) * 20 }, signal: controller.signal }),
      api.get("/infirmary/summary", { params: scope, signal: controller.signal })])
      .then(([records, visits, schedules, logs, stats]) => {
        if (controller.signal.aborted) return;
        const summary: Summary | undefined = stats.data.data;
        const rows: Record<Kind, DataRecord[]> = { records: records.data.data, visits: visits.data.data,
          schedules: schedules.data.data, logs: logs.data.data };
        if (!summary || (summary.student_id ?? "") !== studentId ||
          [summary.total_records, summary.recent_visits, summary.follow_up_visits, summary.active_schedules, summary.pending_requests]
            .some((count) => !Number.isInteger(count) || count < 0) ||
          Object.values(rows).some((list) => !Array.isArray(list) || list.some((row) => !row?.id || !row.student_id ||
            (studentId && row.student_id !== studentId))) ||
          rows.visits.some((row) => row.visit_date !== day) || rows.logs.some((row) => row.scheduled_date && row.scheduled_date !== day)) {
          setSnapshot({ key: dataKey, error: "Revir verileri seçili öğrenci veya tarihle eşleşmiyor." });
          return;
        }
        setSnapshot({ key: dataKey, data: { rows, summary } });
      })
      .catch((reason) => { if (!controller.signal.aborted) setSnapshot({ key: dataKey, error: apiMessage(reason) }); });
    return () => controller.abort();
  }, [studentId, day, pages, dataKey, verifiedScope]);
  function payload(form: HTMLFormElement) {
    return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, String(value).trim() || null]));
  }
  async function submit(path: string, body: Record<string, unknown>, method: "post" | "put", expected: Record<string, unknown>,
    verify: (saved: DataRecord) => boolean, onVerified: () => void, success: string, rereadOnConflict = false) {
    if (!canWrite || pending.current) return;
    const operation = { scope: studentId, controller: new AbortController() };
    const { signal } = operation.controller;
    pending.current = operation;
    setWrite(operation);
    try {
      const { data } = await api[method]<{ data: DataRecord }>(path, body, { signal });
      if (signal.aborted) return;
      const saved = data.data;
      if (typeof saved?.id !== "string" || !saved.id.trim() ||
        !Object.entries(expected).every(([key, value]) => saved[key] === value)) {
        showToast("Kayıt doğrulanamadı", "Sunucu yanıtı seçili öğrenci veya kayıtla eşleşmiyor.", "error");
        return;
      }
      if (!verify(saved)) {
        if (rereadOnConflict) setRevision((value) => value + 1);
        showToast("Gönderilen işlem doğrulanamadı",
          rereadOnConflict ? "Sunucudaki mevcut kayıt yeniden okunuyor." : "Sunucu yanıtı gönderilen bilgilerle eşleşmiyor.", "error");
        return;
      }
      onVerified();
      setRevision((value) => value + 1);
      showToast(success);
    } catch (reason) {
      if (!signal.aborted) showToast("İşlem tamamlanamadı", apiMessage(reason), "error");
    } finally {
      if (pending.current === operation) {
        pending.current = null;
        setWrite(null);
      }
    }
  }
  function save(event: FormEvent<HTMLFormElement>, kind: "records" | "visits" | "schedules") {
    event.preventDefault();
    if (!ready) return;
    const form = event.currentTarget;
    const values = payload(form);
    const scope = { student_id: studentId };
    const reset = () => { form.reset(); setPages(firstPages); };
    if (kind === "records") {
      if (fileRows.length > 1) return;
      const changes = Object.fromEntries(Object.entries(values).filter(([key, value]) => text(value) !== text(file?.[key]).trim()));
      if (!Object.keys(changes).length) return;
      const expected = file ? { ...scope, id: file.id } : scope;
      void submit(`/infirmary/health-records/${encodeURIComponent(studentId)}`, { ...scope, ...changes }, "put", expected,
        (saved) => saved.updated_by === actorId && Object.entries(changes).every(([key, value]) => saved[key] === value),
        () => setPages(firstPages), "Sağlık dosyası kaydedildi");
    } else if (kind === "schedules") {
      void submit("/infirmary/medication-schedules", { ...scope, ...values }, "post", scope,
        (saved) => saved.created_by === actorId && saved.status === "APPROVED" &&
          Object.entries(values).every(([key, value]) => saved[key] === value), reset, "İlaç programı kaydedildi");
    } else {
      const followUp = values.follow_up_required === "on";
      const parentNotified = values.parent_notified === "on";
      const body = { ...values, ...scope, follow_up_required: followUp, parent_notified: parentNotified,
        notification_method: parentNotified ? values.notification_method : null };
      void submit("/infirmary/infirmary-visits", body, "post", scope, (saved) =>
        saved.examined_by === actorId && saved.visit_date === values.visit_date && saved.visit_time === values.visit_time &&
        saved.complaint === values.complaint && saved.severity === values.severity && saved.parent_notified === parentNotified &&
        saved.notification_method === body.notification_method && saved.follow_up_required === followUp,
      () => { reset(); setDay(values.visit_date ?? day); }, "Revir ziyareti kaydedildi");
    }
  }
  function completeVisit(event: FormEvent<HTMLFormElement>, row: DataRecord) {
    event.preventDefault();
    const body = payload(event.currentTarget);
    void submit(`/infirmary/infirmary-visits/${encodeURIComponent(row.id)}/follow-up`, body, "post",
      { id: row.id, student_id: row.student_id, follow_up_required: false },
      (saved) => saved.follow_up_notes === body.follow_up_notes, () => {}, "Takip sonucu kaydedildi", true);
  }
  function decideMedication(row: DataRecord, status: "APPROVED" | "REJECTED" | "COMPLETED") {
    void submit(`/infirmary/medicine-requests/${encodeURIComponent(row.id)}`, { status }, "put",
      { id: row.id, student_id: row.student_id, status },
      (saved) => saved.updated_by === actorId, () => {}, "İlaç talebi durumu kaydedildi", true);
  }
  function recordDose(event: FormEvent<HTMLFormElement>, row: DataRecord) {
    event.preventDefault();
    const body = payload(event.currentTarget);
    const scope = { student_id: row.student_id, schedule_id: row.id };
    void submit("/infirmary/medication/mark-given", { ...body, ...scope }, "post",
      { ...scope, scheduled_time: body.scheduled_time, status: body.status },
      (saved) => saved.scheduled_date === body.scheduled_date && saved.given_by === actorId && saved.notes === body.notes,
      () => { setPages(firstPages); setDay(today); }, "Doz sonucu kaydedildi", true);
  }
  const ready = options?.students.some((row) => row.id === studentId) && Boolean(summary);
  const fileRows = rows.records.filter((row) => row.student_id === studentId), file = fileRows[0];
  function input(label: string, name: string, maxLength: number, value: unknown = "") { return <label>{label}<input className="filter-select" name={name} maxLength={maxLength} defaultValue={text(value)} /></label>; }
  function note(label: string, name: string, value: unknown = "", required = false) { return <label>{label}<textarea className="filter-select" name={name} maxLength={1000} defaultValue={text(value)} required={required} /></label>; }
  function table(kind: Kind) {
    return <section className="card card-pad health-workspace" style={{ marginTop: 18 }} aria-label={fields[kind]} aria-busy={loading}><h2>{fields[kind]}</h2>
      {(kind === "visits" || kind === "logs") && <p>Görüntülenen gün: {shortDate(day)}</p>}
      {loading && !rows[kind].length ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : !rows[kind].length ? <p>Bu kapsamda kayıt yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>{kind === "records" ? "Sağlık bilgisi" : kind === "visits" ? "Ziyaret" : "İlaç / doz"}</th><th>{kind === "records" ? "Güncelleme" : "Tarih / durum"}</th><th>Ayrıntı ve işlemler</th></tr></thead><tbody>{rows[kind].slice(0, 20).map((row) => <tr key={row.id}>
        <td><Link to={`/health?student=${encodeURIComponent(text(row.student_id))}`} onClick={() => setPages(firstPages)}>{text(row.student_name) || "Öğrenci"}</Link></td>
        <td>{kind === "records" ? <>Kan grubu: {text(row.blood_type) || "Belirtilmedi"}<p className="health-notes">Alerji: {text(row.allergies) || "Bilgi girilmedi"}</p></> : kind === "visits" ? <><p className="health-notes">{text(row.complaint) || "Açıklama girilmedi"}</p>{text(row.visit_time)}</> : kind === "schedules" ? <>{text(row.medicine_name)}<br />{text(row.dosage)} · {text(row.time_to_give)}</> : <>{text(row.medication_name) || "İlaç programı"}<br />Plan saati: {text(row.scheduled_time)}<br />{text(row.notes)}</>}</td>
        <td>{kind === "records" ? shortDate(row.updated_at) : kind === "visits" ? <>{shortDate(row.visit_date)}<br /><Badge value={row.severity} /></> : kind === "logs" ? <>{shortDate(row.scheduled_date || row.given_time || row.created_at)}<br /><Badge value={row.status} /></> : <Badge value={row.status} />}</td>
        <td><details><summary>Kaydı aç</summary>
          {kind === "records" && <><p className="health-notes">Kronik durum: {text(row.chronic_conditions) || "Bilgi girilmedi"}</p><p>Acil kişi: {text(row.emergency_contact_name) || "Belirtilmedi"} · {text(row.emergency_contact_phone)}</p><p>Yakınlık: {text(row.emergency_contact_relation) || "Belirtilmedi"}</p><p>Son kontrol: {shortDate(row.last_checkup_date)}</p>{row.insurance_info && <pre className="health-notes">{JSON.stringify(row.insurance_info, null, 2)}</pre>}<p>Güncelleyen: {text(row.updated_by_name) || "Eski kayıt"}</p></>}
          {kind === "visits" && <><p>Kaydeden: {text(row.examined_by_name) || "Eski kayıt"}</p>{row.temperature != null && <p>Ateş: {text(row.temperature)} °C</p>}{row.blood_pressure_systolic != null && <p>Tansiyon: {text(row.blood_pressure_systolic)} / {text(row.blood_pressure_diastolic)}</p>}<p className="health-notes">İşlem: {text(row.treatment_given) || "Bilgi girilmedi"}</p><p className="health-notes">Takip: {text(row.follow_up_notes) || "Not girilmedi"}</p><p>{row.follow_up_required ? "Takip bekliyor" : "Bekleyen takip yok"}</p><p>Manuel veli bilgisi: {row.parent_notified ? text(row.notification_method) : "Kaydedilmedi"}</p>
            {canWrite && row.follow_up_required && <form aria-label={`Revir takibini tamamla ${row.student_name}`} onSubmit={(event) => completeVisit(event, row)}><fieldset disabled={busy || loading} style={{ border: 0, padding: 0 }}>{note("Takip sonuç notu", "follow_up_notes", "", true)}<button className="btn btn-primary">Takibi tamamla</button></fieldset></form>}</>}
          {kind === "logs" && <><p>Kaydeden: {text(row.given_by_name) || "Eski kayıt"}</p><p>Uygulama zamanı: {row.given_time ? new Date(text(row.given_time)).toLocaleString("tr-TR") : "Uygulandı kaydı yok"}</p>{!row.scheduled_date && <p>Eski kayıtta doz günü ayrı tutulmamış; tarih mevcut zaman bilgisinden okunur.</p>}</>}
          {kind === "schedules" && <><p>{shortDate(row.start_date)} – {row.end_date ? shortDate(row.end_date) : "Bitiş girilmedi"}</p><p className="health-notes">Talimat: {text(row.instructions) || "Belirtilmedi"}</p><p>Karar veren: {text(row.updated_by_name) || "Henüz karar yok / eski kayıt"}</p>
            {canWrite && row.status === "PENDING" && <div className="toolbar"><button className="btn btn-primary" disabled={busy || loading} onClick={() => decideMedication(row, "APPROVED")}>İlaç talebini onayla</button><button className="btn btn-secondary" disabled={busy || loading} onClick={() => decideMedication(row, "REJECTED")}>İlaç talebini reddet</button></div>}
            {canWrite && row.status === "APPROVED" && <><form aria-label={`Doz kaydı ${row.medicine_name}`} onSubmit={(event) => recordDose(event, row)}><fieldset disabled={busy || loading || !today} style={{ border: 0, padding: 0, display: "grid", gap: 8 }}>
              <label>Doz günü<input className="filter-select" type="date" name="scheduled_date" value={today} readOnly /></label><label>Planlanan doz saati<input className="filter-select" type="time" name="scheduled_time" required /></label><label>Doz sonucu<select className="filter-select" aria-label="Doz sonucu" name="status"><option value="GIVEN">Uygulandı</option><option value="SKIPPED">Atlandı</option><option value="CANCELLED">İptal edildi</option></select></label>{note("Doz kayıt notu", "notes")}<button className="btn btn-primary">Doz sonucunu kaydet</button>
            </fieldset></form><button className="btn btn-secondary" disabled={busy || loading} onClick={() => decideMedication(row, "COMPLETED")}>Programı kapat</button></>}
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
      <label>Sağlık öğrencisi<select className="filter-select" aria-label="Sağlık öğrencisi" value={studentId} disabled={busy || !currentOptions} onChange={(event) => { setParams(event.target.value ? { student: event.target.value } : {}); setPages(firstPages); }}><option value="">Tüm öğrenciler</option>{options?.students.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <label>Ziyaret ve doz günü<input className="filter-select" type="date" value={day} disabled={busy} required onChange={(event) => { if (event.target.value) { setDay(event.target.value); setPages(firstPages); } }} /></label>
    </div>{options?.more_students && <p>İlk 100 öğrenci gösterilir. Diğer öğrencileri adla arayın.</p>}
      {currentOptions && "error" in currentOptions && <ErrorState message={currentOptions.error} retry={() => setOptionRevision((value) => value + 1)} />}
    </section>
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Revir özeti">
      {summary ? <p>Sağlık dosyası: {summary.total_records} · Bu ay ziyaret: {summary.recent_visits} · Bekleyen takip: {summary.follow_up_visits} · Bugün aktif program: {summary.active_schedules} · Bekleyen ilaç talebi: {summary.pending_requests}</p>
        : <p role="status">{error ? "Revir özeti doğrulanamadı." : "Revir özeti yükleniyor…"}</p>}
    </section>
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

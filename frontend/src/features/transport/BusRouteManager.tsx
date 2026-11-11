import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { Badge } from "../../components/ui";
import type { DataRecord } from "../../types/api";

const text = (value: unknown) => String(value ?? "");
const timeInput = (value: unknown) => text(value).replace(/(\.\d{3})\d+$/, "$1");
const fields = { display: "grid", gap: 12, border: 0, padding: 0 };
interface BusOptions { branches?: DataRecord[]; drivers?: DataRecord[]; students?: DataRecord[]; today?: string; more_students?: boolean; more_drivers?: boolean }
export function BusRouteManager({ routeId, canWrite, onClose, onRefresh }: { routeId: string | null; canWrite: boolean; onClose: () => void; onRefresh: () => void }) {
  const [route, setRoute] = useState<DataRecord | null>(null), [options, setOptions] = useState<BusOptions>({}), [stops, setStops] = useState<DataRecord[]>([]), [records, setRecords] = useState<DataRecord[]>([]), [telemetry, setTelemetry] = useState<DataRecord | null>(null);
  const [branch, setBranch] = useState(""), [driver, setDriver] = useState(""), [student, setStudent] = useState(""), [search, setSearch] = useState(""), [day, setDay] = useState("");
  const [driverSearch, setDriverSearch] = useState("");
  const [stop, setStop] = useState<DataRecord | null>(null), [page, setPage] = useState(1), [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState(""), [message, setMessage] = useState("");
  const [routeNonce, setRouteNonce] = useState(newRequestId), [stopNonce, setStopNonce] = useState(newRequestId), [eventNonce, setEventNonce] = useState(newRequestId);
  const [routeStatus, setRouteStatus] = useState<"loading" | "ready" | "error">(routeId ? "loading" : "ready");
  const loadedRouteVersion = useRef("");
  useEffect(() => {
    const controller = new AbortController();
    if (routeId) setRouteStatus("loading");
    if (routeId) api.get(`/bus/routes/${routeId}`, { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) {
        const version = `${routeId}:${text(response.data.data.updated_at)}`;
        if (loadedRouteVersion.current && loadedRouteVersion.current !== version) setRouteNonce(newRequestId());
        loadedRouteVersion.current = version;
        setRoute(response.data.data); setBranch(response.data.data.branch_id); setDriver(response.data.data.driver_id || ""); setRouteStatus("ready");
      }
    }).catch((reason) => { if (!controller.signal.aborted) { setError(apiMessage(reason)); setRouteStatus("error"); } });
    return () => controller.abort();
  }, [routeId, revision]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    (async () => {
      try {
        const response = await api.get("/bus/options", { params: { route_id: routeId || undefined, branch_id: branch || undefined, student_id: student || undefined, search,
          driver_search: driverSearch, driver_id: driver || undefined }, signal: controller.signal });
        if (controller.signal.aborted) return; setOptions(response.data.data || {}); setDay((current) => current || response.data.data.today); setError("");
      } catch (reason) { if (!controller.signal.aborted) setError(apiMessage(reason)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })(); return () => controller.abort();
  }, [routeId, branch, student, search, driverSearch, driver, revision]);
  useEffect(() => {
    if (!routeId || !day) return; const controller = new AbortController();
    Promise.all([api.get("/bus/stops", { params: { route_id: routeId, limit: 101, offset: (page - 1) * 100 }, signal: controller.signal }),
      api.get("/bus/attendance", { params: { route_id: routeId, attendance_date: day, student_id: student || undefined, limit: 100 }, signal: controller.signal }),
      api.get(`/bus/telemetry/${routeId}/latest`, { signal: controller.signal })]).then(([points, attendance, location]) => {
      if (!controller.signal.aborted) { setStops(points.data.data || []); setRecords(attendance.data.data || []); setTelemetry(location.data.data); }
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); });
    return () => controller.abort();
  }, [routeId, day, student, page, revision]);
  function refresh() { if (routeId) setRouteStatus("loading"); setRevision((value) => value + 1); onRefresh(); }
  async function save(event: FormEvent<HTMLFormElement>, kind: "route" | "stop" | "attendance" | "check-in") {
    event.preventDefault(); if (busy || !canWrite || (kind === "route" && routeStatus !== "ready") || (kind === "stop" && stop && !stop.version)) return;
    const form = event.currentTarget, values = Object.fromEntries(new FormData(form)); setBusy(true); setError(""); setMessage("");
    try {
      if (kind === "route") {
        const body = { ...values, branch_id: branch, driver_id: driver || null, capacity: Number(values.capacity), request_id: routeNonce, ...(route ? { expected_updated_at: route.updated_at } : {}) };
        if (routeId) await api.put(`/bus/routes/${routeId}`, body); else await api.post("/bus/routes", body);
        setRouteNonce(newRequestId()); refresh(); setMessage("Servis rotası kaydedildi"); if (!routeId) { onClose(); return; }
      } else if (kind === "stop") {
        const body = { ...values, route_id: routeId, stop_order: Number(values.stop_order), latitude: values.latitude ? Number(values.latitude) : null,
          longitude: values.longitude ? Number(values.longitude) : null,
          estimated_arrival: stop && values.estimated_arrival === timeInput(stop.estimated_arrival) ? stop.estimated_arrival || null : values.estimated_arrival || null, request_id: stopNonce,
          ...(stop ? { expected_version: stop.version } : {}) };
        if (stop) await api.put(`/bus/stops/${stop.id}`, body); else await api.post("/bus/stops", body);
        setStop(null); form.reset(); setStopNonce(newRequestId()); refresh(); setMessage("Durak kaydedildi");
      } else if (kind === "attendance") {
        await api.post("/bus/attendance", { ...values, route_id: routeId, student_id: student, attendance_date: day }); refresh(); setMessage("Servis katılımı kaydedildi");
      } else {
        await api.post("/bus/check-in", { ...values, route_id: routeId, student_id: student, request_id: eventNonce }); setEventNonce(newRequestId()); refresh(); setMessage("Biniş/iniş kaydedildi");
      }
    } catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  function input(label: string, name: string, value: unknown, type = "text", required = false, min?: number, max?: number) {
    return <label>{label}<input className="filter-select" name={name} type={type} defaultValue={type === "time" ? timeInput(value) : text(value)} required={required} min={min} max={max} step={type === "time" || type === "number" && ["latitude", "longitude"].includes(name) ? "any" : undefined} maxLength={name === "vehicle_plate" ? 20 : name === "route_number" ? 50 : 255} /></label>;
  }
  return <section className="card card-pad saas-workspace" aria-label="Servis rota yönetimi" style={{ marginTop: 18 }}>
    <h2>{routeId ? text(route?.route_name) || "Rota ayrıntıları" : "Yeni servis rotası"}</h2>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}><button className="btn btn-secondary" onClick={refresh} disabled={busy}>Rota verilerini yenile</button><button className="btn btn-secondary" onClick={onClose} disabled={busy}>Rota panelini kapat</button></div>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {routeStatus === "error" && <p role="alert">Rota bilgileri yüklenemedi. Kaydetmeden önce rota verilerini yenileyin.</p>}
    {canWrite && <><label>Rota sürücüsü ara<input className="filter-select" value={driverSearch} maxLength={100} disabled={busy}
      onChange={(event) => setDriverSearch(event.target.value)} /></label>{options.more_drivers && <p>Diğer sürücüler için ad veya soyadla arayın.</p>}</>}
    {canWrite && (!routeId || route) && <form aria-label="Servis rotasını kaydet" key={text(route?.updated_at) || "new"} onSubmit={(event) => save(event, "route")} onChange={() => setRouteNonce(newRequestId())}><fieldset disabled={busy || loading || routeStatus !== "ready"} style={fields}>
      <label>Rota şubesi<select className="filter-select" value={branch} required onChange={(event) => { setBranch(event.target.value); setDriver(""); setDriverSearch(""); }}><option value="">Şube seçin</option>{branch && !(options.branches || []).some((row) => row.id === branch) && <option value={branch}>{branch === route?.branch_id ? text(route.branch_name) || "Mevcut şube" : "Seçili şube"}</option>}{(options.branches || []).map((row: DataRecord) => <option key={row.id} value={row.id}>{text(row.name)}</option>)}</select></label>
      {input("Rota adı", "route_name", route?.route_name, "text", true)}{input("Rota numarası", "route_number", route?.route_number)}{input("Araç plakası", "vehicle_plate", route?.vehicle_plate)}{input("Araç kapasitesi", "capacity", route?.capacity ?? 40, "number", true, 1, 2147483647)}
      <label>Rota sürücüsü<select className="filter-select" value={driver} onChange={(event) => setDriver(event.target.value)}><option value="">Sürücü atanmamış</option>{driver && !(options.drivers || []).some((row: DataRecord) => row.id === driver) && <option value={driver}>Mevcut sürücü</option>}{(options.drivers || []).map((row: DataRecord) => <option key={row.id} value={row.id}>{text(row.name)}</option>)}</select></label>
      <label>Rota durumu<select className="filter-select" name="status" defaultValue={text(route?.status) || "ACTIVE"}><option value="ACTIVE">Aktif</option><option value="MAINTENANCE">Bakımda</option><option value="OUT_OF_SERVICE">Hizmet dışı</option></select></label>
      <label>Rota açıklaması<textarea className="filter-select" name="description" maxLength={1000} defaultValue={text(route?.description)} /></label><button className="btn btn-primary">Servis rotasını kaydet</button>
    </fieldset></form>}
    {routeId && <><section aria-label="Rota durakları"><h3>Duraklar</h3>{!stops.length ? <p>Henüz durak yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Sıra</th><th>Durak</th><th>Varış</th><th>İşlem</th></tr></thead><tbody>{stops.slice(0, 100).map((row) => <tr key={row.id}><td>{text(row.stop_order)}</td><td>{text(row.stop_name)}</td><td>{text(row.estimated_arrival) || "—"}</td><td>{canWrite && <button className="btn btn-secondary" onClick={() => { setStop(row); setStopNonce(newRequestId()); }}>Durağı düzenle</button>}</td></tr>)}</tbody></table></div>}
      <nav aria-label="Durak sayfaları"><button className="btn btn-secondary" disabled={busy || page === 1} onClick={() => setPage((value) => value - 1)}>Önceki duraklar</button><span> Sayfa {page} </span><button className="btn btn-secondary" disabled={busy || stops.length <= 100} onClick={() => setPage((value) => value + 1)}>Sonraki duraklar</button></nav></section>
      {canWrite && <form aria-label="Servis durağını kaydet" key={stop ? `${stop.id}:${stop.version}` : "new-stop"} onSubmit={(event) => save(event, "stop")} onChange={() => setStopNonce(newRequestId())}><h3>{stop ? "Durağı düzenle" : "Durak ekle"}</h3>{stop && !stop.version && <p role="alert">Durağın güncel sürümü alınamadı. Durak listesini yenileyip yeniden seçin.</p>}<fieldset disabled={busy || Boolean(stop && !stop.version)} style={fields}>
        {input("Durak adı", "stop_name", stop?.stop_name, "text", true)}{input("Durak sırası", "stop_order", stop?.stop_order, "number", true, 1, 2147483647)}{input("Durak enlemi", "latitude", stop?.latitude, "number", false, -90, 90)}{input("Durak boylamı", "longitude", stop?.longitude, "number", false, -180, 180)}{input("Tahmini varış saati", "estimated_arrival", stop?.estimated_arrival, "time")}
        <button className="btn btn-primary">Servis durağını kaydet</button>{stop && <button type="button" className="btn btn-secondary" onClick={() => setStop(null)}>Yeni durak</button>}
      </fieldset></form>}
      <section aria-label="Seçili rota katılımı"><h3>Öğrenci katılımı</h3><label>Katılım günü<input className="filter-select" type="date" value={day} onChange={(event) => setDay(event.target.value)} /></label><label>Servis öğrencisi ara<input className="filter-select" value={search} maxLength={100} onChange={(event) => setSearch(event.target.value)} /></label><label>Servis öğrencisi<select className="filter-select" value={student} onChange={(event) => { setStudent(event.target.value); setEventNonce(newRequestId()); }}><option value="">Öğrenci seçin</option>{(options.students || []).map((row: DataRecord) => <option key={row.id} value={row.id}>{text(row.name)} · {text(row.student_number)}</option>)}</select></label>{options.more_students && <p>Diğer öğrenciler için ad veya öğrenci numarasıyla arayın.</p>}
        {!records.length ? <p>Seçilen gün için katılım yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Öğrenci</th><th>Biniş</th><th>İniş</th><th>Durum</th></tr></thead><tbody>{records.map((row) => <tr key={row.id}><td>{text(row.student_name)}</td><td>{text(row.pickup_time) || "—"}</td><td>{text(row.dropoff_time) || "—"}</td><td><Badge value={row.status} /></td></tr>)}</tbody></table></div>}
        {canWrite && <><form aria-label="Servis katılımını kaydet" onSubmit={(event) => save(event, "attendance")}><fieldset disabled={busy || !student || !day} style={fields}><label>Katılım durumu<select className="filter-select" name="status"><option value="PRESENT">Geldi</option><option value="ABSENT">Gelmedi</option><option value="LATE">Geç geldi</option></select></label><button className="btn btn-primary">Servis katılımını kaydet</button></fieldset></form>
          {day === options.today && <form aria-label="Servis biniş iniş" onSubmit={(event) => save(event, "check-in")} onChange={() => setEventNonce(newRequestId())}><fieldset disabled={busy || !student} style={fields}><label>Şimdiki servis hareketi<select className="filter-select" name="event"><option value="BOARDED">Servise bindi</option><option value="DROPPED">Servisten indi</option></select></label><button className="btn btn-primary">Biniş veya inişi şimdi kaydet</button></fieldset></form>}
        </>}
        <p>Bu tabloda seçilen günün ilk 100 kaydı gösterilir. Belirli öğrenciyi seçerek kaydını görebilirsiniz.</p>
      </section>
      <section aria-label="Son servis konumu"><h3>Son konum</h3>{telemetry ? <p>Enlem: {text(telemetry.latitude)} · Boylam: {text(telemetry.longitude)} · Hız: {text(telemetry.speed)} · Kayıt: {text(telemetry.recorded_at)}</p> : <p>Henüz cihazdan konum kaydı gelmedi.</p>}</section>
    </>}
  </section>;
}

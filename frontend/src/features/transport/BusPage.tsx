import { Bus, MapPin, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import type { ApiResponse, DataRecord } from "../../types/api";
import { BusRouteManager } from "./BusRouteManager";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import { hasPermission } from "../../stores/auth";

export function BusPage() {
  const viewer = useWorkspaceUser(), canWrite = hasPermission(viewer, "bus.write");
  const [managing, setManaging] = useState<string | undefined>(undefined);
  const [routes, setRoutes] = useState<DataRecord[]>([]);
  const [attendance, setAttendance] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [search, setSearch] = useState(""), [page, setPage] = useState(1), [attendancePage, setAttendancePage] = useState(1);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      try {
        const [routesRes, attendanceRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/bus/routes", { params: { search, limit: 21, offset: (page - 1) * 20 }, signal: controller.signal }),
          api.get<ApiResponse<DataRecord[]>>("/bus/attendance?limit=50", { params: { offset: (attendancePage - 1) * 50 }, signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        setRoutes(routesRes.data.data || []); setAttendance(attendanceRes.data.data || []); setError("");
      } catch (reason) {
        if (!controller.signal.aborted) setError(apiMessage(reason));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [revision, search, page, attendancePage]);

  const names = new Map(routes.map((route) => [String(route.id), route.route_name]));
  return <>
    <PageHeader eyebrow="Ulaşım" title="Servis Yönetimi" description="Okul servis rotaları ve kaydedilmiş öğrenci katılımı" />
    {loading && !routes.length && <LoadingState label="Servis verileri yükleniyor" />}
    {error && <ErrorState message={error} retry={() => setRevision((value) => value + 1)} />}
    {canWrite && <button className="btn btn-primary" onClick={() => setManaging("new")}>Yeni servis rotası</button>}
    {managing && <BusRouteManager key={managing} routeId={managing === "new" ? null : managing} canWrite={canWrite} onClose={() => setManaging(undefined)} onRefresh={() => setRevision((value) => value + 1)} />}
    <section className="card card-pad" aria-label="Listelenen servis rotalarının özeti">
      <p>Listelenen rota: {routes.slice(0, 20).length} · Aktif rota: {routes.slice(0, 20).filter((route) => route.status === "ACTIVE").length} · Kapasite: {routes.slice(0, 20).reduce((sum, route) => sum + (Number(route.capacity) || 0), 0)}</p>
      <p>Özet bu sayfadaki rotaları kapsar. Rota ve katılım sayfalarını aşağıdan değiştirebilirsiniz.</p>
    </section>
    <section className="card" style={{ marginTop: 18 }} aria-label="Servis rotaları">
      <div className="card-head"><h2>Servis Rotaları</h2><span className="badge badge-green">{routes.length}</span></div>
      <div className="card-pad" style={{ overflowX: "auto" }}>
        <label>Servis rotası ara<input className="filter-select" maxLength={100} value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
        {!routes.length ? <p>Henüz rota oluşturulmadı.</p> : <table className="data-table">
          <thead><tr><th>Rota Adı</th><th>Plaka</th><th>Sürücü</th><th>Kapasite</th><th>Durum</th><th>İşlem</th></tr></thead>
          <tbody>{routes.slice(0, 20).map((route) => <tr key={route.id}>
            <td><Bus size={14} /> {String(route.route_name || "—")}</td><td>{String(route.vehicle_plate || "—")}</td>
            <td>{String(route.driver_name || "—")}</td><td><Users size={14} /> {String(route.capacity ?? "—")}</td>
            <td><Badge value={route.status} /></td>
            <td><button className="btn btn-secondary" onClick={() => setManaging(String(route.id))}>Rotayı aç</button></td>
          </tr>)}</tbody>
        </table>}
        <nav aria-label="Servis rota sayfaları"><button className="btn btn-secondary" disabled={loading || page === 1} onClick={() => setPage((value) => value - 1)}>Önceki rotalar</button><span> Sayfa {page} </span><button className="btn btn-secondary" disabled={loading || routes.length <= 20} onClick={() => setPage((value) => value + 1)}>Sonraki rotalar</button></nav>
      </div>
    </section>
    <section className="card" style={{ marginTop: 18 }} aria-label="Servis katılımları">
      <div className="card-head"><h2>Son Katılımlar</h2><span className="badge badge-green">{attendance.length}</span></div>
      <div className="card-pad" style={{ overflowX: "auto" }}>
        {!attendance.length ? <p>Henüz katılım kaydı yok.</p> : <table className="data-table">
          <thead><tr><th>Öğrenci</th><th>Rota</th><th>Tarih</th><th>Durum</th></tr></thead>
          <tbody>{attendance.map((record) => <tr key={record.id}>
            <td>{String(record.student_name || "—")}</td><td><MapPin size={14} /> {String(record.route_name || names.get(String(record.route_id)) || "Rota bilgisi listede yok")}</td>
            <td>{shortDate(record.date)}</td><td><Badge value={record.status} /></td>
          </tr>)}</tbody>
        </table>}
        <nav aria-label="Servis katılım sayfaları"><button className="btn btn-secondary" disabled={loading || attendancePage === 1} onClick={() => setAttendancePage((value) => value - 1)}>Önceki katılımlar</button><span> Sayfa {attendancePage} </span><button className="btn btn-secondary" disabled={loading || attendance.length < 50} onClick={() => setAttendancePage((value) => value + 1)}>Sonraki katılımlar</button></nav>
      </div>
    </section>
  </>;
}

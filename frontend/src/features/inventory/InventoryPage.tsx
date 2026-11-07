import { getAnalysis } from "../../lib/analysis";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";
import { InventoryWorkspace } from "./InventoryWorkspace";

function Pager({ label, page, more, busy, onChange }: { label: string; page: number; more: boolean; busy: boolean; onChange: (page: number) => void }) {
  if (!more && page === 1) return null;
  return <div className="toolbar" aria-label={label}>
    <button className="btn btn-secondary" disabled={busy || page === 1} onClick={() => onChange(page - 1)}>Önceki</button>
    <span>Sayfa {page}</span><button className="btn btn-secondary" disabled={busy || !more} onClick={() => onChange(page + 1)}>Sonraki</button>
  </div>;
}

export function InventoryPage() {
  const canWrite = useAuthStore((state) => state.can("inventory.write"));
  const [items, setItems] = useState<DataRecord[]>([]);
  const [assignments, setAssignments] = useState<DataRecord[]>([]);
  const [maintenance, setMaintenance] = useState<DataRecord[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [itemPage, setItemPage] = useState(1);
  const [assignmentPage, setAssignmentPage] = useState(1);
  const [maintenancePage, setMaintenancePage] = useState(1);
  const [more, setMore] = useState([false, false, false]);
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);
  const { showToast } = useToast();
  const load = useCallback(async () => {
    const request = ++sequence.current;
    setRefreshing(true); setError("");
    try {
      const [assets, assigned, requests, statistics] = await Promise.all([
        api.get("/inventory/items", { params: { limit: 21, offset: (itemPage - 1) * 20 } }),
        api.get("/inventory/assignments", { params: { limit: 21, offset: (assignmentPage - 1) * 20 } }),
        api.get("/inventory/maintenance-requests", { params: { limit: 21, offset: (maintenancePage - 1) * 20 } }),
        getAnalysis("/ai/inventory-analysis"),
      ]);
      if (request !== sequence.current) return;
      setItems((assets.data.data || []).slice(0, 20)); setAssignments((assigned.data.data || []).slice(0, 20));
      setMaintenance((requests.data.data || []).slice(0, 20)); setSummary(statistics.data.data);
      setMore([assets.data.data.length > 20, assigned.data.data.length > 20, requests.data.data.length > 20]);
    } catch (reason) { if (request === sequence.current) setError(apiMessage(reason)); }
    finally { if (request === sequence.current) { setLoading(false); setRefreshing(false); } }
  }, [itemPage, assignmentPage, maintenancePage]);
  useEffect(() => { void load(); }, [load]);
  const changed = async () => { setRevision((value) => value + 1); await load(); };
  async function finish(row: DataRecord, kind: "assignment" | "maintenance") {
    if (!window.confirm(kind === "assignment" ? "Demirbaşın iadesi kaydedilsin mi?" : "Bakım tamamlandı olarak kaydedilsin mi?")) return;
    setBusy(String(row.id));
    try {
      await api.post(kind === "assignment" ? "/inventory/assignments/" + row.id + "/return" : "/inventory/maintenance-requests/" + row.id + "/resolve");
      await changed(); showToast("Envanter kaydı güncellendi");
    } catch (reason) { showToast("İşlem tamamlanamadı", apiMessage(reason), "error"); }
    finally { setBusy(""); }
  }
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={() => void load()} />;
  return <>
    <PageHeader eyebrow="Envanter" title="Demirbaş & Envanter" description="Demirbaşlar, konumlar, zimmetler ve bakım talepleri" />
    {summary && <section className="card card-pad" aria-label="Envanter özeti">
      <h2>Envanter özeti</h2><div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 16 }}>
        {[["Toplam kalem", summary.total_items], ["Zimmetli", summary.assigned_count], ["Kullanılabilir", summary.available_count], ["Açık bakım", summary.pending_maintenance]].map(([label, value]) =>
          <div key={String(label)}><p>{String(label)}</p><strong style={{ fontSize: 26 }}>{String(value ?? 0)}</strong></div>)}
      </div>
    </section>}
    <InventoryWorkspace revision={revision} onChange={changed} />
    <section className="card" aria-label="Envanter kalemleri" style={{ marginTop: 20 }}><div className="card-head"><h2>Envanter Kalemleri</h2></div>
      <div className="card-pad table-wrap">{items.length === 0 ? <p>Henüz envanter kalemi yok.</p> : <table className="data-table"><thead><tr><th>Kod</th><th>Ad</th><th>Kategori</th><th>Konum</th><th>Durum</th></tr></thead><tbody>
        {items.map((row) => <tr key={row.id}><td>{String(row.item_code)}</td><td>{String(row.item_name)}</td><td>{String(row.category || "—")}</td><td>{String(row.location_name || "—")}</td><td><Badge value={row.status} /></td></tr>)}
      </tbody></table>}</div><Pager label="Demirbaş sayfaları" page={itemPage} more={more[0]} busy={refreshing} onChange={setItemPage} />
    </section>
    <section className="card" aria-label="Demirbaş zimmetleri" style={{ marginTop: 20 }}><div className="card-head"><h2>Zimmetler</h2></div>
      <div className="card-pad table-wrap">{assignments.length === 0 ? <p>Henüz zimmet yok.</p> : <table className="data-table"><thead><tr><th>Demirbaş</th><th>Sorumlu</th><th>Zimmet tarihi</th><th>İade tarihi</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>
        {assignments.map((row) => <tr key={row.id}><td>{String(row.item_name || "—")}</td><td>{String(row.assigned_to_name || "—")}</td><td>{shortDate(row.assigned_date)}</td><td>{row.return_date ? (row.status === "ASSIGNED" ? "Planlanan: " : "") + shortDate(row.return_date) : "—"}</td><td><Badge value={row.status} /></td><td>
          {canWrite && row.status === "ASSIGNED" && <button className="btn btn-secondary" disabled={Boolean(busy)} aria-label={String(row.item_name) + " iade al"} onClick={() => finish(row, "assignment")}>İade al</button>}
        </td></tr>)}
      </tbody></table>}</div><Pager label="Zimmet sayfaları" page={assignmentPage} more={more[1]} busy={refreshing} onChange={setAssignmentPage} />
    </section>
    <section className="card" aria-label="Demirbaş bakım talepleri" style={{ marginTop: 20 }}><div className="card-head"><h2>Bakım Talepleri</h2></div>
      <div className="card-pad table-wrap">{maintenance.length === 0 ? <p>Henüz bakım talebi yok.</p> : <table className="data-table"><thead><tr><th>Demirbaş</th><th>Açıklama</th><th>Öncelik</th><th>Sorumlu</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>
        {maintenance.map((row) => <tr key={row.id}><td>{String(row.item_name || "—")}</td><td>{String(row.issue_description)}</td><td><Badge value={row.priority} /></td><td>{String(row.assigned_to_name || "—")}</td><td><Badge value={row.status} /></td><td>
          {canWrite && row.status !== "RESOLVED" && <button className="btn btn-secondary" disabled={Boolean(busy)} aria-label={String(row.item_name) + " bakımını tamamla"} onClick={() => finish(row, "maintenance")}>Tamamla</button>}
        </td></tr>)}
      </tbody></table>}</div><Pager label="Bakım sayfaları" page={maintenancePage} more={more[2]} busy={refreshing} onChange={setMaintenancePage} />
    </section>
  </>;
}

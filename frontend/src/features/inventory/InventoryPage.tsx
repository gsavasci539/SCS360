import { Package, MapPin } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function InventoryPage() {
  const [items, setItems] = useState<DataRecord[]>([]);
  const [assignments, setAssignments] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [itemsRes, assignmentsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/inventory/items"),
          api.get<ApiResponse<DataRecord[]>>("/inventory/assignments?limit=50")
        ]);
        setItems(itemsRes.data.data || []);
        setAssignments(assignmentsRes.data.data || []);
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="card"><LoadingState label="Yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Envanter"
        title="Demirbaş & Envanter"
        description="Demirbaşlar, envanter ve atama yönetimi"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Envanter Kalemleri</h2>
          <span className="badge badge-green">{String(items.length)}</span>
        </div>
        <div className="card-pad">
          {items.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz envanter kalemi yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Kod</th>
                  <th>Ad</th>
                  <th>Kategori</th>
                  <th>Konum</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{String(item.item_code)}</td>
                    <td><Package size={14} /> {String(item.item_name)}</td>
                    <td>{String(item.category)}</td>
                    <td><MapPin size={14} /> {String(item.location_name)}</td>
                    <td><Badge value={String(item.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Atamalar</h2>
          <span className="badge badge-green">{String(assignments.length)}</span>
        </div>
        <div className="card-pad">
          {assignments.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz atama yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Kalem</th>
                  <th>Atanan Kişi</th>
                  <th>Atama Tarihi</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((assignment) => (
                  <tr key={assignment.id}>
                    <td>{String(assignment.item_name)}</td>
                    <td>{String(assignment.assigned_to_name)}</td>
                    <td>{String(assignment.assigned_date)}</td>
                    <td><Badge value={String(assignment.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

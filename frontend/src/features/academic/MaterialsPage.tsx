import { BookOpen, Download, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function MaterialsPage() {
  const [materials, setMaterials] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.get<ApiResponse<DataRecord[]>>("/materials");
        setMaterials(res.data.data || []);
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
        eyebrow="Akademik"
        title="Ders Materyalleri"
        description="Ders notları, kaynaklar ve dijital kütüphane"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Materyaller</h2>
          <span className="badge badge-green">{String(materials.length)}</span>
        </div>
        <div className="card-pad">
          {materials.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz materyal yüklenmedi</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Başlık</th>
                  <th>Ders</th>
                  <th>Tür</th>
                  <th>Yükleme Tarihi</th>
                  <th>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((material) => (
                  <tr key={material.id}>
                    <td><BookOpen size={14} /> {String(material.title)}</td>
                    <td>{String(material.subject_name)}</td>
                    <td><Badge value={String(material.material_type)} /></td>
                    <td>{String(material.uploaded_at)}</td>
                    <td><Download size={14} /></td>
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

import { FileText, CheckCircle, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ConsentsPage() {
  const [documents, setDocuments] = useState<DataRecord[]>([]);
  const [consents, setConsents] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [documentsRes, consentsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/consents/documents"),
          api.get<ApiResponse<DataRecord[]>>("/consents/student-consents?limit=50")
        ]);
        setDocuments(documentsRes.data.data || []);
        setConsents(consentsRes.data.data || []);
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
        eyebrow="KVKK"
        title="Veli Onay Masası"
        description="KVKK aydınlatma metinleri ve veli onayları"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Onay Belgeleri</h2>
          <span className="badge badge-green">{String(documents.length)}</span>
        </div>
        <div className="card-pad">
          {documents.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz onay belgesi oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Belge Başlığı</th>
                  <th>Tür</th>
                  <th>Sürüm</th>
                  <th>Yürürlük Tarihi</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td><FileText size={14} /> {String(doc.title)}</td>
                    <td>{String(doc.document_type)}</td>
                    <td>{String(doc.version)}</td>
                    <td>{String(doc.effective_date)}</td>
                    <td><Badge value={doc.is_active ? "ACTIVE" : "INACTIVE"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Veli Onayları</h2>
          <span className="badge badge-green">{String(consents.length)}</span>
        </div>
        <div className="card-pad">
          {consents.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz onay kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Belge</th>
                  <th>Veli</th>
                  <th>Onay Tarihi</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {consents.map((consent) => (
                  <tr key={consent.id}>
                    <td>{String(consent.student_name)}</td>
                    <td>{String(consent.document_title)}</td>
                    <td>{String(consent.parent_name)}</td>
                    <td><Clock size={14} /> {String(consent.consented_at)}</td>
                    <td><CheckCircle size={14} /> <Badge value={String(consent.consent_status)} /></td>
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

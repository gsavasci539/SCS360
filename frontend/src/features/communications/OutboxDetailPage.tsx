import { ArrowLeft, Mail, MessageSquare, Phone, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuthStore } from "../../stores/auth";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useToast } from "../../components/Toast";
import type { ApiResponse, DataRecord } from "../../types/api";

export function OutboxDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { showToast } = useToast();
  const navigate = useNavigate();
  const can = useAuthStore((state) => state.can);

  async function load() {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/outbox/${id}`);
      setData(r.data.data);
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function handleDelete() {
    try {
      await api.delete(`/outbox/${id}`);
      showToast("Mesaj silindi", "Mesaj başarıyla silindi.");
      navigate("/outbox");
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;
  if (!data) return <div className="card"><ErrorState message="Mesaj bulunamadı" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Mesaj Detayı"
        description="Gönderilmiş mesajın detayları."
      >
        <Link to="/outbox" className="btn btn-secondary">
          <ArrowLeft size={16} />Geri Dön
        </Link>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 10, color: "var(--brand)", background: "#e9f3ef" }}>
              {data.type === "E-posta" ? <Mail size={20} /> : data.type === "SMS" ? <Phone size={20} /> : <MessageSquare size={20} />}
            </div>
            <div>
              <h2>{String(data.subject)}</h2>
              <p style={{ color: "var(--muted)", fontSize: 12 }}>{String(data.type)}</p>
            </div>
          </div>
          {can("notification.write") && <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={16} />Sil
          </button>}
        </div>
        <div className="card-pad">
          <div style={{ display: "grid", gap: 16 }}>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Alıcı</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.recipient)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Gönderim Tarihi</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.sent_at)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Durum</small>
              <span className="badge badge-green">{String(data.status)}</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

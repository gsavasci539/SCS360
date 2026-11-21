import { ArrowLeft, Mail, MessageSquare, Phone, RotateCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuthStore } from "../../stores/auth";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useToast } from "../../components/Toast";
import type { ApiResponse, DataRecord } from "../../types/api";
import { deleteOutboxRecord, outboxScope, outboxStatuses } from "./outboxRecords";

export function OutboxDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { showToast } = useToast();
  const navigate = useNavigate();
  const can = useAuthStore((state) => state.can);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/outbox/${id}`, { signal });
      if (signal?.aborted) return;
      if (r.data.data?.id !== id) throw new Error("Gönderim kaydı doğrulanamadı.");
      setData(r.data.data);
    } catch (e) {
      if (!signal?.aborted) setError(apiMessage(e));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function handleDelete() {
    if (!data || busy || !can("notification.write") || !window.confirm("Gönderim kaydı kaldırılsın mı?")) return;
    setBusy(true);
    try {
      await deleteOutboxRecord(data);
      showToast("Gönderim kaydı kaldırıldı");
      navigate("/outbox");
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    } finally { setBusy(false); }
  }

  async function handleRetry() {
    if (!data || busy || !can("notification.write") || !["FAILED", "CANCELLED"].includes(String(data.status))) return;
    setBusy(true);
    try {
      const params = outboxScope(data);
      const ack = await api.post<ApiResponse<DataRecord>>(`/outbox/retry/${data.id}`, {}, { params });
      if (ack.data.data?.id !== data.id || ack.data.data.job_id !== data.job_id || ack.data.data.status !== "PENDING" ||
          ack.data.data.sent_at) throw new Error("Kuyruk kaydı doğrulanamadı.");
      const response = await api.get<ApiResponse<DataRecord>>(`/outbox/${data.id}`, { params });
      const stored = response.data.data;
      if (stored?.id !== data.id || stored.job_id !== data.job_id) throw new Error("Güncel gönderim kaydı doğrulanamadı.");
      setData(stored);
      showToast("Kuyruk isteği doğrulandı", outboxStatuses[String(stored.status)] || String(stored.status));
    } catch (e) {
      showToast("Kuyruğa alınamadı", apiMessage(e), "error");
    } finally { setBusy(false); }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={() => void load()} /></div>;
  if (!data) return <div className="card"><ErrorState message="Mesaj bulunamadı" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Mesaj Detayı"
        description="Gönderim kaydı ve sağlayıcı durumu."
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
          {can("notification.write") && <div className="table-actions">
            {["FAILED", "CANCELLED"].includes(String(data.status)) && <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleRetry}>
              <RotateCw size={16} />Yeniden kuyruğa al
            </button>}
            <button type="button" className="btn btn-danger" disabled={busy} onClick={handleDelete}><Trash2 size={16} />Kaldır</button>
          </div>}
        </div>
        <div className="card-pad">
          <div style={{ display: "grid", gap: 16 }}>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Alıcı</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.recipient)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Gönderim Tarihi</small>
              <strong style={{ display: "block", fontSize: 13 }}>{data.sent_at ? String(data.sent_at) : "Henüz sağlayıcı kabulü yok"}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Durum</small>
              <span>{outboxStatuses[String(data.status)] || String(data.status)}</span>
            </div>
            {data.error_message && <p style={{ overflowWrap: "anywhere" }}>{String(data.error_message)}</p>}
          </div>
        </div>
      </div>
    </>
  );
}

import { ArrowLeft, Bell, Mail, MessageCircle, Send, RefreshCw } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, Badge } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import type { ApiResponse } from "../../types/api";
import { useAnnouncementScope } from "./useAnnouncementScope";

interface Announcement {
  id: string;
  title: string;
  content: string;
  audience: string;
  channels: string[];
  scheduled_at?: string;
  sent_at?: string;
  status: string;
  recipient_count?: number;
  sent_count?: number;
  failed_count?: number;
}

interface SendResult {
  job_id: string;
  channel: string;
  sent: number;
  failed: number;
  pending: number;
  error?: string | null;
}

export function AnnouncementDetailPage() {
  const { id } = useParams();
  const scope = useAnnouncementScope();
  if (!id || !scope.active || !scope.canRead) return <p>Duyuru kayıtları için yetkili kurum çalışma alanını açın.</p>;
  return <AnnouncementDetail key={JSON.stringify([scope.key, id])} id={id} canWrite={scope.canWrite} />;
}

function AnnouncementDetail({ id, canWrite }: { id: string; canWrite: boolean }) {
  const [announcement, setAnnouncement] = useState<Announcement | null>(null);
  const [results, setResults] = useState<SendResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [retryNotice, setRetryNotice] = useState("");
  const pending = useRef<AbortController | null>(null);
  const { showToast } = useToast();
  const path = `/announcements/${encodeURIComponent(id)}`;

  useLayoutEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    setLoading(true);
    setError("");
    async function load() {
      try {
        const response = await api.get<ApiResponse<Announcement>>(path, { signal });
        if (signal.aborted) return;
        const record = response.data.data;
        if (record?.id !== id) throw new Error("Sunucu seçili duyuruyu doğrulamadı.");
        const delivery = record.status === "SENT"
          ? (await api.get<ApiResponse<SendResult[]>>(`${path}/results`, { signal })).data.data
          : [];
        if (signal.aborted) return;
        if (!Array.isArray(delivery) || delivery.some((row) =>
          !row?.job_id || ![row.sent, row.failed, row.pending].every((count) => Number.isInteger(count) && count >= 0))) {
          throw new Error("Sunucu gönderim sonuçlarını doğrulamadı.");
        }
        setAnnouncement(record);
        setResults(delivery);
      } catch (err) {
        if (!signal.aborted) setError(apiMessage(err));
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [id, path, attempt]);

  async function retryFailed() {
    if (!canWrite || pending.current || !results.some((row) => row.failed > 0)) return;
    const controller = new AbortController();
    const { signal } = controller;
    pending.current = controller;
    setRetrying(true);
    setRetryNotice("");
    try {
      const response = await api.post<ApiResponse<{ announcement_id: string; recipients_retried: number }>>(
        `${path}/retry`, undefined, { signal },
      );
      if (signal.aborted) return;
      const outcome = response.data.data;
      if (outcome?.announcement_id !== id || !Number.isInteger(outcome.recipients_retried) || outcome.recipients_retried < 0) {
        throw new Error("Sunucu seçili duyurunun kuyruk işlemini doğrulamadı.");
      }
      if (outcome.recipients_retried > 0) {
        showToast("Gönderimler kuyruğa alındı", `${outcome.recipients_retried} alıcı`);
      } else {
        setRetryNotice("Şu anda yeniden kuyruğa alınabilecek gönderim yok.");
      }
      setLoading(true);
      setAttempt((value) => value + 1);
    } catch (err) {
      if (!signal.aborted) showToast("Yeniden deneme başlatılamadı", apiMessage(err), "error");
    } finally {
      pending.current = null;
      if (!signal.aborted) setRetrying(false);
    }
  }

  if (loading) return <div className="card"><LoadingState label="Duyuru yükleniyor" /></div>;
  if (error || !announcement) return <div className="card"><ErrorState message={error || "Duyuru bulunamadı."} /></div>;

  const channelIcons = {
    EMAIL: <Mail size={16} />,
    SMS: <MessageCircle size={16} />,
    WHATSAPP: <MessageCircle size={16} />
  };

  return (
    <>
      <PageHeader
        eyebrow="Duyuru detayı"
        title={announcement.title}
        description="Duyuru içeriği, gönderim durumu ve alıcı sonuçları."
      >
        <Link className="btn btn-secondary" to="/announcements">
          <ArrowLeft size={16} />Listeye dön
        </Link>
        {canWrite && announcement.status === "SENT" && results.some((r) => r.failed > 0) && (
          <button className="btn btn-primary" onClick={retryFailed} disabled={retrying}>
            {retrying ? <><RefreshCw size={16} className="spin" />Yeniden deneniyor...</> : <><RefreshCw size={16} />Başarısızları yeniden dene</>}
          </button>
        )}
      </PageHeader>
      {retryNotice && <p role="status">{retryNotice}</p>}

      <div className="grid dashboard-grid">
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Duyuru bilgileri</h2>
              <p>İçerik ve gönderim ayarları</p>
            </div>
          </div>
          <div className="card-pad detail-list">
            <div className="detail-item">
              <small>Durum</small>
              <strong><Badge value={announcement.status} /></strong>
            </div>
            <div className="detail-item">
              <small>Hedef kitle</small>
              <strong>{announcement.audience}</strong>
            </div>
            <div className="detail-item">
              <small>Kanallar</small>
              <strong>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {announcement.channels.map((channel) => (
                    <span key={channel} className="badge badge-neutral">
                      {channelIcons[channel as keyof typeof channelIcons]}
                      <span style={{ marginLeft: 4 }}>{channel}</span>
                    </span>
                  ))}
                </div>
              </strong>
            </div>
            {announcement.scheduled_at && (
              <div className="detail-item">
                <small>Planlanan tarih</small>
                <strong>{shortDate(announcement.scheduled_at)}</strong>
              </div>
            )}
            {announcement.sent_at && (
              <div className="detail-item">
                <small>Gönderim tarihi</small>
                <strong>{shortDate(announcement.sent_at)}</strong>
              </div>
            )}
          </div>
          <div className="card-pad" style={{ borderTop: "1px solid #e7ece8" }}>
            <h3 style={{ font: "600 14px Manrope", marginBottom: 12 }}>İçerik</h3>
            <div
              style={{
                padding: 16,
                background: "#f8f9fa",
                borderRadius: 8,
                fontSize: 14,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap"
              }}
            >
              {announcement.content}
            </div>
          </div>
        </section>

        <aside className="card">
          <div className="card-head">
            <div>
              <h2>Gönderim sonuçları</h2>
              <p>Kanallara göre gönderim istatistikleri</p>
            </div>
          </div>
          <div className="card-pad">
            {announcement.status !== "SENT" ? (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <Bell size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
                <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Gönderim kaydı yok</h3>
              </div>
            ) : results.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <Send size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
                <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Sonuç kaydı yok</h3>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {results.map((result) => (
                  <div
                    key={result.job_id}
                    style={{
                      padding: 12,
                      background: "#f8f9fa",
                      borderRadius: 8,
                      border: "1px solid #e7ece8"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      {channelIcons[result.channel as keyof typeof channelIcons]}
                      <strong>{result.channel}</strong>
                    </div>
                    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 13 }}>
                      <span style={{ color: "#176b5b" }}>✓ {result.sent} gönderildi</span>
                      {result.failed > 0 && (
                        <span style={{ color: "#b14545" }}>✗ {result.failed} başarısız</span>
                      )}
                      {result.pending > 0 && <span>{result.pending} bekliyor</span>}
                    </div>
                    {result.error && (
                      <div style={{ marginTop: 8, fontSize: 12, color: "#b14545" }}>
                        {result.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

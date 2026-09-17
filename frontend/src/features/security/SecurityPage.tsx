import { QrCode, Shield, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, AddButton, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";

export function SecurityPage() {
  const [tokens, setTokens] = useState<DataRecord[]>([]);
  const [gateLogs, setGateLogs] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const can = useAuthStore((state) => state.can);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [tokensRes, logsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/security/digital-ids"),
          api.get<ApiResponse<DataRecord[]>>("/security/gate-logs?limit=50")
        ]);
        setTokens(tokensRes.data.data || []);
        setGateLogs(logsRes.data.data || []);
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
        eyebrow="Güvenlik"
        title="Digital ID & Gate Validator"
        description="Öğrenci kimlik kartları ve kapı geçiş sistemi yönetimi"
      >
        {can("security.write") && (
          <AddButton to="/security/digital-ids/new" label="Digital ID Oluştur" />
        )}
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Active Digital IDs</h2>
          <span className="badge badge-green">{String(tokens.length)}</span>
        </div>
        <div className="card-pad">
          {tokens.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz digital ID oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>QR Code</th>
                  <th>Valid Until</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((token) => (
                  <tr key={token.id}>
                    <td>{String(token.student_name)}</td>
                    <td><QrCode size={16} /> {String(token.qr_code)}</td>
                    <td>{String(token.valid_until)}</td>
                    <td><Badge value={String(token.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Recent Gate Logs</h2>
          <Shield size={16} />
        </div>
        <div className="card-pad">
          {gateLogs.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz geçiş kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Direction</th>
                  <th>Gate</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {gateLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{String(log.student_name)}</td>
                    <td><Badge value={String(log.direction)} /></td>
                    <td>{String(log.gate_name)}</td>
                    <td><Clock size={14} /> {String(log.passed_at)}</td>
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

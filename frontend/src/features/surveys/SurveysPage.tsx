import { FileText, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function SurveysPage() {
  const [surveys, setSurveys] = useState<DataRecord[]>([]);
  const [responses, setResponses] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [surveysRes, responsesRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/surveys/surveys"),
          api.get<ApiResponse<DataRecord[]>>("/surveys/responses?limit=50")
        ]);
        setSurveys(surveysRes.data.data || []);
        setResponses(responsesRes.data.data || []);
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
        eyebrow="Anketler"
        title="Anket & Geri Bildirim"
        description="Anketler, sorular ve yanıtlar yönetimi"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Anketler</h2>
          <span className="badge badge-green">{String(surveys.length)}</span>
        </div>
        <div className="card-pad">
          {surveys.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz anket oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Başlık</th>
                  <th>Hedef Kitle</th>
                  <th>Başlangıç</th>
                  <th>Bitiş</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {surveys.map((survey) => (
                  <tr key={survey.id}>
                    <td><FileText size={14} /> {String(survey.title)}</td>
                    <td>{String(survey.target_audience)}</td>
                    <td>{String(survey.start_date)}</td>
                    <td>{String(survey.end_date)}</td>
                    <td><Badge value={String(survey.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Yanıtlar</h2>
          <span className="badge badge-green">{String(responses.length)}</span>
        </div>
        <div className="card-pad">
          {responses.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz yanıt yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Anket</th>
                  <th>Katılımcı</th>
                  <th>Gönderim Tarihi</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {responses.map((response) => (
                  <tr key={response.id}>
                    <td>{String(response.survey_title)}</td>
                    <td><Users size={14} /> {String(response.respondent_name)}</td>
                    <td>{String(response.submitted_at)}</td>
                    <td><Badge value="COMPLETED" /></td>
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

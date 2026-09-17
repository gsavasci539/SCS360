import { useState, useEffect } from "react";
import { Plus } from "lucide-react";
import { api, apiMessage } from "../../lib/api";
import { PageHeader, LoadingState, ErrorState, Badge, Tabs } from "../../components/ui";

interface MedicineRequest {
  id: string;
  student_id: string;
  student_name: string;
  medicine_name: string;
  dosage: string;
  time_to_give: string;
  instructions: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'COMPLETED';
  created_at: string;
}

interface HealthRecord {
  id: string;
  student_id: string;
  student_name: string;
  visit_date: string;
  complaint: string;
  diagnosis: string;
  treatment: string;
  follow_up_required: boolean;
}

export default function InfirmaryPage() {
  const [activeTab, setActiveTab] = useState("requests");
  const [medicineRequests, setMedicineRequests] = useState<MedicineRequest[]>([]);
  const [healthRecords, setHealthRecords] = useState<HealthRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [requestsResult, recordsResult] = await Promise.allSettled([
        api.get("/api/infirmary/medicine-requests"),
        api.get("/api/infirmary/infirmary-visits")
      ]);
      if (requestsResult.status === "fulfilled") {
        setMedicineRequests(requestsResult.value.data.data || []);
      }
      if (recordsResult.status === "fulfilled") {
        // Map infirmary visits to health records format
        const visits = recordsResult.value.data.data || [];
        setHealthRecords(visits.map((visit: any) => ({
          id: visit.id,
          student_id: visit.student_id,
          student_name: visit.student_name,
          visit_date: visit.visit_date,
          complaint: visit.complaint,
          diagnosis: visit.treatment_given || "Belirtilmedi",
          treatment: visit.treatment_given || "",
          follow_up_required: visit.follow_up_required
        })));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (requestId: string, status: string) => {
    try {
      await api.put(`/api/infirmary/medicine-requests/${requestId}`, { status });
      load();
    } catch (err) {
      setError(apiMessage(err));
    }
  };

  if (loading) return <LoadingState label="Yükleniyor..." />;
  if (error) return <ErrorState message={error} retry={load} />;

  return (
    <>
      <PageHeader
        eyebrow="Sağlık Hizmetleri"
        title="Sağlık Oda"
        description="İlaç talepleri ve sağlık kayıtları yönetimi"
      />

      <div className="card">
        <Tabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          tabs={[
            { id: "requests", label: "İlaç Talepleri" },
            { id: "records", label: "Sağlık Kayıtları" }
          ]}
        />

        {activeTab === "requests" && (
          <div className="tab-content">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>İlaç Adı</th>
                  <th>Doz</th>
                  <th>Saat</th>
                  <th>Durum</th>
                  <th>İşlemler</th>
                </tr>
              </thead>
              <tbody>
                {medicineRequests.map((req) => (
                  <tr key={req.id}>
                    <td>{req.student_name}</td>
                    <td>{req.medicine_name}</td>
                    <td>{req.dosage}</td>
                    <td>{req.time_to_give}</td>
                    <td><Badge value={req.status} /></td>
                    <td>
                      <div className="flex gap-2">
                        {req.status === "PENDING" && (
                          <>
                            <button
                              className="btn btn-sm btn-success"
                              onClick={() => handleStatusChange(req.id, "APPROVED")}
                            >
                              Onayla
                            </button>
                            <button
                              className="btn btn-sm btn-danger"
                              onClick={() => handleStatusChange(req.id, "REJECTED")}
                            >
                              Reddet
                            </button>
                          </>
                        )}
                        {req.status === "APPROVED" && (
                          <button
                            className="btn btn-sm"
                            onClick={() => handleStatusChange(req.id, "COMPLETED")}
                          >
                            Verildi
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "records" && (
          <div className="tab-content">
            <div className="flex justify-between items-center mb-4">
              <h3>Sağlık Kayıtları</h3>
              <button className="btn btn-primary">
                <Plus size={16} /> Yeni Kayıt
              </button>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Ziyaret Tarihi</th>
                  <th>Şikayet</th>
                  <th>Tanı</th>
                  <th>Tedavi</th>
                  <th>Takip Gerekli</th>
                </tr>
              </thead>
              <tbody>
                {healthRecords.map((record) => (
                  <tr key={record.id}>
                    <td>{record.student_name}</td>
                    <td>{new Date(record.visit_date).toLocaleDateString("tr-TR")}</td>
                    <td>{record.complaint}</td>
                    <td>{record.diagnosis}</td>
                    <td>{record.treatment}</td>
                    <td><Badge value={record.follow_up_required ? "YES" : "NO"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

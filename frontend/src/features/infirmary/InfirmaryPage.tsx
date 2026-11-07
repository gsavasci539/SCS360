import { useState, useEffect } from "react";
import { Plus } from "lucide-react";
import { api, apiMessage } from "../../lib/api";
import { PageHeader, LoadingState, ErrorState, Badge, Tabs, Modal, Field } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { useForm } from "react-hook-form";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

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
  const [createOpen, setCreateOpen] = useState(false);
  const [students, setStudents] = useState<DataRecord[]>([]);
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [requestsResult, recordsResult] = await Promise.allSettled([
        api.get("/infirmary/medicine-requests"),
        api.get("/infirmary/infirmary-visits")
      ]);
      if (requestsResult.status === "fulfilled") {
        const requestData = requestsResult.value.data.data;
        // Handle both array and paginated response formats
        setMedicineRequests(Array.isArray(requestData) ? requestData : (requestData?.items || []));
      }
      if (recordsResult.status === "fulfilled") {
        // Map infirmary visits to health records format
        const recordsData = recordsResult.value.data.data;
        const visits = Array.isArray(recordsData) ? recordsData : (recordsData?.items || []);
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
      const studentsResult = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/students", { params: { page_size: 200 } });
      const studentData = studentsResult.data.data;
      setStudents(Array.isArray(studentData) ? studentData : studentData.items);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const handleStatusChange = async (requestId: string, status: string) => {
    try {
      await api.put(`/infirmary/medicine-requests/${requestId}`, { status });
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
              <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
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
      <VisitCreateModal
        open={createOpen}
        students={students}
        onClose={() => setCreateOpen(false)}
        onSuccess={async () => { setCreateOpen(false); await load(); }}
        showToast={showToast}
      />
    </>
  );
}

function VisitCreateModal({ open, students, onClose, onSuccess, showToast }: {
  open: boolean; students: DataRecord[]; onClose: () => void; onSuccess: () => Promise<void>;
  showToast: (title: string, message?: string, type?: "success" | "error") => void;
}) {
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm();
  async function submit(values: Record<string, unknown>) {
    try {
      await api.post("/infirmary/infirmary-visits", values);
      showToast("Sağlık kaydı oluşturuldu");
      reset();
      await onSuccess();
    } catch (err) { showToast("Kayıt oluşturulamadı", apiMessage(err), "error"); }
  }
  return <Modal open={open} title="Yeni sağlık kaydı" description="Öğrenci ziyareti ve uygulanan tedaviyi kaydedin." onClose={onClose} actions={<>
    <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
    <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>Kaydet</button>
  </>}><form className="form-grid">
    <Field label="Öğrenci" required error={errors.student_id?.message as string}><select {...register("student_id", { required: "Öğrenci seçimi zorunludur." })}><option value="">Öğrenci seçin</option>{students.map((student) => <option key={student.id} value={student.id}>{String(student.first_name)} {String(student.last_name)}</option>)}</select></Field>
    <Field label="Ziyaret tarihi" required error={errors.visit_date?.message as string}><input type="date" {...register("visit_date", { required: "Tarih zorunludur." })} /></Field>
    <Field label="Ziyaret saati"><input type="time" {...register("visit_time")} /></Field>
    <Field label="Önem seviyesi"><select {...register("severity")}><option value="LOW">Düşük</option><option value="MEDIUM">Orta</option><option value="HIGH">Yüksek</option><option value="EMERGENCY">Acil</option></select></Field>
    <Field label="Şikayet" full><textarea {...register("complaint")} /></Field>
    <Field label="Uygulanan tedavi" full><textarea {...register("treatment_given")} /></Field>
    <Field label="Takip gerekli"><input type="checkbox" {...register("follow_up_required")} /></Field>
  </form></Modal>;
}

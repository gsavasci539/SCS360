import { ArrowLeft, ArrowRight, Save, Search, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function AssignStudentsPage() {
  const { id } = useParams();
  const [classInfo, setClassInfo] = useState<DataRecord | null>(null);
  const [available, setAvailable] = useState<DataRecord[]>([]);
  const [assigned, setAssigned] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [searchAvailable, setSearchAvailable] = useState("");
  const [searchAssigned, setSearchAssigned] = useState("");
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [classRes, availableRes, assignedRes] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord>>(`/classes/${id}`),
        api.get<ApiResponse<DataRecord[]>>(`/students`, { params: { unassigned: true, limit: 100, page_size: 100 } }),
        api.get<ApiResponse<DataRecord[]>>(`/classes/${id}/students`)
      ]);

      if (classRes.status === "fulfilled") {
        setClassInfo(classRes.value.data.data);
      } else {
        throw new Error(apiMessage(classRes.reason));
      }

      if (availableRes.status === "fulfilled") {
        setAvailable(availableRes.value.data.data || []);
      } else {
        throw new Error(apiMessage(availableRes.reason));
      }

      if (assignedRes.status === "fulfilled") {
        setAssigned(assignedRes.value.data.data || []);
      } else {
        throw new Error(apiMessage(assignedRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function save() {
    setSaving(true);
    try {
      await api.post(`/classes/${id}/assign-students`, {
        student_ids: assigned.map((s) => s.id)
      });
      showToast("Öğrenciler atandı", `${assigned.length} öğrenci sınıfa eklendi.`);
      await load();
    } catch (err) {
      showToast("Öğrenciler atanamadı", apiMessage(err), "error");
    } finally {
      setSaving(false);
    }
  }

  function moveToAssigned(student: DataRecord) {
    setAvailable(available.filter((s) => s.id !== student.id));
    setAssigned([...assigned, student]);
  }

  function moveToAvailable(student: DataRecord) {
    setAssigned(assigned.filter((s) => s.id !== student.id));
    setAvailable([...available, student]);
  }

  const filteredAvailable = available.filter((s) => {
    const name = [s.first_name, s.last_name].join(" ").toLowerCase();
    return name.includes(searchAvailable.toLowerCase());
  });

  const filteredAssigned = assigned.filter((s) => {
    const name = [s.first_name, s.last_name].join(" ").toLowerCase();
    return name.includes(searchAssigned.toLowerCase());
  });

  if (loading) return <div className="card"><LoadingState label="Öğrenci listesi yükleniyor" /></div>;
  if (error || !classInfo) return <div className="card"><ErrorState message={error || "Sınıf bulunamadı."} /></div>;

  const capacity = Number(classInfo.capacity || 0);
  const isOverCapacity = assigned.length > capacity;

  return (
    <>
      <PageHeader
        eyebrow="Öğrenci atama"
        title={String(classInfo.name)}
        description={`${String(classInfo.code)} kodlu sınıfa öğrenci atayın. Kapasite: ${capacity}`}
      >
        <Link className="btn btn-secondary" to={`/classes/${id}`}>
          <ArrowLeft size={16} />Sınıfa dön
        </Link>
        <button className="btn btn-primary" onClick={save} disabled={saving || assigned.length === 0}>
          <Save size={16} />{saving ? "Kaydediliyor..." : "Kaydet"}
        </button>
      </PageHeader>

      {isOverCapacity && (
        <div className="card" style={{ marginBottom: 18, background: "#fff0ef", border: "1px solid #f5c6c6" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center", fontSize: 14, color: "#b14545" }}>
            <Users size={20} />
            <div>
              <strong>Kapasite aşıldı</strong>
              <span style={{ marginLeft: 8 }}>Seçilen öğrenci sayısı ({assigned.length}) sınıf kapasitesinden ({capacity}) fazla.</span>
            </div>
          </div>
        </div>
      )}

      <div className="grid dashboard-grid">
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Mevcut öğrenciler</h2>
              <p>Sınıfta kayıtlı öğrenciler</p>
            </div>
            <span className="badge badge-neutral">{assigned.length} öğrenci</span>
          </div>
          <div className="toolbar">
            <div className="search">
              <Search size={16} />
              <input
                type="text"
                placeholder="Öğrenci ara..."
                value={searchAssigned}
                onChange={(e) => setSearchAssigned(e.target.value)}
              />
            </div>
          </div>
          <div className="card-pad" style={{ maxHeight: 400, overflowY: "auto" }}>
            {filteredAssigned.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                Henüz öğrenci atanmamış
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {filteredAssigned.map((student) => (
                  <div
                    key={student.id}
                    style={{
                      padding: 12,
                      background: "#f8f9fa",
                      borderRadius: 8,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div>
                      <div style={{ font: "600 14px Manrope" }}>
                        {[String(student.first_name), String(student.last_name)].filter(Boolean).join(" ")}
                      </div>
                      <div style={{ fontSize: 12, color: "#7a8888" }}>
                        {String(student.student_number || "Öğrenci no yok")}
                      </div>
                    </div>
                    <button
                      className="btn btn-ghost btn-icon"
                      onClick={() => moveToAvailable(student)}
                      title="Kaldır"
                    >
                      <ArrowRight size={16} style={{ transform: "rotate(180deg)" }} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="card">
          <div className="card-head">
            <div>
              <h2>Atanabilir öğrenciler</h2>
              <p>Sınıfa atanabilecek öğrenciler</p>
            </div>
            <span className="badge badge-neutral">{filteredAvailable.length} öğrenci</span>
          </div>
          <div className="toolbar">
            <div className="search">
              <Search size={16} />
              <input
                type="text"
                placeholder="Öğrenci ara..."
                value={searchAvailable}
                onChange={(e) => setSearchAvailable(e.target.value)}
              />
            </div>
          </div>
          <div className="card-pad" style={{ maxHeight: 400, overflowY: "auto" }}>
            {filteredAvailable.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                Atanabilir öğrenci yok
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {filteredAvailable.map((student) => (
                  <div
                    key={student.id}
                    style={{
                      padding: 12,
                      background: "#f8f9fa",
                      borderRadius: 8,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div>
                      <div style={{ font: "600 14px Manrope" }}>
                        {[String(student.first_name), String(student.last_name)].filter(Boolean).join(" ")}
                      </div>
                      <div style={{ fontSize: 12, color: "#7a8888" }}>
                        {String(student.student_number || "Öğrenci no yok")}
                      </div>
                    </div>
                    <button
                      className="btn btn-ghost btn-icon"
                      onClick={() => moveToAssigned(student)}
                      title="Ekle"
                    >
                      <ArrowRight size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  );
}

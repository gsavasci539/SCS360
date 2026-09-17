import { ArrowLeft, Mail, Phone, Trash2, User, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { ConfirmDialog, EmptyState, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { titleCase } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";

export function StudentParentsPage() {
  const { id } = useParams();
  const [parents, setParents] = useState<DataRecord[]>([]);
  const [student, setStudent] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<DataRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const { showToast } = useToast();
  const can = useAuthStore((state) => state.can);

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    relationship: "FATHER",
    is_primary: false,
    address: ""
  });

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [parentsRes, studentRes] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord[]>>(`/students/${id}/parents`),
        api.get<ApiResponse<DataRecord>>(`/students/${id}`)
      ]);

      if (parentsRes.status === "fulfilled") {
        setParents(parentsRes.value.data.data || []);
      } else {
        throw new Error(apiMessage(parentsRes.reason));
      }

      if (studentRes.status === "fulfilled") {
        setStudent(studentRes.value.data.data);
      } else {
        throw new Error(apiMessage(studentRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    try {
      await api.delete(`/students/${id}/parents/${deleting.id}`);
      showToast("Veli kaldırıldı", "Kayıt başarıyla silindi.");
      setDeleting(null);
      await load();
    } catch (err) {
      showToast("İşlem tamamlanamadı", apiMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  async function addParent(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post(`/students/${id}/parents`, formData);
      showToast("Veli eklendi", "Yeni veli kaydı oluşturuldu.");
      setShowAddForm(false);
      setFormData({
        first_name: "",
        last_name: "",
        phone: "",
        email: "",
        relationship: "FATHER",
        is_primary: false,
        address: ""
      });
      await load();
    } catch (err) {
      showToast("Veli eklenemedi", apiMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="card"><LoadingState label="Veli bilgileri yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;

  const studentName = [student?.first_name, student?.last_name].filter(Boolean).join(" ");

  return (
    <>
      <PageHeader
        eyebrow="Veli yönetimi"
        title="Veli kayıtları"
        description={`${studentName || "Öğrenci"} için veli bilgileri ve iletişim detayları.`}
      >
        <Link className="btn btn-secondary" to={`/students/${id}`}>
          <ArrowLeft size={16} />Öğrenciye dön
        </Link>
        {can("student.write") && (
          <button className="btn btn-primary" onClick={() => setShowAddForm(true)}>
            <UserPlus size={16} />Veli ekle
          </button>
        )}
      </PageHeader>

      {showAddForm && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>Yeni veli ekle</h2>
              <p>Öğrenci için yeni veli kaydı oluşturun</p>
            </div>
            <button className="btn btn-ghost btn-icon" onClick={() => setShowAddForm(false)} aria-label="Veli formunu kapat">
              ✕
            </button>
          </div>
          <form className="form-card" onSubmit={addParent}>
            <div className="form-grid">
              <div className="field">
                <label>Ad *</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>Soyad *</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>Telefon</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </div>
              <div className="field">
                <label>E-posta</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Yakınlık derecesi</label>
                <select
                  value={formData.relationship}
                  onChange={(e) => setFormData({ ...formData, relationship: e.target.value })}
                >
                  <option value="FATHER">Baba</option>
                  <option value="MOTHER">Anne</option>
                  <option value="GUARDIAN">Vasi</option>
                  <option value="OTHER">Diğer</option>
                </select>
              </div>
              <div className="field">
                <label>Adres</label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                />
              </div>
              <div className="field field-full">
                <label className="checkbox-line">
                  <input
                    type="checkbox"
                    checked={formData.is_primary}
                    onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
                  />
                  Birincil veli olarak işaretle
                </label>
              </div>
            </div>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowAddForm(false)}
              >
                Vazgeç
              </button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? "Kaydediliyor..." : "Kaydet"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        {parents.length === 0 ? (
          <EmptyState
            title="Henüz veli kaydı yok"
            description="Öğrenci için ilk veli kaydını oluşturun."
            action={can("student.write") && (
              <button className="btn btn-primary" onClick={() => setShowAddForm(true)}>
                <UserPlus size={16} />İlk veliyi ekle
              </button>
            )}
          />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Veli</th>
                  <th>İletişim</th>
                  <th>Yakınlık</th>
                  <th>Durum</th>
                  {can("student.write") && <th style={{ textAlign: "right" }}>İşlem</th>}
                </tr>
              </thead>
              <tbody>
                {parents.map((parent) => (
                  <tr key={parent.id}>
                    <td>
                      <div className="inline" style={{ gap: 10 }}>
                        <div className="quick-icon"><User size={16} /></div>
                        <div>
                          <div className="cell-main">
                            {[String(parent.first_name), String(parent.last_name)].filter(Boolean).join(" ")}
                          </div>
                          {parent.address && (
                            <div className="cell-sub">{String(parent.address)}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                        {parent.phone && (
                          <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                            <Phone size={12} />{String(parent.phone)}
                          </span>
                        )}
                        {parent.email && (
                          <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                            <Mail size={12} />{String(parent.email)}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>{titleCase(parent.relationship)}</td>
                    <td>
                      {parent.is_primary ? (
                        <span className="badge badge-green">Birincil</span>
                      ) : (
                        <span className="badge badge-gray">Yedek</span>
                      )}
                    </td>
                    {can("student.write") && (
                      <td>
                        <div className="table-actions">
                          <button
                            className="btn btn-ghost btn-icon"
                            onClick={() => setDeleting(parent)}
                            aria-label={`${String(parent.first_name)} ${String(parent.last_name)} veli kaydını kaldır`}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Veli kaydını kaldır?"
        description="Bu veli öğrenci ile ilişkilendirmesini kaldırır."
        busy={busy}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </>
  );
}

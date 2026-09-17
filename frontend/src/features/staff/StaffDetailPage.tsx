import { ArrowLeft, BadgeCheck, Edit, Trash2, IdCard } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useToast } from "../../components/Toast";
import type { ApiResponse, DataRecord } from "../../types/api";
import { useForm } from "react-hook-form";

export function StaffDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/staff/${id}`);
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
      await api.delete(`/staff/${id}`);
      showToast("Personel silindi", "Personel başarıyla silindi.");
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;
  if (!data) return <div className="card"><ErrorState message="Personel bulunamadı" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Yönetim"
        title="Personel Detayı"
        description="Personel bilgileri ve detayları."
      >
        <div style={{ display: "flex", gap: 8 }}>
          <Link to={`/rfid-cards?holder_id=${id}`} className="btn btn-secondary">
            <IdCard size={16} />RFID Kartı
          </Link>
          <button className="btn btn-secondary" onClick={() => setEditOpen(true)}>
            <Edit size={16} />Düzenle
          </button>
          <Link to="/staff" className="btn btn-secondary">
            <ArrowLeft size={16} />Geri Dön
          </Link>
        </div>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 10, color: "var(--brand)", background: "#e9f3ef" }}>
              <BadgeCheck size={20} />
            </div>
            <div>
              <h2>{String(data.first_name)} {String(data.last_name)}</h2>
              <p style={{ color: "var(--muted)", fontSize: 12 }}>{String(data.position)}</p>
            </div>
          </div>
          <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={16} />Sil
          </button>
        </div>
        <div className="card-pad">
          <div style={{ display: "grid", gap: 16 }}>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>E-posta</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.email)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Telefon</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.phone)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Pozisyon</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.position)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Departman</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.department)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Durum</small>
              <span className="badge badge-green">{String(data.status)}</span>
            </div>
          </div>
        </div>
      </div>

      <EditModal open={editOpen} data={data} onClose={() => setEditOpen(false)} onSuccess={() => load()} />
    </>
  );
}

function EditModal({ open, data, onClose, onSuccess }: { open: boolean; data: DataRecord | null; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const { showToast } = useToast();

  async function submit(values: any) {
    if (!data) return;
    try {
      await api.put(`/staff/${data.id}`, values);
      showToast("Personel güncellendi", "Personel bilgileri başarıyla güncellendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Personel düzenle" description="Personel bilgilerini güncelleyin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          Kaydet
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Ad" required error={errors.first_name?.message as string}>
          <input {...register("first_name", { required: "Ad zorunludur." })} defaultValue={String(data?.first_name || "")} />
        </Field>
        <Field label="Soyad" required error={errors.last_name?.message as string}>
          <input {...register("last_name", { required: "Soyad zorunludur." })} defaultValue={String(data?.last_name || "")} />
        </Field>
        <Field label="Ünvan" error={errors.position?.message as string}>
          <input {...register("position")} defaultValue={String(data?.position || "")} />
        </Field>
        <Field label="Departman" error={errors.department?.message as string}>
          <input {...register("department")} defaultValue={String(data?.department || "")} />
        </Field>
        <Field label="Telefon" error={errors.phone?.message as string}>
          <input {...register("phone")} defaultValue={String(data?.phone || "")} />
        </Field>
        <Field label="E-posta" error={errors.email?.message as string}>
          <input type="email" {...register("email")} defaultValue={String(data?.email || "")} />
        </Field>
      </form>
    </Modal>
  );
}

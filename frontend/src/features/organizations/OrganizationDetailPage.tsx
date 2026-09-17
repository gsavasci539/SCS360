import { ArrowLeft, Building2, Edit, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useToast } from "../../components/Toast";
import type { ApiResponse, DataRecord } from "../../types/api";
import { useForm } from "react-hook-form";

export function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/organizations/${id}`);
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
      await api.delete(`/organizations/${id}`);
      showToast("Kurum silindi", "Kurum başarıyla silindi.");
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;
  if (!data) return <div className="card"><ErrorState message="Kurum bulunamadı" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Yönetim"
        title="Kurum Detayı"
        description="Kurum bilgileri ve ayarları."
      >
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary" onClick={() => setEditOpen(true)}>
            <Edit size={16} />Düzenle
          </button>
          <Link to="/organizations" className="btn btn-secondary">
            <ArrowLeft size={16} />Geri Dön
          </Link>
        </div>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 10, color: "var(--brand)", background: "#e9f3ef" }}>
              <Building2 size={20} />
            </div>
            <div>
              <h2>{String(data.name)}</h2>
              <p style={{ color: "var(--muted)", fontSize: 12 }}>{String(data.legal_name)}</p>
            </div>
          </div>
          <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={16} />Sil
          </button>
        </div>
        <div className="card-pad">
          <div style={{ display: "grid", gap: 16 }}>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Vergi Numarası</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.tax_number)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Vergi Dairesi</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.tax_office)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Telefon</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.phone)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>E-posta</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.email)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Adres</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.address)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Şehir</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.city)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Ülke</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.country)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Durum</small>
              <span className="badge badge-green">{String(data.is_active)}</span>
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
      await api.put(`/organizations/${data.id}`, values);
      showToast("Kurum güncellendi", "Kurum bilgileri başarıyla güncellendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Kurum düzenle" description="Kurum bilgilerini güncelleyin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          Kaydet
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Kurum adı" required error={errors.name?.message as string}>
          <input {...register("name", { required: "Kurum adı zorunludur." })} defaultValue={String(data?.name || "")} />
        </Field>
        <Field label="Vergi no" error={errors.tax_number?.message as string}>
          <input {...register("tax_number")} defaultValue={String(data?.tax_number || "")} />
        </Field>
        <Field label="Vergi dairesi" error={errors.tax_office?.message as string}>
          <input {...register("tax_office")} defaultValue={String(data?.tax_office || "")} />
        </Field>
        <Field label="Telefon" error={errors.phone?.message as string}>
          <input {...register("phone")} defaultValue={String(data?.phone || "")} />
        </Field>
        <Field label="E-posta" error={errors.email?.message as string}>
          <input type="email" {...register("email")} defaultValue={String(data?.email || "")} />
        </Field>
        <Field label="Adres" full error={errors.address?.message as string}>
          <textarea {...register("address")} defaultValue={String(data?.address || "")} />
        </Field>
        <Field label="Şehir" error={errors.city?.message as string}>
          <input {...register("city")} defaultValue={String(data?.city || "")} />
        </Field>
        <Field label="Ülke" error={errors.country?.message as string}>
          <input {...register("country")} defaultValue={String(data?.country || "")} />
        </Field>
      </form>
    </Modal>
  );
}

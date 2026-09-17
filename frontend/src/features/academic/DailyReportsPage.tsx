import { Plus, ArrowLeft, FileText, Edit, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function DailyReportsPage() {
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/daily-reports", {
        params: { page, page_size: 20, limit: 20, skip: (page - 1) * 20 }
      });
      setData(normalize(r.data.data));
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(1); }, []);

  const filtered = useMemo(() => 
    data.items.filter((r) => JSON.stringify(r).toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))),
    [data.items, search]
  );

  async function handleDelete(row: DataRecord) {
    try {
      await api.delete(`/daily-reports/${row.id}`);
      showToast("Günlük karne silindi", "Günlük karne başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Eğitim"
        title="Günlük Karne"
        description="Öğrencilerin günlük gelişim raporlarını yönetin."
      >
        {can("academic.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni karne
          </button>
        )}
      </PageHeader>

      {loading ? (
        <div className="card"><LoadingState /></div>
      ) : error ? (
        <div className="card"><ErrorState message={error} retry={() => load()} /></div>
      ) : (
        <DataTable
          rows={filtered}
          columns={[
            { key: "student_name", label: "Öğrenci" },
            { key: "date", label: "Tarih", type: "date" },
            { key: "behavior", label: "Davranış" },
            { key: "academic_performance", label: "Akademik" },
            { key: "notes", label: "Notlar" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/daily-reports"
          canEdit={can("academic.write")}
          onDelete={can("academic.write") ? handleDelete : undefined}
        />
      )}

      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} onSuccess={() => load()} />
    </>
  );
}

function CreateModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const { showToast } = useToast();

  async function submit(values: any) {
    try {
      await api.post("/daily-reports", values);
      showToast("Günlük karne oluşturuldu", "Yeni günlük karne başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni günlük karne" description="Günlük karne bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Öğrenci" required error={errors.student_id?.message as string}>
          <input {...register("student_id", { required: "Öğrenci seçimi zorunludur." })} />
        </Field>
        <Field label="Tarih" error={errors.date?.message as string}>
          <input type="date" {...register("date")} />
        </Field>
        <Field label="Davranış" error={errors.behavior?.message as string}>
          <input {...register("behavior")} />
        </Field>
        <Field label="Akademik performans" error={errors.academic_performance?.message as string}>
          <input {...register("academic_performance")} />
        </Field>
        <Field label="Notlar" full error={errors.notes?.message as string}>
          <textarea {...register("notes")} />
        </Field>
      </form>
    </Modal>
  );
}

export function DailyReportsDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/daily-reports/${id}`);
      setData(r.data.data);
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function handleDelete() {
    if (!data) return;
    try {
      await api.delete(`/daily-reports/${data.id}`);
      showToast("Günlük karne silindi", "Günlük karne başarıyla silindi.");
      window.location.href = "/daily-reports";
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;
  if (!data) return <div className="card"><ErrorState message="Günlük karne bulunamadı" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Eğitim"
        title="Günlük Karne Detayı"
        description="Günlük karne bilgileri ve detayları."
      >
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary" onClick={() => setEditOpen(true)}>
            <Edit size={16} />Düzenle
          </button>
          <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={16} />Sil
          </button>
          <Link to="/daily-reports" className="btn btn-secondary">
            <ArrowLeft size={16} />Geri Dön
          </Link>
        </div>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 10, color: "var(--brand)", background: "#e9f3ef" }}>
              <FileText size={20} />
            </div>
            <div>
              <h2>{String(data.student_name)}</h2>
              <small style={{ color: "var(--muted)" }}>{String(data.date)}</small>
            </div>
          </div>
        </div>
        <div className="card-pad">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Davranış</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.behavior || "-")}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Akademik Performans</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.academic_performance || "-")}</strong>
            </div>
          </div>
          {data.notes && (
            <div style={{ marginTop: 16 }}>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Notlar</small>
              <p style={{ fontSize: 13, lineHeight: 1.6 }}>{String(data.notes)}</p>
            </div>
          )}
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
      await api.put(`/daily-reports/${data.id}`, values);
      showToast("Günlük karne güncellendi", "Günlük karne başarıyla güncellendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Günlük karne düzenle" description="Günlük karne bilgilerini güncelleyin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          Kaydet
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Öğrenci" required error={errors.student_id?.message as string}>
          <input {...register("student_id", { required: "Öğrenci seçimi zorunludur." })} defaultValue={String(data?.student_id || "")} />
        </Field>
        <Field label="Tarih" error={errors.date?.message as string}>
          <input type="date" {...register("date")} defaultValue={String(data?.date || "")} />
        </Field>
        <Field label="Davranış" error={errors.behavior?.message as string}>
          <input {...register("behavior")} defaultValue={String(data?.behavior || "")} />
        </Field>
        <Field label="Akademik performans" error={errors.academic_performance?.message as string}>
          <input {...register("academic_performance")} defaultValue={String(data?.academic_performance || "")} />
        </Field>
        <Field label="Notlar" full error={errors.notes?.message as string}>
          <textarea {...register("notes")} defaultValue={String(data?.notes || "")} />
        </Field>
      </form>
    </Modal>
  );
}

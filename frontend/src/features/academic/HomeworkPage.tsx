import { Plus, ArrowLeft, BookOpen, Edit, Trash2 } from "lucide-react";
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

export function HomeworkPage() {
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
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/homework", {
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
      await api.delete(`/homework/${row.id}`);
      showToast("Ödev silindi", "Ödev başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Eğitim"
        title="Ödev & Notlandırma"
        description="Ödev atamalarını ve notları yönetin."
      >
        {can("academic.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni ödev
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
            { key: "title", label: "Ödev adı" },
            { key: "subject", label: "Ders" },
            { key: "class_name", label: "Sınıf" },
            { key: "due_date", label: "Son teslim", type: "date" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/homework"
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
      await api.post("/homework", values);
      showToast("Ödev oluşturuldu", "Yeni ödev başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni ödev" description="Ödev bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Ödev adı" required error={errors.title?.message as string}>
          <input {...register("title", { required: "Ödev adı zorunludur." })} />
        </Field>
        <Field label="Ders" error={errors.subject?.message as string}>
          <input {...register("subject")} />
        </Field>
        <Field label="Sınıf" error={errors.class_id?.message as string}>
          <input {...register("class_id")} />
        </Field>
        <Field label="Son teslim tarihi" error={errors.due_date?.message as string}>
          <input type="date" {...register("due_date")} />
        </Field>
        <Field label="Açıklama" full error={errors.description?.message as string}>
          <textarea {...register("description")} />
        </Field>
      </form>
    </Modal>
  );
}

export function HomeworkDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/homework/${id}`);
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
      await api.delete(`/homework/${data.id}`);
      showToast("Ödev silindi", "Ödev başarıyla silindi.");
      window.location.href = "/homework";
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;
  if (!data) return <div className="card"><ErrorState message="Ödev bulunamadı" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Eğitim"
        title="Ödev Detayı"
        description="Ödev bilgileri ve detayları."
      >
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary" onClick={() => setEditOpen(true)}>
            <Edit size={16} />Düzenle
          </button>
          <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={16} />Sil
          </button>
          <Link to="/homework" className="btn btn-secondary">
            <ArrowLeft size={16} />Geri Dön
          </Link>
        </div>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 10, color: "var(--brand)", background: "#e9f3ef" }}>
              <BookOpen size={20} />
            </div>
            <div>
              <h2>{String(data.title)}</h2>
              <small style={{ color: "var(--muted)" }}>{String(data.subject)}</small>
            </div>
          </div>
          <span className="badge badge-green">{String(data.status)}</span>
        </div>
        <div className="card-pad">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Sınıf</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.class_name)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Son teslim</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.due_date)}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Durum</small>
              <span className="badge badge-green">{String(data.status)}</span>
            </div>
          </div>
          {data.description && (
            <div style={{ marginTop: 16 }}>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Açıklama</small>
              <p style={{ fontSize: 13, lineHeight: 1.6 }}>{String(data.description)}</p>
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
      await api.put(`/homework/${data.id}`, values);
      showToast("Ödev güncellendi", "Ödev bilgileri başarıyla güncellendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Ödev düzenle" description="Ödev bilgilerini güncelleyin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          Kaydet
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Ödev adı" required error={errors.title?.message as string}>
          <input {...register("title", { required: "Ödev adı zorunludur." })} defaultValue={String(data?.title || "")} />
        </Field>
        <Field label="Ders" error={errors.subject?.message as string}>
          <input {...register("subject")} defaultValue={String(data?.subject || "")} />
        </Field>
        <Field label="Sınıf" error={errors.class_id?.message as string}>
          <input {...register("class_id")} defaultValue={String(data?.class_id || "")} />
        </Field>
        <Field label="Son teslim tarihi" error={errors.due_date?.message as string}>
          <input type="date" {...register("due_date")} defaultValue={String(data?.due_date || "")} />
        </Field>
        <Field label="Açıklama" full error={errors.description?.message as string}>
          <textarea {...register("description")} defaultValue={String(data?.description || "")} />
        </Field>
      </form>
    </Modal>
  );
}

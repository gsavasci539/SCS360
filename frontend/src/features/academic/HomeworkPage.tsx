import { getAnalysis } from "../../lib/analysis";
import { Plus, ArrowLeft, BookOpen, Edit, Trash2, Brain, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";
import { HomeworkSubmissions } from "./HomeworkSubmissions";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function HomeworkPage() {
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [homeworkAI, setHomeworkAI] = useState<any>(null);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    setError("");
    try {
      const [r, aiResult] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/homework", {
          params: { page, page_size: 20, limit: 20, skip: (page - 1) * 20 }
        }),
        getAnalysis("/ai/ai-homework-analysis").catch(() => null)
      ]);
      if (r.status === "rejected") throw r.reason;
      setData(normalize(r.value.data.data));
      if (aiResult.status === "fulfilled" && aiResult.value) {
        setHomeworkAI(aiResult.value.data.data);
      }
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
        {can("homework.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni ödev
          </button>
        )}
      </PageHeader>

      {homeworkAI && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Ödev Analizi</h2>
              <p>Ödev performansı ve ders bazlı insights - {homeworkAI.ai_model}</p>
            </div>
            <Brain size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Toplam Ödev</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>{homeworkAI.homework_stats?.total || 0}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Ortalama Puan</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>{homeworkAI.homework_stats?.avg_score || 0}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Tamamlama Oranı</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>%{homeworkAI.homework_stats?.completion_rate || 0}</div>
              </div>
            </div>
            {homeworkAI.subject_insights && homeworkAI.subject_insights.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Ders Bazlı Analiz</h3>
                {homeworkAI.subject_insights.slice(0, 3).map((insight: any, index: number) => (
                  <div key={index} style={{ padding: 10, borderRadius: 6, background: index === 0 ? "#fee2e2" : "#f8faf8", marginBottom: 6, borderLeft: `3px solid ${insight.performance === "zayıf" ? "#dc2626" : insight.performance === "normal" ? "#ca8a04" : "#16a34a"}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{insight.subject}</span>
                      <span style={{ fontSize: 12, fontWeight: 700 }}>{insight.avg_score} puan</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>{insight.total} ödev • {insight.performance}</div>
                  </div>
                ))}
              </div>
            )}
            {homeworkAI.recommendations && homeworkAI.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>AI Önerileri</h3>
                {homeworkAI.recommendations.map((rec: string, index: number) => (
                  <div key={index} style={{ display: "flex", gap: 8, marginBottom: 6, padding: 8, borderRadius: 6, background: "#f0fdf4" }}>
                    <TrendingUp size={16} color="#176b5b" />
                    <span style={{ fontSize: 13 }}>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

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
          canEdit={false}
          onDelete={can("homework.write") ? handleDelete : undefined}
        />
      )}

      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} onSuccess={() => load()} />
    </>
  );
}

function CreateModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const { showToast } = useToast();
  const [classes, setClasses] = useState<DataRecord[]>([]);
  useEffect(() => {
    if (open) api.get<ApiResponse<DataRecord[]>>("/homework/classes")
      .then((response) => setClasses(response.data.data))
      .catch((reason) => showToast("Sınıflar yüklenemedi", apiMessage(reason), "error"));
  }, [open, showToast]);

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
          <select {...register("class_id")}><option value="">Sınıf seçin</option>
            {classes.map((row) => <option key={String(row.id)} value={String(row.id)}>{String(row.name)}</option>)}
          </select>
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
  const can = useAuthStore((state) => state.can);

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
          {can("homework.write") && <button className="btn btn-secondary" onClick={() => setEditOpen(true)}>
            <Edit size={16} />Düzenle
          </button>}
          {can("homework.write") && <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={16} />Sil
          </button>}
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

      <div className="card card-pad" style={{ marginTop: 18 }}>
        <h2>Ödev teslimleri</h2>
        <HomeworkSubmissions homeworkId={String(data.id)} canGrade={can("homework.write")} />
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

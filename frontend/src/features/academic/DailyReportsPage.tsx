import { getAnalysis } from "../../lib/analysis";
import { Plus, ArrowLeft, FileText, Edit, Trash2, Brain, TrendingUp } from "lucide-react";
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
  const [dailyReportsAI, setDailyReportsAI] = useState<any>(null);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    try {
      const [r, aiResult] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/daily-reports", {
          params: { page, page_size: 20, limit: 20, skip: (page - 1) * 20 }
        }),
        getAnalysis("/ai/ai-daily-reports-analysis").catch(() => null)
      ]);
      setData(normalize(r.status === "fulfilled" ? r.value.data.data : []));
      if (aiResult.status === "fulfilled" && aiResult.value) {
        setDailyReportsAI(aiResult.value.data.data);
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

      {dailyReportsAI && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Günlük Karne Analizi</h2>
              <p>Öğrenci gelişim ve wellness analizi - {dailyReportsAI.ai_model}</p>
            </div>
            <Brain size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Toplam Rapor</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>{dailyReportsAI.report_stats?.total || 0}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Mutlu Oranı</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>%{dailyReportsAI.report_stats?.mood_rate || 0}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Uyku Oranı</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>%{dailyReportsAI.report_stats?.sleep_rate || 0}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: 11, color: "#6e7b7d", marginBottom: 4 }}>Beslenme Oranı</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>%{dailyReportsAI.report_stats?.meal_rate || 0}</div>
              </div>
            </div>
            {dailyReportsAI.students_needing_attention && dailyReportsAI.students_needing_attention.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Dikkat Gerektiren Öğrenciler</h3>
                {dailyReportsAI.students_needing_attention.slice(0, 3).map((student: any, index: number) => (
                  <div key={index} style={{ padding: 10, borderRadius: 6, background: student.risk_level === "yüksek" ? "#fee2e2" : "#f8faf8", marginBottom: 6, borderLeft: `3px solid ${student.risk_level === "yüksek" ? "#dc2626" : "#ca8a04"}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{student.student_name}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: student.risk_level === "yüksek" ? "#dc2626" : "#ca8a04" }}>{student.wellness_score} wellness</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>{student.total_reports} rapor • {student.poor_mood} ruh hali sorunu • {student.poor_sleep} uyku sorunu</div>
                  </div>
                ))}
              </div>
            )}
            {dailyReportsAI.recommendations && dailyReportsAI.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>AI Önerileri</h3>
                {dailyReportsAI.recommendations.map((rec: string, index: number) => (
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
            { key: "student_name", label: "Öğrenci" },
            { key: "date", label: "Tarih", type: "date" },
            { key: "mood", label: "Ruh Hali" },
            { key: "sleep_status", label: "Uyku Durumu" },
            { key: "meal_status", label: "Beslenme" },
            { key: "teacher_notes", label: "Öğretmen Notları" }
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
        <Field label="Ruh Hali" error={errors.mood?.message as string}>
          <select {...register("mood")}>
            <option value="">Seçiniz</option>
            <option value="HAPPY">Mutlu</option>
            <option value="CALM">Sakin</option>
            <option value="UNSETTLED">Huzursuz</option>
            <option value="TIRED">Yorgun</option>
          </select>
        </Field>
        <Field label="Uyku Durumu" error={errors.sleep_status?.message as string}>
          <select {...register("sleep_status")}>
            <option value="">Seçiniz</option>
            <option value="SLEPT_WELL">İyi uyudu</option>
            <option value="SHORT">Kısa uyku</option>
            <option value="NO_SLEEP">Uyku yok</option>
          </select>
        </Field>
        <Field label="Beslenme Durumu" error={errors.meal_status?.message as string}>
          <select {...register("meal_status")}>
            <option value="">Seçiniz</option>
            <option value="ALL">Tam yedi</option>
            <option value="HALF">Yarım yedi</option>
            <option value="NONE">Yemedi</option>
          </select>
        </Field>
        <Field label="Öğretmen Notları" full error={errors.teacher_notes?.message as string}>
          <textarea {...register("teacher_notes")} />
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
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Ruh Hali</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.mood || "-")}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Uyku Durumu</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.sleep_status || "-")}</strong>
            </div>
            <div>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Beslenme Durumu</small>
              <strong style={{ display: "block", fontSize: 13 }}>{String(data.meal_status || "-")}</strong>
            </div>
          </div>
          {data.teacher_notes && (
            <div style={{ marginTop: 16 }}>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Öğretmen Notları</small>
              <p style={{ fontSize: 13, lineHeight: 1.6 }}>{String(data.teacher_notes)}</p>
            </div>
          )}
          {data.activities && (
            <div style={{ marginTop: 16 }}>
              <small style={{ display: "block", color: "var(--muted)", fontSize: 10, fontWeight: 700, letterSpacing: ".4px", textTransform: "uppercase", marginBottom: 6 }}>Aktiviteler</small>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {Array.isArray(data.activities) ? data.activities.map((activity: any, index: number) => (
                  <span key={index} style={{ padding: "4px 8px", borderRadius: 4, background: "#f0fdf4", fontSize: 12, color: "#16a34a" }}>{String(activity)}</span>
                )) : <span style={{ fontSize: 13 }}>{String(data.activities)}</span>}
              </div>
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
        <Field label="Ruh Hali" error={errors.mood?.message as string}>
          <select {...register("mood")} defaultValue={String(data?.mood || "")}>
            <option value="">Seçiniz</option>
            <option value="HAPPY">Mutlu</option>
            <option value="CALM">Sakin</option>
            <option value="UNSETTLED">Huzursuz</option>
            <option value="TIRED">Yorgun</option>
          </select>
        </Field>
        <Field label="Uyku Durumu" error={errors.sleep_status?.message as string}>
          <select {...register("sleep_status")} defaultValue={String(data?.sleep_status || "")}>
            <option value="">Seçiniz</option>
            <option value="SLEPT_WELL">İyi uyudu</option>
            <option value="SHORT">Kısa uyku</option>
            <option value="NO_SLEEP">Uyku yok</option>
          </select>
        </Field>
        <Field label="Beslenme Durumu" error={errors.meal_status?.message as string}>
          <select {...register("meal_status")} defaultValue={String(data?.meal_status || "")}>
            <option value="">Seçiniz</option>
            <option value="ALL">Tam yedi</option>
            <option value="HALF">Yarım yedi</option>
            <option value="NONE">Yemedi</option>
          </select>
        </Field>
        <Field label="Öğretmen Notları" full error={errors.teacher_notes?.message as string}>
          <textarea {...register("teacher_notes")} defaultValue={String(data?.teacher_notes || "")} />
        </Field>
      </form>
    </Modal>
  );
}

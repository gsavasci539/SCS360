import { Plus, ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function AppointmentsPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [detail, setDetail] = useState<DataRecord | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/appointments", {
        params: { page, page_size: 20, limit: 20, skip: (page - 1) * 20 }
      });
      setData(normalize(r.data.data));
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(appointmentId: string) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/appointments/${appointmentId}`);
      setDetail(r.data.data);
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) {
      loadDetail(id);
    } else {
      load(1);
    }
  }, [id]);

  const filtered = useMemo(() => 
    data.items.filter((r) => JSON.stringify(r).toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))),
    [data.items, search]
  );

  async function handleDelete(row: DataRecord) {
    try {
      await api.delete(`/appointments/${row.id}`);
      showToast("Randevu silindi", "Randevu başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  async function handleUpdateStatus(status: string) {
    if (!detail) return;
    try {
      await api.put(`/appointments/${detail.id}`, { status });
      showToast("Durum güncellendi", "Randevu durumu başarıyla güncellendi.");
      await loadDetail(detail.id);
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  if (id) {
    return (
      <>
        <PageHeader
          eyebrow="İletişim"
          title="Randevu Detayı"
          description="Randevu bilgilerini görüntüleyin ve yönetin."
        >
          <Link to="/appointments" className="btn btn-secondary">
            <ArrowLeft size={16} />Geri dön
          </Link>
        </PageHeader>

        {loading ? (
          <div className="card"><LoadingState /></div>
        ) : error ? (
          <div className="card"><ErrorState message={error} retry={() => loadDetail(id)} /></div>
        ) : detail ? (
          <div className="card" style={{ padding: 24 }}>
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{String(detail.student_name || "-")}</h3>
              <div style={{ fontSize: 14, color: "#666" }}>{String(detail.teacher_name || "-")}</div>
            </div>
            
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Tarih ve Saat</label>
              <div style={{ padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14 }}>
                {String(detail.appointment_date || "-")} {String(detail.appointment_time || "-")}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Notlar</label>
              <div style={{ padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14 }}>
                {String(detail.notes || "-")}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Durum</label>
              <div style={{ display: "flex", gap: 8 }}>
                <button 
                  className={`btn ${String(detail.status).toUpperCase() === "PENDING" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleUpdateStatus("PENDING")}
                >
                  Beklemede
                </button>
                <button 
                  className={`btn ${String(detail.status).toUpperCase() === "CONFIRMED" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleUpdateStatus("CONFIRMED")}
                >
                  Onaylandı
                </button>
                <button 
                  className={`btn ${String(detail.status).toUpperCase() === "COMPLETED" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleUpdateStatus("COMPLETED")}
                >
                  Tamamlandı
                </button>
                <button 
                  className={`btn ${String(detail.status).toUpperCase() === "CANCELLED" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleUpdateStatus("CANCELLED")}
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Randevu & PTC"
        description="Veli-öğretmen görüşme randevularını yönetin."
      >
        {can("appointments.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni randevu
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
            { key: "teacher_name", label: "Öğretmen" },
            { key: "appointment_date", label: "Tarih", type: "date" },
            { key: "appointment_time", label: "Saat" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/appointments"
          canEdit={can("appointments.write")}
          onDelete={can("appointments.write") ? handleDelete : undefined}
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
      // Combine date and time into slot_datetime
      const slot_datetime = values.appointment_date && values.appointment_time 
        ? new Date(`${values.appointment_date}T${values.appointment_time}`).toISOString()
        : null;
      
      const payload = {
        teacher_id: values.teacher_id,
        student_id: values.student_id,
        slot_datetime: slot_datetime,
        parent_note: values.notes,
        duration_minutes: 30
      };
      
      await api.post("/appointments", payload);
      showToast("Randevu oluşturuldu", "Yeni randevu başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni randevu" description="Randevu bilgilerini girin." onClose={onClose} actions={
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
        <Field label="Öğretmen" required error={errors.teacher_id?.message as string}>
          <input {...register("teacher_id", { required: "Öğretmen seçimi zorunludur." })} />
        </Field>
        <Field label="Tarih" required error={errors.appointment_date?.message as string}>
          <input type="date" {...register("appointment_date", { required: "Tarih zorunludur." })} />
        </Field>
        <Field label="Saat" required error={errors.appointment_time?.message as string}>
          <input type="time" {...register("appointment_time", { required: "Saat zorunludur." })} />
        </Field>
        <Field label="Notlar" full error={errors.notes?.message as string}>
          <textarea {...register("notes")} />
        </Field>
      </form>
    </Modal>
  );
}

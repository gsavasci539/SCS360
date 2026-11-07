import { Plus, ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { Badge, ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function ParentNoticesPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [detail, setDetail] = useState<DataRecord | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [statusSaving, setStatusSaving] = useState(false);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/parent-notices", {
        params: { page, page_size: 20, limit: 20, skip: (page - 1) * 20 }
      });
      setData(normalize(r.data.data));
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(noticeId: string) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/parent-notices/${noticeId}`);
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
      await api.delete(`/parent-notices/${row.id}`);
      showToast("Veli talebi silindi", "Veli talebi başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  async function handleUpdateStatus(status: string) {
    if (!detail || statusSaving) return;
    setStatusSaving(true);
    try {
      await api.put(`/parent-notices/${detail.id}`, { status });
      showToast("Durum güncellendi", "Veli talebi durumu başarıyla güncellendi.");
      await loadDetail(detail.id);
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    } finally { setStatusSaving(false); }
  }

  if (id) {
    return (
      <>
        <PageHeader
          eyebrow="İletişim"
          title="Veli Talebi Detayı"
          description="Veli talebi bilgilerini görüntüleyin ve yönetin."
        >
          <Link to="/parent-notices" className="btn btn-secondary">
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
              <div style={{ fontSize: 14, color: "#666" }}>{String(detail.type || "-")}</div>
            </div>
            
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Açıklama</label>
              <div style={{ padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14 }}>
                {String(detail.description || "-")}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Durum</label>
              <Badge value={detail.status} />
              {can("parent_notices.write") && (detail.source !== "medicine_request" || can("health.write")) && <div className="toolbar" style={{ flexWrap: "wrap", marginTop: 12 }}>
                {(detail.source === "medicine_request" ? detail.status === "PENDING" ? ["APPROVED", "REJECTED"] : detail.status === "APPROVED" ? ["COMPLETED"] : [] : ["PENDING", "APPROVED", "COMPLETED"]).map((status) => <button className="btn btn-secondary" key={status} disabled={statusSaving || detail.status === status} onClick={() => handleUpdateStatus(status)}>{({ PENDING: "Beklemeye al", APPROVED: "Onayla", REJECTED: "Reddet", COMPLETED: "Tamamla" } as Record<string, string>)[status]}</button>)}
              </div>}
              {detail.source === "medicine_request" && can("health.read") && <Link className="btn btn-secondary" to={`/health?student=${detail.student_id}`}>Revir kaydını aç</Link>}
            </div>

            <div style={{ fontSize: 12, color: "#999" }}>
              Oluşturulma tarihi: {detail.created_at ? new Date(String(detail.created_at)).toLocaleString("tr-TR") : "-"}
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
        title="Veli Talepleri & İlaç"
        description="Veli taleplerini ve ilaç bildirimlerini yönetin."
      >
        {can("parent_notices.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni talep
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
            { key: "type", label: "Tür" },
            { key: "description", label: "Açıklama" },
            { key: "status", label: "Durum", type: "status" },
            { key: "created_at", label: "Tarih", type: "date" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/parent-notices"
          canEdit={(row) => can("parent_notices.write") && row.source !== "medicine_request"}
          onDelete={can("parent_notices.write") ? handleDelete : undefined}
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
      await api.post("/parent-notices", values);
      showToast("Veli talebi oluşturuldu", "Yeni veli talebi başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni veli talebi" description="Veli talebi bilgilerini girin." onClose={onClose} actions={
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
        <Field label="Tür" required error={errors.type?.message as string}>
          <select {...register("type", { required: "Tür seçimi zorunludur." })}>
            <option value="">Seçiniz</option>
            <option value="MEDICATION">İlaç</option>
            <option value="REQUEST">Talep</option>
            <option value="NOTICE">Bildirim</option>
          </select>
        </Field>
        <Field label="Açıklama" full error={errors.description?.message as string}>
          <textarea {...register("description")} />
        </Field>
      </form>
    </Modal>
  );
}

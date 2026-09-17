import { Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function ParentNoticesPage() {
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

  useEffect(() => { load(1); }, []);

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

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Veli Talepleri & İlaç"
        description="Veli taleplerini ve ilaç bildirimlerini yönetin."
      >
        {can("communication.write") && (
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
          canEdit={can("communication.write")}
          onDelete={can("communication.write") ? handleDelete : undefined}
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

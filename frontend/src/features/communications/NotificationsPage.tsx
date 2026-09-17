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

export function NotificationsPage() {
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
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/notifications", {
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
      await api.delete(`/notifications/${row.id}`);
      showToast("Bildirim silindi", "Bildirim başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Bildirimler"
        description="Toplu bildirimleri ve gönderim geçmişini yönetin."
      >
        {can("communication.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni bildirim
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
            { key: "title", label: "Başlık" },
            { key: "type", label: "Tür" },
            { key: "target_audience", label: "Hedef kitle" },
            { key: "scheduled_for", label: "Planlanan", type: "date" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/notifications"
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
      await api.post("/notifications", values);
      showToast("Bildirim oluşturuldu", "Yeni bildirim başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni bildirim" description="Bildirim bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Başlık" required error={errors.title?.message as string}>
          <input {...register("title", { required: "Başlık zorunludur." })} />
        </Field>
        <Field label="Tür" required error={errors.type?.message as string}>
          <select {...register("type", { required: "Tür seçimi zorunludur." })}>
            <option value="">Seçiniz</option>
            <option value="SMS">SMS</option>
            <option value="EMAIL">E-posta</option>
            <option value="PUSH">Push bildirim</option>
          </select>
        </Field>
        <Field label="Hedef kitle" required error={errors.target_audience?.message as string}>
          <select {...register("target_audience", { required: "Hedef kitle zorunludur." })}>
            <option value="">Seçiniz</option>
            <option value="ALL">Tümü</option>
            <option value="PARENTS">Veliler</option>
            <option value="STAFF">Personel</option>
            <option value="STUDENTS">Öğrenciler</option>
          </select>
        </Field>
        <Field label="Planlanan tarih" error={errors.scheduled_for?.message as string}>
          <input type="datetime-local" {...register("scheduled_for")} />
        </Field>
        <Field label="İçerik" full error={errors.content?.message as string}>
          <textarea {...register("content")} />
        </Field>
      </form>
    </Modal>
  );
}

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

export function BranchesPage() {
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
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/branches", {
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
      await api.delete(`/branches/${row.id}`);
      showToast("Şube silindi", "Şube başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Yönetim"
        title="Şubeler"
        description="Okul şubelerini yönetin ve ayarları düzenleyin."
      >
        {can("branch.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni şube
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
            { key: "name", label: "Şube adı" },
            { key: "code", label: "Kod" },
            { key: "city", label: "Şehir" },
            { key: "district", label: "İlçe" },
            { key: "phone", label: "Telefon" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/branches"
          canEdit={can("branch.write")}
          onDelete={can("branch.write") ? handleDelete : undefined}
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
      await api.post("/branches", values);
      showToast("Şube oluşturuldu", "Yeni şube başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni şube" description="Şube bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Şube adı" required error={errors.name?.message as string}>
          <input {...register("name", { required: "Şube adı zorunludur." })} />
        </Field>
        <Field label="Kod" required error={errors.code?.message as string}>
          <input {...register("code", { required: "Şube kodu zorunludur." })} />
        </Field>
        <Field label="Şehir" error={errors.city?.message as string}>
          <input {...register("city")} />
        </Field>
        <Field label="İlçe" error={errors.district?.message as string}>
          <input {...register("district")} />
        </Field>
        <Field label="Telefon" error={errors.phone?.message as string}>
          <input {...register("phone")} />
        </Field>
        <Field label="Adres" full error={errors.address?.message as string}>
          <textarea {...register("address")} />
        </Field>
      </form>
    </Modal>
  );
}

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

export function StaffPage() {
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
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/staff", {
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
      await api.delete(`/staff/${row.id}`);
      showToast("Personel silindi", "Personel başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Yönetim"
        title="Personel & Nöbet"
        description="Personel listesini ve nöbet çizelgesini yönetin."
      >
        {can("user.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni personel
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
            { key: "first_name", label: "Ad" },
            { key: "last_name", label: "Soyad" },
            { key: "position", label: "Ünvan" },
            { key: "department", label: "Departman" },
            { key: "phone", label: "Telefon" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/staff"
          canEdit={can("user.write")}
          onDelete={can("user.write") ? handleDelete : undefined}
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
      await api.post("/staff", values);
      showToast("Personel oluşturuldu", "Yeni personel başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni personel" description="Personel bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Ad" required error={errors.first_name?.message as string}>
          <input {...register("first_name", { required: "Ad zorunludur." })} />
        </Field>
        <Field label="Soyad" required error={errors.last_name?.message as string}>
          <input {...register("last_name", { required: "Soyad zorunludur." })} />
        </Field>
        <Field label="Ünvan" error={errors.position?.message as string}>
          <input {...register("position")} />
        </Field>
        <Field label="Departman" error={errors.department?.message as string}>
          <input {...register("department")} />
        </Field>
        <Field label="Telefon" error={errors.phone?.message as string}>
          <input {...register("phone")} />
        </Field>
        <Field label="E-posta" error={errors.email?.message as string}>
          <input type="email" {...register("email")} />
        </Field>
      </form>
    </Modal>
  );
}

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

export function ExpensesPage() {
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
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/finance/expenses", {
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
      await api.delete(`/finance/expenses/${row.id}`);
      showToast("Gider silindi", "Gider başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Finans"
        title="Giderler & Harcamalar"
        description="Okul giderlerini ve harcamalarını yönetin."
      >
        {can("finance.write") && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni gider
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
            { key: "description", label: "Açıklama" },
            { key: "category", label: "Kategori" },
            { key: "amount", label: "Tutar", type: "money" },
            { key: "expense_date", label: "Tarih", type: "date" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/finance/expenses"
          canEdit={can("finance.write")}
          onDelete={can("finance.write") ? handleDelete : undefined}
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
      await api.post("/finance/expenses", values);
      showToast("Gider oluşturuldu", "Yeni gider başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni gider" description="Gider bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Açıklama" required error={errors.description?.message as string}>
          <input {...register("description", { required: "Açıklama zorunludur." })} />
        </Field>
        <Field label="Kategori" required error={errors.category?.message as string}>
          <select {...register("category", { required: "Kategori zorunludur." })}>
            <option value="">Seçiniz</option>
            <option value="SALARY">Maaş</option>
            <option value="UTILITIES">Faturalar</option>
            <option value="MAINTENANCE">Bakım</option>
            <option value="SUPPLIES">Malzeme</option>
            <option value="OTHER">Diğer</option>
          </select>
        </Field>
        <Field label="Tutar" required error={errors.amount?.message as string}>
          <input type="number" step="0.01" {...register("amount", { required: "Tutar zorunludur." })} />
        </Field>
        <Field label="Tarih" error={errors.expense_date?.message as string}>
          <input type="date" {...register("expense_date")} />
        </Field>
        <Field label="Notlar" full error={errors.notes?.message as string}>
          <textarea {...register("notes")} />
        </Field>
      </form>
    </Modal>
  );
}

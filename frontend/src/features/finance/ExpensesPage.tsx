import { Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { ExpenseCreateModal } from "./ExpenseCreateModal";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import { expenseScope } from "./expenseAttempt";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function ExpensesPage() {
  const user = useAuthStore((s) => s.user), session = useAuthStore((s) => s.sessionVersion);
  const workspace = usePlatformWorkspace((s) => s.workspace);
  return <ScopedExpensesPage key={JSON.stringify([expenseScope(user, workspace)?.key, session, user?.permissions])} />;
}

function ScopedExpensesPage() {
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    setError("");
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

      {createOpen && <ExpenseCreateModal onClose={() => setCreateOpen(false)} onSuccess={() => load()} />}
    </>
  );
}


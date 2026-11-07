import { getAnalysis } from "../../lib/analysis";
import { Plus, Upload, BookOpen, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { ExcelImport } from "../../components/ExcelImport";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function LibraryPage() {
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/library/books", {
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

  useEffect(() => {
    getAnalysis("/ai/library-analysis").then((r) => setAiAnalysis(r.data.data)).catch(() => {});
  }, []);

  const filtered = useMemo(() => 
    data.items.filter((r) => JSON.stringify(r).toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))),
    [data.items, search]
  );

  async function handleDelete(row: DataRecord) {
    try {
      await api.delete(`/library/books/${row.id}`);
      showToast("Kitap silindi", "Kitap başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Eğitim"
        title="Kütüphane & Zimmet"
        description="Kitapları ve zimmet kayıtlarını yönetin."
      >
        {can("library.write") && (
          <>
            <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
              <Plus size={16} />Yeni kitap
            </button>
            <button className="btn btn-secondary" onClick={() => setImportOpen(true)}>
              <Upload size={16} />Excel İçe Aktar
            </button>
          </>
        )}
      </PageHeader>

      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Kütüphane Analizi</h2>
              <p>Kitap durumu ve öneriler</p>
            </div>
            <BookOpen size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Kitap</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{data.total}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Mevcut</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{data.items.reduce((sum, item) => sum + (Number(item.available_count) || 0), 0)}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Kategori</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{new Set(data.items.map(item => item.category)).size}</div>
              </div>
            </div>
            {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                {aiAnalysis.recommendations.slice(0, 3).map((rec: string, index: number) => (
                  <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                    <TrendingUp size={16} color="#176b5b" style={{ flexShrink: 0, marginTop: 2 }} />
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
            { key: "title", label: "Kitap adı" },
            { key: "author", label: "Yazar" },
            { key: "isbn", label: "ISBN" },
            { key: "category", label: "Kategori" },
            { key: "status", label: "Durum", type: "status" },
            { key: "available_count", label: "Mevcut" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/library/books"
          canEdit={can("library.write")}
          onDelete={can("library.write") ? handleDelete : undefined}
        />
      )}

      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} onSuccess={() => load()} />
      <ExcelImport
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => load()}
        endpoint="/import/library"
        title="Kitap İçe Aktarma"
        description="Excel dosyasından kitap bilgilerini toplu olarak içe aktarın."
        templateColumns={[
          { key: "title", label: "Kitap Adı", required: true },
          { key: "author", label: "Yazar", required: true },
          { key: "isbn", label: "ISBN", required: false },
          { key: "category", label: "Kategori", required: false },
          { key: "total_count", label: "Adet", required: false }
        ]}
      />
    </>
  );
}

function CreateModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const { showToast } = useToast();

  async function submit(values: any) {
    try {
      await api.post("/library/books", values);
      showToast("Kitap oluşturuldu", "Yeni kitap başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal open={open} title="Yeni kitap" description="Kitap bilgilerini girin." onClose={onClose} actions={
      <>
        <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
        <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
          <Plus size={16} />Oluştur
        </button>
      </>
    }>
      <form className="form-grid">
        <Field label="Kitap adı" required error={errors.title?.message as string}>
          <input {...register("title", { required: "Kitap adı zorunludur." })} />
        </Field>
        <Field label="Yazar" error={errors.author?.message as string}>
          <input {...register("author")} />
        </Field>
        <Field label="ISBN" error={errors.isbn?.message as string}>
          <input {...register("isbn")} />
        </Field>
        <Field label="Kategori" error={errors.category?.message as string}>
          <input {...register("category")} />
        </Field>
        <Field label="Adet" error={errors.total_count?.message as string}>
          <input type="number" {...register("total_count")} />
        </Field>
      </form>
    </Modal>
  );
}

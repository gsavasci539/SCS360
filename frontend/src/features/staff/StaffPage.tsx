import { getAnalysis } from "../../lib/analysis";
import { Plus, Users, TrendingUp } from "lucide-react";
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
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);

  async function load(page = data.page) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/users", {
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
    getAnalysis("/ai/staff-analysis").then((r) => setAiAnalysis(r.data.data)).catch(() => {});
  }, []);

  const filtered = useMemo(() => 
    data.items.filter((r) => JSON.stringify(r).toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))),
    [data.items, search]
  );

  async function handleDelete(row: DataRecord) {
    try {
      await api.delete(`/users/${row.id}`);
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

      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Personel Analizi</h2>
              <p>Personel yapısı ve öneriler</p>
            </div>
            <Users size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Personel</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.total_staff}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Aktif Personel</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.active_staff}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiAnalysis.active_staff >= aiAnalysis.total_staff * 0.9 ? "#dcfce7" : "#fef3c7" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Aktiflik Oranı</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>%{aiAnalysis.total_staff > 0 ? Math.round(aiAnalysis.active_staff / aiAnalysis.total_staff * 100) : 0}</div>
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
      await api.post("/users", values);
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
          <input type="email" {...register("email", { required: "E-posta zorunludur." })} />
        </Field>
        <Field label="Geçici şifre" required error={errors.password?.message as string}>
          <input type="password" {...register("password", { required: "Geçici şifre zorunludur.", minLength: { value: 8, message: "Şifre en az 8 karakter olmalıdır." } })} />
        </Field>
      </form>
    </Modal>
  );
}

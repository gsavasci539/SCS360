import { getAnalysis } from "../../lib/analysis";
import { Utensils, AlertCircle, CheckCircle, Upload, Plus, Edit, Trash2, X, TrendingUp } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { ExcelImport } from "../../components/ExcelImport";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import { hasPermission, useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";

interface CanteenProduct {
  id: string;
  branch_id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: number;
  image_url: string | null;
  is_available: boolean;
  allergens: string[];
  nutritional_info: Record<string, unknown> | null;
  updated_at: string;
}

export function CanteenPage() {
  const viewer = useWorkspaceUser();
  const session = useAuthStore((state) => state.sessionVersion);
  const canWrite = hasPermission(viewer, "canteen.write");
  if (!viewer || viewer.is_super_admin || !hasPermission(viewer, "canteen.read")) {
    return <p>Kantin kataloğu için yetkili kurum çalışma alanını açın.</p>;
  }
  return <CanteenCatalog canWrite={canWrite}
    key={JSON.stringify([session, viewer.id, viewer.organization_id, viewer.branch_ids, canWrite])} />;
}

function CanteenCatalog({ canWrite }: { canWrite: boolean }) {
  const [products, setProducts] = useState<CanteenProduct[]>([]);
  const [restrictions, setRestrictions] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<CanteenProduct | null>(null);
  const [branches, setBranches] = useState<Array<{ id: string; name: string }>>([]);
  const [available, setAvailable] = useState(true);
  const [revision, setRevision] = useState(0);
  const [formError, setFormError] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [formData, setFormData] = useState({
    branch_id: "",
    name: "",
    description: "",
    category: "",
    price: "",
    image_url: "",
    allergens: [] as string[],
    is_available: true,
  });
  const [saving, setSaving] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const operation = useRef<{ signature: string; id: string } | null>(null);
  useLayoutEffect(() => () => pending.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      try {
        const [productsRes, restrictionsRes, scope] = await Promise.all([
          api.get<ApiResponse<CanteenProduct[]>>("/canteen/products", { params: { is_available: available }, signal: controller.signal }),
          api.get<ApiResponse<DataRecord[]>>("/canteen/dietary-restrictions", { signal: controller.signal }),
          api.get<ApiResponse<{ branches: Array<{ id: string; name: string }> }>>("/canteen/options", { signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        setProducts(productsRes.data.data || []);
        setRestrictions(restrictionsRes.data.data || []);
        setBranches(scope.data.data.branches);
        setError("");
      } catch (err) {
        if (!controller.signal.aborted) setError(apiMessage(err));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [available, revision]);

  useEffect(() => {
    getAnalysis("/ai/canteen-analysis").then((r) => setAiAnalysis(r.data.data)).catch(() => {});
  }, []);

  const openAddModal = () => {
    if (!canWrite) return;
    setFormError("");
    operation.current = null;
    setEditingProduct(null);
    setFormData({
      branch_id: branches.length === 1 ? branches[0].id : "",
      name: "",
      description: "",
      category: "",
      price: "",
      image_url: "",
      allergens: [],
      is_available: true,
    });
    setEditModalOpen(true);
  };

  const openEditModal = (product: CanteenProduct) => {
    if (!canWrite || !product.updated_at) return;
    setFormError("");
    operation.current = null;
    setEditingProduct(product);
    setFormData({
      branch_id: product.branch_id,
      name: product.name,
      description: product.description || "",
      category: product.category || "",
      price: String(product.price),
      image_url: product.image_url || "",
      allergens: product.allergens || [],
      is_available: product.is_available,
    });
    setEditModalOpen(true);
  };

  const handleSave = async () => {
    if (!canWrite || pending.current || !branches.some((row) => row.id === formData.branch_id)) return;
    const price = formData.price.trim().replace(",", ".");
    if (!formData.name.trim() || !/^\d{1,8}(?:\.\d{1,2})?$/.test(price) || Number(price) <= 0) {
      setFormError("Ürün adı ve geçerli bir fiyat girin.");
      return;
    }
    const controller = new AbortController();
    pending.current = controller;
    const { signal } = controller;
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        branch_id: formData.branch_id,
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        category: formData.category.trim() || null,
        price,
        image_url: formData.image_url.trim() || null,
        allergens: formData.allergens,
        is_available: formData.is_available,
        nutritional_info: editingProduct?.nutritional_info ?? null,
        expected_updated_at: editingProduct?.updated_at ?? null,
      };
      const signature = JSON.stringify(payload);
      if (!operation.current || operation.current.signature !== signature) operation.current = { id: newRequestId(), signature };
      const body = { ...payload, request_id: operation.current.id };
      const id = editingProduct?.id || operation.current.id;
      const response = editingProduct ? await api.put(`/canteen/products/${encodeURIComponent(id)}`, body, { signal })
        : await api.post("/canteen/products", body, { signal });
      if (signal.aborted) return;
      if (response.data.data?.id !== id) throw new Error("Kantin ürünü kimliği doğrulanamadı.");
      const read = await api.get<ApiResponse<CanteenProduct[]>>("/canteen/products", {
        params: { record_id: id, branch_id: body.branch_id, limit: 1 }, signal,
      });
      if (signal.aborted) return;
      const rows = read.data.data;
      const stored = Array.isArray(rows) && rows.length === 1 ? rows[0] : null;
      if (!stored || stored.id !== id || stored.branch_id !== body.branch_id || stored.name !== body.name ||
        Number(stored.price) !== Number(body.price) || stored.is_available !== body.is_available ||
        stored.description !== body.description || stored.category !== body.category || stored.image_url !== body.image_url ||
        JSON.stringify(stored.allergens) !== JSON.stringify(body.allergens) ||
        (editingProduct && stored.updated_at !== response.data.data.updated_at)) throw new Error("Kayıtlı ürün form ile eşleşmedi.");
      setAvailable(body.is_available);
      setRevision((value) => value + 1);
      setEditModalOpen(false);
    } catch (err) {
      if (!signal.aborted) setFormError(apiMessage(err));
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setSaving(false);
      }
    }
  };

  const handleDelete = async (productId: string) => {
    if (!canWrite || pending.current || !confirm("Bu ürünü silmek istediğinize emin misiniz?")) return;
    const controller = new AbortController();
    pending.current = controller;
    const { signal } = controller;
    try {
      const response = await api.delete(`/canteen/products/${encodeURIComponent(productId)}`, { signal });
      if (signal.aborted) return;
      if (response.data.data?.id !== productId) throw new Error("Kantin ürünü silme yanıtı doğrulanamadı.");
      const read = await api.get<ApiResponse<CanteenProduct[]>>("/canteen/products", { params: { record_id: productId, limit: 1 }, signal });
      if (signal.aborted) return;
      if (!Array.isArray(read.data.data) || read.data.data.length) throw new Error("Ürünün silindiği doğrulanamadı.");
      setRevision((value) => value + 1);
    } catch (err) {
      if (!signal.aborted) setError(apiMessage(err));
    } finally {
      if (pending.current === controller) pending.current = null;
    }
  };

  if (loading) return <div className="card"><LoadingState label="Yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Operasyonel"
        title="Kantin & Beslenme"
        description="Kantin ürünleri ve diyet kısıtlamaları yönetimi"
      >
        {canWrite && <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button className="btn btn-primary" onClick={openAddModal}>
            <Plus size={16} />Ürün Ekle
          </button>
          <button className="btn btn-secondary" onClick={() => setImportOpen(true)}>
            <Upload size={16} />Excel İçe Aktar
          </button>
        </div>}
      </PageHeader>
      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Kantin Analizi</h2>
              <p>Ürün durumu ve öneriler</p>
            </div>
            <Utensils size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Ürün</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{products.length}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Mevcut</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{products.filter(p => p.is_available).length}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Diyet Kısıtlaması</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{restrictions.length}</div>
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
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kantin Ürünleri</h2>
          <span className="badge badge-green">{String(products.length)}</span>
        </div>
        <div className="card-pad" style={{ overflowX: "auto" }}>
          <label>Ürün durumu <select value={available ? "active" : "inactive"}
            onChange={(event) => setAvailable(event.target.value === "active")} aria-label="Liste ürün durumu">
            <option value="active">Satışa açık</option><option value="inactive">Satışa kapalı</option>
          </select></label>
          {products.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz ürün eklenmedi</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ürün Adı</th>
                  <th>Kategori</th>
                  <th>Fiyat</th>
                  <th>Durum</th>
                  {canWrite && <th>İşlemler</th>}
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td><Utensils size={14} /> {product.name}</td>
                    <td>{product.category || "-"}</td>
                    <td>{product.price.toFixed(2)} TL</td>
                    <td><Badge value={product.is_available ? "ACTIVE" : "INACTIVE"} /></td>
                    {canWrite && <td>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          aria-label={`${product.name} ürününü düzenle`}
                          disabled={!product.updated_at}
                          onClick={() => openEditModal(product)}
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          className="btn btn-danger"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          aria-label={`${product.name} ürününü sil`}
                          onClick={() => handleDelete(product.id)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Diyet Kısıtlamaları</h2>
          <span className="badge badge-green">{String(restrictions.length)}</span>
        </div>
        <div className="card-pad">
          {restrictions.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz kısıtlama eklenmedi</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Alerji Tipi</th>
                  <th>Açıklama</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {restrictions.map((restriction) => (
                  <tr key={restriction.id}>
                    <td>{String(restriction.student_name)}</td>
                    <td><AlertCircle size={14} /> {String(restriction.allergy_type)}</td>
                    <td>{String(restriction.description)}</td>
                    <td><CheckCircle size={14} /> <Badge value={String(restriction.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <ExcelImport
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => setRevision((value) => value + 1)}
        endpoint="/import/canteen"
        title="Kantin Ürün İçe Aktarma"
        description="Excel dosyasından kantin ürün bilgilerini toplu olarak içe aktarın."
        templateColumns={[
          { key: "name", label: "Ürün Adı", required: true },
          { key: "category", label: "Kategori", required: true },
          { key: "price", label: "Fiyat", required: true },
          { key: "calories", label: "Kalori", required: false },
          { key: "is_available", label: "Mevcut", required: false }
        ]}
      />

      {/* Edit/Add Modal */}
      {canWrite && editModalOpen && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>
          <div role="dialog" aria-label="Kantin ürünü formu" style={{
            backgroundColor: "white",
            borderRadius: 8,
            padding: 24,
            width: 500,
            maxWidth: "90%",
            maxHeight: "calc(100dvh - 32px)",
            overflowY: "auto",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <h3>{editingProduct ? "Ürün Düzenle" : "Yeni Ürün Ekle"}</h3>
              <button disabled={saving} aria-label="Ürün formunu kapat" onClick={() => setEditModalOpen(false)} style={{ background: "none", border: "none", cursor: "pointer" }}>
                <X size={20} />
              </button>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {formError && <p role="alert">{formError}</p>}
              <label>Şube<select aria-label="Ürün şubesi" value={formData.branch_id}
                disabled={saving} onChange={(event) => setFormData({ ...formData, branch_id: event.target.value })}>
                <option value="">Şube seçin</option>
                {branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
              </select></label>
              <label><input type="checkbox" checked={formData.is_available} disabled={saving}
                onChange={(event) => setFormData({ ...formData, is_available: event.target.checked })} /> Satışa açık</label>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Ürün Adı</label>
                <input
                  type="text"
                  aria-label="Ürün adı"
                  disabled={saving}
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Kategori</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Fiyat (TL)</label>
                <input
                  type="number"
                  aria-label="Ürün fiyatı"
                  disabled={saving}
                  step="0.01"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Açıklama</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 4, minHeight: 60 }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Resim URL</label>
                <input
                  type="text"
                  value={formData.image_url}
                  onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
            </div>
            
            <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
              <button
                className="btn btn-secondary"
                onClick={() => setEditModalOpen(false)}
              >
                İptal
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving || !formData.branch_id}
              >
                {saving ? "Kaydediliyor..." : "Kaydet"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

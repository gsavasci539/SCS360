import { Utensils, AlertCircle, CheckCircle, Upload, Plus, Edit, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { ExcelImport } from "../../components/ExcelImport";
import { api, apiMessage } from "../../lib/api";
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
  nutritional_info: any;
}

export function CanteenPage() {
  const [products, setProducts] = useState<CanteenProduct[]>([]);
  const [restrictions, setRestrictions] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<CanteenProduct | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "",
    price: "",
    image_url: "",
    allergens: [] as string[]
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [productsRes, restrictionsRes] = await Promise.all([
          api.get<ApiResponse<CanteenProduct[]>>("/canteen/products"),
          api.get<ApiResponse<DataRecord[]>>("/canteen/dietary-restrictions")
        ]);
        setProducts(productsRes.data.data || []);
        setRestrictions(restrictionsRes.data.data || []);
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const openAddModal = () => {
    setEditingProduct(null);
    setFormData({
      name: "",
      description: "",
      category: "",
      price: "",
      image_url: "",
      allergens: []
    });
    setEditModalOpen(true);
  };

  const openEditModal = (product: CanteenProduct) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      description: product.description || "",
      category: product.category || "",
      price: String(product.price),
      image_url: product.image_url || "",
      allergens: product.allergens || []
    });
    setEditModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = {
        branch_id: "00000000-0000-0000-0000-000000000000", // Default branch
        name: formData.name,
        description: formData.description || null,
        category: formData.category || null,
        price: parseFloat(formData.price),
        image_url: formData.image_url || null,
        allergens: formData.allergens
      };

      if (editingProduct) {
        await api.put(`/canteen/products/${editingProduct.id}`, payload);
      } else {
        await api.post("/canteen/products", payload);
      }

      setEditModalOpen(false);
      // Reload products
      const productsRes = await api.get<ApiResponse<CanteenProduct[]>>("/canteen/products");
      setProducts(productsRes.data.data || []);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (productId: string) => {
    if (!confirm("Bu ürünü silmek istediğinize emin misiniz?")) return;
    
    try {
      await api.delete(`/canteen/products/${productId}`);
      setProducts(products.filter(p => p.id !== productId));
    } catch (err) {
      setError(apiMessage(err));
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
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-primary" onClick={openAddModal}>
            <Plus size={16} />Ürün Ekle
          </button>
          <button className="btn btn-secondary" onClick={() => setImportOpen(true)}>
            <Upload size={16} />Excel İçe Aktar
          </button>
        </div>
      </PageHeader>
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kantin Ürünleri</h2>
          <span className="badge badge-green">{String(products.length)}</span>
        </div>
        <div className="card-pad">
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
                  <th>İşlemler</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td><Utensils size={14} /> {product.name}</td>
                    <td>{product.category || "-"}</td>
                    <td>{product.price.toFixed(2)} TL</td>
                    <td><Badge value={product.is_available ? "ACTIVE" : "INACTIVE"} /></td>
                    <td>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          onClick={() => openEditModal(product)}
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          className="btn btn-danger"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          onClick={() => handleDelete(product.id)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
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
        onSuccess={() => {
          // Reload data after import
          const load = async () => {
            setLoading(true);
            try {
              const [productsRes, restrictionsRes] = await Promise.all([
                api.get<ApiResponse<CanteenProduct[]>>("/canteen/products"),
                api.get<ApiResponse<DataRecord[]>>("/canteen/dietary-restrictions")
              ]);
              setProducts(productsRes.data.data || []);
              setRestrictions(restrictionsRes.data.data || []);
            } catch (err) {
              setError(apiMessage(err));
            } finally {
              setLoading(false);
            }
          };
          load();
        }}
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
      {editModalOpen && (
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
          <div style={{
            backgroundColor: "white",
            borderRadius: 8,
            padding: 24,
            width: 500,
            maxWidth: "90%"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <h3>{editingProduct ? "Ürün Düzenle" : "Yeni Ürün Ekle"}</h3>
              <button onClick={() => setEditModalOpen(false)} style={{ background: "none", border: "none", cursor: "pointer" }}>
                <X size={20} />
              </button>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Ürün Adı</label>
                <input
                  type="text"
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
                disabled={saving}
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

import { Check, Plus, Save, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useToast } from "../../components/Toast";
import { EmptyState, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

export function RolesPage() {
  const [roles, setRoles] = useState<DataRecord[]>([]);
  const [permissions, setPermissions] = useState<DataRecord[]>([]);
  const [selected, setSelected] = useState("");
  const [assigned, setAssigned] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState({ name: "", slug: "", description: "" });
  const { showToast } = useToast();
  const canWrite = useAuthStore((state) => state.can("user.write"));

  async function load() {
    setLoading(true);
    try {
      const [r, p] = await Promise.all([
        api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/roles"),
        api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/permissions")
      ]);
      const roleItems = toArray(r.data.data);
      setRoles(roleItems);
      setPermissions(toArray(p.data.data));
      if (!selected && roleItems[0]) setSelected(roleItems[0].id);
    } catch (e) {
      showToast("Yetki verileri yüklenemedi", apiMessage(e), "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!selected) return;
    api.get<ApiResponse<DataRecord[] | string[] | Paginated<DataRecord>>>(`/roles/${selected}/permissions`)
      .then((r) => {
        const data = r.data.data;
        const ids = Array.isArray(data)
          ? data.map((permission) => typeof permission === "string" ? permission : permission.id)
          : toArray(data).map((permission) => permission.id);
        setAssigned(new Set(ids));
      })
      .catch(() => setAssigned(new Set()));
  }, [selected]);

  const groups = useMemo(() =>
    permissions.reduce<Record<string, DataRecord[]>>((result, permission) => {
      const module = String(permission.module || "Diğer");
      (result[module] ||= []).push(permission);
      return result;
    }, {}), [permissions]);

  async function saveMatrix() {
    if (!canWrite) return;
    try {
      await api.post(`/roles/${selected}/permissions`, { permission_ids: [...assigned] });
      showToast("Yetkiler güncellendi", "Rol matrisi kaydedildi.");
    } catch (e) {
      showToast("Kaydedilemedi", apiMessage(e), "error");
    }
  }

  async function createRole() {
    if (!canWrite) return;
    try {
      await api.post("/roles", role);
      showToast("Rol oluşturuldu");
      setOpen(false);
      await load();
    } catch (e) {
      showToast("Rol oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Erişim kontrolü"
        title="Rol ve yetkiler"
        description="Her rolün görebileceği ve yönetebileceği alanları açıkça belirleyin."
      >
        {canWrite && (
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(true)}>
              <Plus size={16} />Rol ekle
            </button>
            <button className="btn btn-primary" onClick={saveMatrix} disabled={!selected}>
              <Save size={16} />Matrisi kaydet
            </button>
          </>
        )}
      </PageHeader>

      {loading ? (
        <div className="card"><LoadingState /></div>
      ) : roles.length === 0 ? (
        <div className="card"><EmptyState title="Rol bulunamadı" /></div>
      ) : (
        <div className="detail-grid">
          <aside className="card card-pad">
            <h2 style={{ font: "700 15px Manrope", margin: "0 0 12px" }}>Roller</h2>
            <div className="quick-list" style={{ padding: 0 }}>
              {roles.map((item) => (
                <button
                  key={item.id}
                  className="quick-item"
                  style={{
                    width: "100%",
                    border: selected === item.id ? "1px solid #86b9ab" : "1px solid transparent",
                    background: selected === item.id ? "#eef6f2" : "transparent",
                    textAlign: "left"
                  }}
                  onClick={() => setSelected(item.id)}
                >
                  <div className="quick-icon"><ShieldCheck size={16} /></div>
                  <div className="quick-copy">
                    <strong>{String(item.name)}</strong>
                    <span>{String(item.slug)}</span>
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="card">
            <div className="card-head">
              <div>
                <h2>Yetki matrisi</h2>
                <p>Seçili role atanacak işlem izinleri</p>
              </div>
            </div>

            {Object.entries(groups).map(([module, items]) => (
              <div key={module} style={{ padding: "0 21px 20px" }}>
                <div className="nav-section" style={{ marginLeft: 0 }}>{module}</div>
                <div className="form-grid">
                  {items?.map((permission) => (
                    <label
                      className="checkbox-line"
                      key={permission.id}
                      style={{
                        padding: "11px 12px",
                        border: "1px solid var(--line)",
                        borderRadius: 10,
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        cursor: canWrite ? "pointer" : "not-allowed"
                      }}
                    >
                      <input
                        type="checkbox"
                        disabled={!canWrite}
                        checked={assigned.has(permission.id)}
                        onChange={(e) => setAssigned((current) => {
                          const next = new Set(current);
                          if (e.target.checked) next.add(permission.id);
                          else next.delete(permission.id);
                          return next;
                        })}
                      />
                      <span style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
                        <strong style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {String(permission.name)}
                        </strong>
                        <span className="cell-sub" style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {String(permission.code)}
                        </span>
                      </span>
                      {assigned.has(permission.id) && <Check size={14} color="#176b5b" />}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </section>
        </div>
      )}

      <Modal
        open={canWrite && open}
        title="Yeni rol"
        onClose={() => setOpen(false)}
        actions={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Vazgeç</button>
            <button className="btn btn-primary" onClick={createRole}>Oluştur</button>
          </>
        }
      >
        <div className="form-grid">
          <div className="field">
            <label>Rol adı</label>
            <input value={role.name} onChange={(e) => setRole({ ...role, name: e.target.value })} />
          </div>
          <div className="field">
            <label>Kısa kod</label>
            <input value={role.slug} onChange={(e) => setRole({ ...role, slug: e.target.value })} />
          </div>
          <div className="field field-full">
            <label>Açıklama</label>
            <textarea value={role.description} onChange={(e) => setRole({ ...role, description: e.target.value })} />
          </div>
        </div>
      </Modal>
    </>
  );
}

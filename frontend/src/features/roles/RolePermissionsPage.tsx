import { ArrowLeft, Save, Shield } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, Paginated } from "../../types/api";

interface Permission {
  id: string;
  name: string;
  description: string;
  module: string;
}

interface Role {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
}

export function RolePermissionsPage() {
  const { id } = useParams();
  const [role, setRole] = useState<Role | null>(null);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { showToast } = useToast();
  const can = useAuthStore((state) => state.can);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [roleRes, permissionsRes, rolePermissionsRes] = await Promise.allSettled([
        api.get<ApiResponse<Role>>(`/roles/${id}`),
        api.get<ApiResponse<Permission[] | Paginated<Permission>>>(`/permissions`),
        api.get<ApiResponse<Permission[] | string[] | Paginated<Permission>>>(`/roles/${id}/permissions`)
      ]);

      if (roleRes.status === "fulfilled") {
        setRole(roleRes.value.data.data);
      } else {
        throw new Error(apiMessage(roleRes.reason));
      }

      if (permissionsRes.status === "fulfilled") {
        setPermissions(toArray(permissionsRes.value.data.data));
      } else {
        throw new Error(apiMessage(permissionsRes.reason));
      }

      if (rolePermissionsRes.status === "fulfilled") {
        const assigned = rolePermissionsRes.value.data.data;
        const ids = Array.isArray(assigned)
          ? assigned.map((permission) => typeof permission === "string" ? permission : permission.id)
          : toArray(assigned as Paginated<Permission>).map((permission) => permission.id);
        setSelectedPermissions(new Set(ids));
      } else {
        throw new Error(apiMessage(rolePermissionsRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function save() {
    setSaving(true);
    try {
      await api.put(`/roles/${id}/permissions`, {
        permission_ids: Array.from(selectedPermissions)
      });
      showToast("İzinler güncellendi", "Rol izinleri başarıyla kaydedildi.");
    } catch (err) {
      showToast("İzinler güncellenemedi", apiMessage(err), "error");
    } finally {
      setSaving(false);
    }
  }

  function togglePermission(permissionId: string) {
    const newSet = new Set(selectedPermissions);
    if (newSet.has(permissionId)) {
      newSet.delete(permissionId);
    } else {
      newSet.add(permissionId);
    }
    setSelectedPermissions(newSet);
  }

  function toggleModule(allPermissionsInModule: Permission[]) {
    const allIds = allPermissionsInModule.map((p) => p.id);
    const allSelected = allIds.every((id) => selectedPermissions.has(id));
    const newSet = new Set(selectedPermissions);
    
    if (allSelected) {
      allIds.forEach((id) => newSet.delete(id));
    } else {
      allIds.forEach((id) => newSet.add(id));
    }
    
    setSelectedPermissions(newSet);
  }

  if (loading) return <div className="card"><LoadingState label="İzinler yükleniyor" /></div>;
  if (error || !role) return <div className="card"><ErrorState message={error || "Rol bulunamadı."} /></div>;

  const permissionsByModule = permissions.reduce((acc, perm) => {
    if (!acc[perm.module]) acc[perm.module] = [];
    acc[perm.module].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  return (
    <>
      <PageHeader
        eyebrow="Rol izinleri"
        title={role.name}
        description={`${role.description || "Rol"} için izin atamaları.`}
      >
        <Link className="btn btn-secondary" to="/roles">
          <ArrowLeft size={16} />Rollere dön
        </Link>
        {can("user.write") && !role.is_system && (
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            <Save size={16} />{saving ? "Kaydediliyor..." : "Kaydet"}
          </button>
        )}
      </PageHeader>

      {role.is_system && (
        <div className="card" style={{ marginBottom: 18, background: "#fff2df", border: "1px solid #f5dcb0" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center", fontSize: 14, color: "#ad7020" }}>
            <Shield size={20} />
            <div>
              <strong>Sistem rolü</strong>
              <span style={{ marginLeft: 8 }}>Bu rol sistem tarafından yönetilir ve izinleri değiştirilemez.</span>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <div>
            <h2>İzin matrisi</h2>
            <p>Modül bazında izin atamaları</p>
          </div>
        </div>
        <div className="card-pad">
          {Object.entries(permissionsByModule).map(([module, modulePermissions]) => {
            const allSelected = modulePermissions.every((p) => selectedPermissions.has(p.id));
            const someSelected = modulePermissions.some((p) => selectedPermissions.has(p.id));
            
            return (
              <div key={module} style={{ marginBottom: 24, paddingBottom: 24, borderBottom: "1px solid #e7ece8" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <h3 style={{ font: "600 15px Manrope", margin: 0 }}>{module}</h3>
                  {!role.is_system && (
                    <button
                      className="btn btn-ghost"
                      onClick={() => toggleModule(modulePermissions)}
                      style={{ fontSize: 12 }}
                    >
                      {allSelected ? "Tümünü kaldır" : someSelected ? "Tümünü seç" : "Tümünü seç"}
                    </button>
                  )}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
                  {modulePermissions.map((permission) => (
                    <label
                      key={permission.id}
                      className={`checkbox-line ${selectedPermissions.has(permission.id) ? "checked" : ""}`}
                      style={{
                        padding: 12,
                        background: selectedPermissions.has(permission.id) ? "#e6f3ef" : "#f8f9fa",
                        borderRadius: 8,
                        cursor: role.is_system ? "not-allowed" : "pointer",
                        opacity: role.is_system ? 0.6 : 1
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedPermissions.has(permission.id)}
                        onChange={() => togglePermission(permission.id)}
                        disabled={role.is_system || saving}
                      />
                      <div>
                        <div style={{ font: "600 13px Manrope", marginBottom: 2 }}>{permission.name}</div>
                        <div style={{ fontSize: 12, color: "#7a8888" }}>{permission.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

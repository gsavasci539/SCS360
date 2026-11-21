import { ArrowLeft, Pencil, Shield, Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { textValue, toArray } from "../../lib/data";
import { shortDate, titleCase } from "../../lib/format";
import { useAuthStore, hasPermission } from "../../stores/auth";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

type AccessOptions = { roles: DataRecord[]; branches: DataRecord[]; allows_institution_scope?: boolean };

export function UserDetailPage() {
  const { id } = useParams();
  const [user, setUser] = useState<DataRecord | null>(null);
  const [roles, setRoles] = useState<DataRecord[]>([]);
  const [branches, setBranches] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [accessError, setAccessError] = useState(""), [saving, setSaving] = useState(false), [message, setMessage] = useState("");
  const [options, setOptions] = useState<AccessOptions | null>(null);
  const [roleIds, setRoleIds] = useState<string[]>([]), [branchIds, setBranchIds] = useState<string[]>([]);
  const viewer = useWorkspaceUser(), operator = useAuthStore((state) => state.user);
  const can = (permission: string) => hasPermission(viewer, permission);
  const writable = can("user.write");
  const canPrepare = can("role.write") && (operator?.is_super_admin || viewer?.roles.some((role) => ["owner", "org_admin"].includes(role.slug)));

  useEffect(() => {
    const controller = new AbortController();
    setOptions(null); setAccessError(""); setMessage("");
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [userRes, rolesRes, branchesRes] = await Promise.allSettled([
          api.get<ApiResponse<DataRecord>>(`/users/${id}`, { signal: controller.signal }),
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/users/${id}/roles`, { signal: controller.signal }),
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/users/${id}/branches`, { signal: controller.signal })
        ]);
        if (controller.signal.aborted) return;

        if (userRes.status === "fulfilled") {
          setUser(userRes.value.data.data);
        } else {
          throw new Error(apiMessage(userRes.reason));
        }

        if (rolesRes.status === "fulfilled") {
          setRoles(toArray(rolesRes.value.data.data));
          setRoleIds(toArray(rolesRes.value.data.data).map((row) => row.id));
        }

        if (branchesRes.status === "fulfilled") {
          setBranches(toArray(branchesRes.value.data.data));
          setBranchIds(toArray(branchesRes.value.data.data).map((row) => row.id));
        }
        if (rolesRes.status === "rejected" || branchesRes.status === "rejected") {
          setAccessError("Mevcut erişim yüklenemedi. Değişiklik yapmadan önce sayfayı yenileyin.");
        } else if (writable && !userRes.value.data.data.is_super_admin) {
          try { const response = await api.get("/users/options", { params: { organization_id: userRes.value.data.data.organization_id }, signal: controller.signal });
            if (!controller.signal.aborted) { setOptions(response.data.data); setAccessError(""); }
          } catch (reason) { if (!controller.signal.aborted) setAccessError(apiMessage(reason)); }
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(apiMessage(err));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [id, writable]);

  async function saveAccess(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving) return; setSaving(true); setMessage(""); setAccessError("");
    try {
      const updated = await api.put<ApiResponse<{ user_id: string; role_ids: string[]; branch_ids: string[] }>>(`/users/${id}/access`, {
        role_ids: roleIds, branch_ids: branchIds, expected_role_ids: roles.map((row) => row.id), expected_branch_ids: branches.map((row) => row.id),
      });
      const ack = updated.data.data;
      const same = (left: string[], right: string[]) => left.length === right.length && left.every((value) => right.includes(value));
      if (!updated.data.success || ack?.user_id !== id || !same(ack.role_ids, roleIds) || !same(ack.branch_ids, branchIds)) {
        throw new Error("Erişim kaydı onaylanmadı");
      }
      const [roleReply, branchReply] = await Promise.all([
        api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/users/${id}/roles`),
        api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/users/${id}/branches`),
      ]);
      const storedRoles = toArray(roleReply.data.data), storedBranches = toArray(branchReply.data.data);
      if (!roleReply.data.success || !branchReply.data.success
          || !same(storedRoles.map((row) => row.id), roleIds) || !same(storedBranches.map((row) => row.id), branchIds)) {
        throw new Error("Kaydedilen rol ve şubeler doğrulanamadı");
      }
      setRoles(storedRoles);
      setBranches(storedBranches);
      setMessage("Rol ve şube erişimi kaydedildi.");
      if (useAuthStore.getState().user?.id === id) { const response = await api.get("/auth/me"); useAuthStore.getState().setUser(response.data.data); }
    } catch (reason) { setAccessError(apiMessage(reason)); } finally { setSaving(false); }
  }
  function checked(values: string[], value: string, enabled: boolean) { return enabled ? [...new Set([...values, value])] : values.filter((item) => item !== value); }
  async function prepareRoles() {
    if (saving || !user) return; setSaving(true); setAccessError(""); setMessage("");
    try {
      const organization = String(user.organization_id);
      const receipt = await api.post<ApiResponse<{ organization_id: string; role_slugs: string[] }>>("/users/role-catalog", { organization_id: organization });
      const verified = receipt.data.data;
      if (!receipt.data.success || verified?.organization_id !== organization || !verified.role_slugs?.length) {
        throw new Error("Kurum rol kataloğu onaylanmadı");
      }
      const response = await api.get<ApiResponse<AccessOptions>>("/users/options", { params: { organization_id: organization } });
      const saved = response.data.data;
      if (!response.data.success || !verified.role_slugs.every((slug) =>
        saved.roles.some((row) => row.slug === slug && row.organization_id === organization))) {
        throw new Error("Kurumun standart rolleri doğrulanamadı");
      }
      setOptions(saved);
      setMessage("Eksik standart kurum rolleri tamamlandı.");
    }
    catch (reason) { setAccessError(apiMessage(reason)); } finally { setSaving(false); }
  }

  if (loading) return <div className="card"><LoadingState label="Kullanıcı bilgileri yükleniyor" /></div>;
  if (error || !user) return <div className="card"><ErrorState message={error || "Kullanıcı bulunamadı."} /></div>;

  const displayName = [user.first_name, user.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ") || textValue(user.email);

  return (
    <>
      <PageHeader
        eyebrow="Kullanıcı profili"
        title={displayName}
        description="Kullanıcı bilgileri, roller ve şube atamaları."
      >
        <Link className="btn btn-secondary" to="/users">
          <ArrowLeft size={16} />Listeye dön
        </Link>
        {can("user.write") && (
          <Link className="btn btn-primary" to={`/users/${id}/edit`}>
            <Pencil size={16} />Düzenle
          </Link>
        )}
      </PageHeader>

      {writable && !user.is_super_admin && <section className="card card-pad account-workspace" style={{ marginBottom: 18 }}><h2>Rol ve şube erişimi</h2>
        {canPrepare && <button className="btn btn-secondary" disabled={saving} onClick={prepareRoles}>Eksik standart rolleri ekle</button>}
        {accessError && <p role="alert">{accessError}</p>}{message && <p role="status">{message}</p>}
        {options && <form aria-label="Kullanıcı erişimini düzenle" onSubmit={saveAccess}><fieldset disabled={saving} style={{ border: 0, padding: 0, display: "grid", gap: 14 }}>
          <fieldset><legend>Roller</legend>{options.roles.map((row) => <label key={row.id} style={{ display: "block", margin: "8px 0" }}><input type="checkbox" checked={roleIds.includes(row.id)} disabled={row.assignable === false} onChange={(event) => setRoleIds(checked(roleIds, row.id, event.target.checked))} /> {String(row.name)}{row.organization_id === null ? " · Genel rol" : row.organization_id ? " · Kurum rolü" : ""}</label>)}</fieldset>
          <fieldset><legend>Şube erişimi</legend>{options.branches.map((row) => <label key={row.id} style={{ display: "block", margin: "8px 0" }}><input type="checkbox" checked={branchIds.includes(row.id)} onChange={(event) => setBranchIds(checked(branchIds, row.id, event.target.checked))} /> {String(row.name)}</label>)}
            <p>{options.allows_institution_scope === false ? "En az bir yetkili şube seçin." : "Şube seçilmezse hesap, rolünün izin verdiği kurum kapsamını kullanır."}</p></fieldset>
          <button className="btn btn-primary" disabled={options.allows_institution_scope === false && branchIds.length === 0}>Erişimi kaydet</button>
        </fieldset></form>}
      </section>}

      <div className="detail-grid">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Kişisel bilgiler</h2>
              <p>Kullanıcının temel bilgileri</p>
            </div>
          </div>
          <div className="card-pad detail-list">
            <div className="detail-item">
              <small>Ad</small>
              <strong>{titleCase(user.first_name)}</strong>
            </div>
            <div className="detail-item">
              <small>Soyad</small>
              <strong>{titleCase(user.last_name)}</strong>
            </div>
            <div className="detail-item">
              <small>E-posta</small>
              <strong>{String(user.email)}</strong>
            </div>
            <div className="detail-item">
              <small>Telefon</small>
              <strong>{user.phone ? String(user.phone) : "-"}</strong>
            </div>
            <div className="detail-item">
              <small>Durum</small>
              <strong><Badge value={user.status} /></strong>
            </div>
            {user.created_at && (
              <div className="detail-item">
                <small>Kayıt tarihi</small>
                <strong>{shortDate(user.created_at)}</strong>
              </div>
            )}
          </div>
        </div>

        <aside className="card card-pad">
          <h2 style={{ margin: "0 0 15px", font: "700 15px Manrope" }}>Hızlı bilgiler</h2>
          <div className="quick-list" style={{ padding: 0 }}>
            <div className="quick-item" style={{ cursor: "default" }}>
              <div className="quick-icon"><Shield size={16} /></div>
              <div className="quick-copy">
                <strong>{roles.length} rol</strong>
                <span>Atanmış roller</span>
              </div>
            </div>
            <div className="quick-item" style={{ cursor: "default" }}>
              <div className="quick-icon"><Building2 size={16} /></div>
              <div className="quick-copy">
                <strong>{branches.length} şube</strong>
                <span>Erişim izni</span>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {roles.length > 0 && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>Roller</h2>
              <p>Kullanıcıya atanan roller</p>
            </div>
          </div>
          <div className="card-pad">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {roles.map((role) => (
                <span key={role.id} className="badge badge-neutral">
                  <Shield size={12} style={{ marginRight: 4 }} />
                  {String(role.name)}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {branches.length > 0 && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>Şube erişimi</h2>
              <p>Kullanıcının erişebildiği şubeler</p>
            </div>
          </div>
          <div className="card-pad">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {branches.map((branch) => (
                <div key={branch.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Building2 size={14} style={{ color: "#7a8888" }} />
                  <span style={{ font: "600 14px Manrope" }}>{String(branch.name)}</span>
                  {branch.code && (
                    <span style={{ fontSize: 12, color: "#7a8888" }}>({String(branch.code)})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

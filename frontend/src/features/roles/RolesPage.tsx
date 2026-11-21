import { Plus, Save, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse } from "../../types/api";

interface Role { id: string; name: string; slug: string; description: string | null; is_system: boolean; organization_id: string | null }
interface Permission { id: string; code: string; name: string; module: string; description: string | null; assignable: boolean }
interface Matrix { roleId: string; saved: Set<string>; draft: Set<string> }
const emptyRole = { name: "", slug: "", description: "" };

function verified<T>(reply: ApiResponse<T>): T {
  if (!reply.success || reply.data == null) throw new Error("Sunucu rol kaydını doğrulamadı");
  return reply.data;
}

function sameIds(left: Set<string>, right: Set<string>) {
  return left.size === right.size && [...left].every((id) => right.has(id));
}

async function readMatrix(roleId: string, signal?: AbortSignal) {
  const response = await api.get<ApiResponse<Permission[]>>(`/roles/${roleId}/permissions`, { signal });
  return new Set(verified(response.data).map((row) => row.id));
}

export function RolesPage({ initialRoleId }: { initialRoleId?: string } = {}) {
  const user = useAuthStore((state) => state.user);
  const canWrite = useAuthStore((state) => state.can("users.write") || state.can("role.write"));
  const workspace = usePlatformWorkspace((state) => state.workspace?.id);
  const organization = user?.is_super_admin ? workspace : user?.organization_id;
  if (!organization) return <ErrorState message="Rol yönetimi için kurum çalışma alanını seçin." />;
  return <RoleWorkspace key={JSON.stringify([user?.id, organization, initialRoleId])}
    organization={organization} initialRoleId={initialRoleId} canWrite={canWrite} />;
}

function RoleWorkspace({ organization, initialRoleId, canWrite }: { organization: string; initialRoleId?: string; canWrite: boolean }) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selected, setSelected] = useState(initialRoleId || "");
  const [matrix, setMatrix] = useState<Matrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [matrixError, setMatrixError] = useState("");
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [matrixRevision, setMatrixRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState(emptyRole);
  const createAttempt = useRef<{ signature: string; id: string } | null>(null);
  const active = useRef(false);
  const { showToast } = useToast();

  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);

  useEffect(() => {
    const controller = new AbortController();
    setError(""); setLoading(true);
    Promise.all([
      api.get<ApiResponse<Role[]>>("/roles", { signal: controller.signal }),
      api.get<ApiResponse<Permission[]>>("/permissions", { signal: controller.signal }),
    ]).then(([roleResult, permissionResult]) => {
      if (controller.signal.aborted) return;
      const rows = verified(roleResult.data);
      setRoles(rows); setPermissions(verified(permissionResult.data));
      setSelected((current) => current || rows[0]?.id || "");
    }).catch((reason) => {
      if (!controller.signal.aborted) setError(apiMessage(reason));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [revision]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setMatrix(null); setMatrixError("");
    readMatrix(selected, controller.signal).then((saved) => {
      if (!controller.signal.aborted) setMatrix({ roleId: selected, saved, draft: new Set(saved) });
    }).catch((reason) => {
      if (!controller.signal.aborted) setMatrixError(apiMessage(reason));
    });
    return () => controller.abort();
  }, [selected, matrixRevision]);

  const groups = useMemo(() => {
    const grouped = new Map<string, Permission[]>();
    for (const permission of permissions) {
      const rows = grouped.get(permission.module) ?? [];
      rows.push(permission);
      grouped.set(permission.module, rows);
    }
    return [...grouped];
  }, [permissions]);
  const selectedRole = roles.find((item) => item.id === selected);
  const editable = canWrite && selectedRole?.organization_id === organization && !selectedRole.is_system;
  const activeMatrix = matrix?.roleId === selected ? matrix : null;
  const setPermission = useCallback((id: string, checked: boolean) => {
    setMatrix((current) => {
      if (!current) return current;
      const draft = new Set(current.draft);
      if (checked) draft.add(id); else draft.delete(id);
      return { ...current, draft };
    });
  }, []);

  async function saveMatrix() {
    if (!editable || !activeMatrix || busy || sameIds(activeMatrix.saved, activeMatrix.draft)) return;
    setBusy(true);
    const { roleId, draft, saved } = activeMatrix;
    try {
      const reply = await api.put<ApiResponse<{ role_id: string; permission_ids: string[] }>>(`/roles/${roleId}/permissions`,
        { permission_ids: [...draft], expected_permission_ids: [...saved] });
      const ack = verified(reply.data);
      if (ack.role_id !== roleId || !sameIds(new Set(ack.permission_ids), draft)) throw new Error("Rol izinleri doğrulanamadı");
      if (!active.current) return;
      const persisted = await readMatrix(roleId);
      if (!active.current) return;
      if (!sameIds(persisted, draft)) throw new Error("Kalıcı rol izinleri doğrulanamadı");
      setMatrix({ roleId, saved: persisted, draft: new Set(persisted) });
      showToast("Rol izinleri doğrulandı");
    } catch (e) {
      if (active.current) showToast("Rol izinleri doğrulanamadı", apiMessage(e), "error");
    } finally { if (active.current) setBusy(false); }
  }

  async function createRole() {
    if (!canWrite || busy) return;
    const draft = { name: role.name.trim(), slug: role.slug.trim().toLowerCase(), description: role.description.trim() || null };
    if (!draft.name || !/^[a-z][a-z0-9_-]*$/.test(draft.slug)) return;
    const signature = JSON.stringify(draft);
    if (createAttempt.current?.signature !== signature) createAttempt.current = { signature, id: newRequestId() };
    const requestId = createAttempt.current.id;
    setBusy(true);
    try {
      const reply = await api.post<ApiResponse<Role>>("/roles", { ...draft, request_id: requestId });
      if (verified(reply.data).id !== requestId) throw new Error("Rol kimliği doğrulanamadı");
      if (!active.current) return;
      const stored = verified((await api.get<ApiResponse<Role>>(`/roles/${requestId}`)).data);
      if (!active.current) return;
      if (stored.id !== requestId || stored.organization_id !== organization || stored.is_system
          || stored.name !== draft.name || stored.slug !== draft.slug || stored.description !== draft.description) {
        throw new Error("Kalıcı rol doğrulanamadı");
      }
      createAttempt.current = null;
      setRoles((rows) => [...rows.filter((row) => row.id !== stored.id), stored]);
      setSelected(stored.id); setOpen(false); setRole(emptyRole); setRevision((current) => current + 1);
      showToast("Kurum rolü doğrulandı");
    } catch (e) {
      if (active.current) showToast("Kurum rolü doğrulanamadı", apiMessage(e), "error");
    } finally { if (active.current) setBusy(false); }
  }

  return <>
    <PageHeader eyebrow="Erişim kontrolü" title="Rol ve yetkiler" description="Kurum rolleri ve işlem izinleri">
      {initialRoleId && <Link className="btn btn-secondary" to="/roles">Rollere dön</Link>}
      {canWrite && <button className="btn btn-secondary" disabled={busy} onClick={() => setOpen(true)}><Plus size={16} />Rol ekle</button>}
      {editable && <button className="btn btn-primary" onClick={saveMatrix}
        disabled={busy || !activeMatrix || sameIds(activeMatrix.saved, activeMatrix.draft)}><Save size={16} />Matrisi kaydet</button>}
    </PageHeader>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((current) => current + 1)} />
      : roles.length === 0 ? <EmptyState title="Kurum rolü bulunamadı" /> : <div className="detail-grid">
      <aside className="card card-pad">
        <h2>Roller</h2>
        <div className="quick-list" style={{ padding: 0 }}>
          {roles.map((item) => <button type="button" key={item.id} className="quick-item"
            style={{ textAlign: "left", width: "100%" }} aria-pressed={selected === item.id} disabled={busy} onClick={() => setSelected(item.id)}>
            <span className="quick-icon"><ShieldCheck size={16} /></span>
            <span className="quick-copy"><strong>{item.name}</strong><span>{item.slug}</span></span>
          </button>)}
        </div>
      </aside>
      <section className="card card-pad" aria-label="Yetki matrisi">
        <h2>{selectedRole?.name || "Yetki matrisi"}</h2>
        {selectedRole?.description && <p>{selectedRole.description}</p>}
        {selectedRole?.is_system && <p>Sistem rolü salt okunur.</p>}
        {matrixError ? <ErrorState message={matrixError} retry={() => setMatrixRevision((current) => current + 1)} />
          : !activeMatrix ? <LoadingState label="Rol izinleri yükleniyor" /> : <>
          {editable && <button className="btn btn-secondary" disabled={busy} onClick={() => setMatrixRevision((current) => current + 1)}>
            Güncel izinleri yeniden yükle
          </button>}
          {groups.map(([module, items]) => <section key={module}>
            <h3>{module}</h3>
            <div className="form-grid">{items.map((permission) => <label className="checkbox-line" key={permission.id}>
              <input type="checkbox" checked={activeMatrix.draft.has(permission.id)}
                disabled={busy || !editable || !permission.assignable} onChange={(event) => setPermission(permission.id, event.target.checked)} />
              <span>{permission.name}</span>
            </label>)}</div>
          </section>)}
        </>}
      </section>
    </div>}
    {open && <Modal open title="Yeni kurum rolü" onClose={() => { if (!busy) setOpen(false); }}
      actions={<button className="btn btn-primary" disabled={busy || !role.name.trim() || !/^[a-z][a-z0-9_-]*$/.test(role.slug.trim().toLowerCase())}
        onClick={createRole}>Rolü kaydet</button>}>
      <div className="form-grid">
        <label>Rol adı<input value={role.name} maxLength={100} disabled={busy} onChange={(event) => setRole({ ...role, name: event.target.value })} /></label>
        <label>Rol kodu<input value={role.slug} maxLength={100} disabled={busy} onChange={(event) => setRole({ ...role, slug: event.target.value })} /></label>
        <label>Açıklama<textarea value={role.description} maxLength={2000} disabled={busy} onChange={(event) => setRole({ ...role, description: event.target.value })} /></label>
      </div>
    </Modal>}
  </>;
}

import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ErrorState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useWorkspaceUser } from "../../lib/workspaceUser";

export function UserCreatePage() {
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [organizations, setOrganizations] = useState<Array<{ id: string; name: string }>>([]);
  const user = useWorkspaceUser(); const navigate = useNavigate();
  useEffect(() => {
    const controller = new AbortController();
    if (user?.is_super_admin) api.get("/users/options", { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) setOrganizations(response.data.data.organizations);
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); });
    return () => controller.abort();
  }, [user?.is_super_admin]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; setBusy(true); setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try { const response = await api.post("/users", data); navigate(`/users/${response.data.data.id}`); }
    catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <>
    <PageHeader eyebrow="Kullanıcı Yönetimi" title="Yeni Kullanıcı" description="Hesabı oluşturduktan sonra profilinden rol ve şube erişimini atayın."><Link className="btn btn-secondary" to="/users">Listeye dön</Link></PageHeader>
    <section className="card card-pad account-workspace" style={{ marginTop: 18 }}>{error && <ErrorState message={error} />}<form aria-label="Kullanıcı oluştur" onSubmit={submit}><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 16 }}>
      <label>Ad<input className="filter-select" name="first_name" maxLength={100} autoComplete="given-name" required /></label>
      <label>Soyad<input className="filter-select" name="last_name" maxLength={100} autoComplete="family-name" required /></label>
      <label>E-posta<input className="filter-select" name="email" type="email" maxLength={255} autoComplete="email" required /></label>
      <label>Başlangıç parolası<input className="filter-select" name="password" type="password" minLength={8} maxLength={4096} autoComplete="new-password" required /></label>
      <label>Telefon<input className="filter-select" name="phone" type="tel" maxLength={20} autoComplete="tel" /></label>
      {user?.is_super_admin && <label>Kurum<select className="filter-select" name="organization_id" required defaultValue={user.organization_id || ""}><option value="">Kurum seçin</option>{organizations.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>}
      <button className="btn btn-primary">{busy ? "Kaydediliyor…" : "Kullanıcıyı oluştur"}</button>
    </fieldset></form></section>
  </>;
}

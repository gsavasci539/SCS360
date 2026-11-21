import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ErrorState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import type { ApiResponse, DataRecord } from "../../types/api";

type Choice = { id: string; name: string };
type AccountOptions = { organizations: Choice[]; branches: Choice[]; allows_institution_scope: boolean };

export function UserCreatePage() {
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [options, setOptions] = useState<AccountOptions | null>(null);
  const [chosenOrganization, setChosenOrganization] = useState("");
  const [branch, setBranch] = useState("");
  const user = useWorkspaceUser(); const navigate = useNavigate();
  const organization = user?.is_super_admin ? chosenOrganization || user.organization_id : user?.organization_id;
  useEffect(() => {
    const controller = new AbortController();
    setOptions(null); setBranch("");
    api.get<ApiResponse<AccountOptions>>("/users/options", {
      params: { organization_id: organization || undefined }, signal: controller.signal,
    }).then((response) => {
      if (controller.signal.aborted) return;
      if (!response.data.success) throw new Error("Kurum ve şube seçenekleri alınamadı");
      const choices = response.data.data;
      setOptions(choices);
      if (choices.allows_institution_scope === false && choices.branches.length === 1) setBranch(choices.branches[0].id);
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); });
    return () => controller.abort();
  }, [organization]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; setBusy(true); setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    if (!data.branch_id) delete data.branch_id;
    try {
      const response = await api.post<ApiResponse<DataRecord>>("/users", data);
      const savedId = response.data.data?.id;
      if (!response.data.success || !savedId) throw new Error("Kullanıcı kimliği doğrulanamadı");
      const saved = await api.get<ApiResponse<DataRecord>>(`/users/${savedId}`);
      const record = saved.data.data;
      if (!saved.data.success || record.id !== savedId || record.organization_id !== organization ||
          record.first_name !== data.first_name || record.last_name !== data.last_name ||
          String(record.email).toLowerCase() !== String(data.email).toLowerCase()) {
        throw new Error("Kalıcı kullanıcı kaydı doğrulanamadı");
      }
      if (data.branch_id) {
        const assigned = await api.get<ApiResponse<DataRecord[]>>(`/users/${savedId}/branches`);
        if (!assigned.data.success || assigned.data.data.length !== 1 || assigned.data.data[0].id !== data.branch_id) {
          throw new Error("Başlangıç şubesi doğrulanamadı");
        }
      }
      navigate(`/users/${savedId}`);
    }
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
      {user?.is_super_admin && <label>Kurum<select className="filter-select" name="organization_id" required value={organization || ""}
        onChange={(event) => setChosenOrganization(event.target.value)}><option value="">Kurum seçin</option>{options?.organizations.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>}
      {!!options?.branches.length && <label>Başlangıç şubesi<select className="filter-select" name="branch_id" value={branch}
        required={options.allows_institution_scope === false} onChange={(event) => setBranch(event.target.value)}>
        <option value="">{options.allows_institution_scope === false ? "Şube seçin" : "Kurum geneli"}</option>
        {options.branches.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
      </select></label>}
      <button className="btn btn-primary" disabled={!options || (options.allows_institution_scope === false && !branch)}>
        {busy ? "Kaydediliyor…" : "Kullanıcıyı oluştur"}</button>
    </fieldset></form></section>
  </>;
}

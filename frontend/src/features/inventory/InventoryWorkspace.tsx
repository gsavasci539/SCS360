import { useEffect, useState, type FormEvent } from "react";
import { ErrorState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";

interface Choice { id: string; name: string; code?: string; is_assigned?: boolean }
interface Options { branches: Choice[]; locations: Choice[]; items: Choice[]; users: Choice[]; more_items?: boolean; more_users?: boolean }
const empty: Options = { branches: [], locations: [], items: [], users: [] };

export function InventoryWorkspace({ revision, onChange }: { revision: number; onChange: () => Promise<void> }) {
  const canWrite = useAuthStore((state) => state.can("inventory.write"));
  const [options, setOptions] = useState<Options>(empty);
  const [branch, setBranch] = useState("");
  const [item, setItem] = useState("");
  const [user, setUser] = useState("");
  const [itemSearch, setItemSearch] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const { showToast } = useToast();
  useEffect(() => {
    if (!canWrite) return;
    const controller = new AbortController();
    const load = () => {
      api.get("/inventory/options", { params: { branch_id: branch || undefined, item_search: itemSearch, user_search: userSearch }, signal: controller.signal }).then((response) => {
        if (controller.signal.aborted) return;
        const data = response.data.data as Options;
        setOptions(data); setError("");
        if (!branch && data.branches.length) setBranch(data.branches[0].id);
      }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); });
    };
    const timer = itemSearch || userSearch ? window.setTimeout(load, 250) : undefined;
    if (timer === undefined) load();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [canWrite, branch, itemSearch, userSearch, revision, retry]);
  if (!canWrite) return null;
  async function save(event: FormEvent<HTMLFormElement>, kind: string) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, value === "" ? null : value]));
    setBusy(true);
    try {
      if (kind === "location") await api.post("/inventory/locations", { ...data, branch_id: branch });
      if (kind === "item") await api.post("/inventory/items", { ...data, branch_id: branch });
      if (kind === "assignment") await api.post("/inventory/assignments", { ...data, item_id: item, assigned_to: user });
      if (kind === "maintenance") await api.post("/inventory/maintenance-requests", { ...data, item_id: item });
      form.reset(); showToast("Envanter kaydı güncellendi");
      await onChange();
    } catch (reason) { showToast("İşlem tamamlanamadı", apiMessage(reason), "error"); }
    finally { setBusy(false); }
  }
  const assigned = options.items.find((row) => row.id === item)?.is_assigned;
  return <section className="card card-pad inventory-workspace" aria-label="Envanter işlemleri" style={{ marginTop: 20 }}>
    <h2>Envanter işlemleri</h2>
    {error && <ErrorState message={error} retry={() => setRetry((value) => value + 1)} />}
    <div className="toolbar" style={{ flexWrap: "wrap", margin: "12px 0" }}>
      <label>Envanter şubesi<select className="filter-select" value={branch} onChange={(event) => { setBranch(event.target.value); setItem(""); setUser(""); setItemSearch(""); setUserSearch(""); setOptions((value) => ({ ...empty, branches: value.branches })); }}>
        <option value="">Şube seçin</option>{options.branches.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
      </select></label>
      <label>Demirbaş ara<input className="filter-select" value={itemSearch} onChange={(event) => { setItemSearch(event.target.value); setItem(""); setOptions((value) => ({ ...value, items: [] })); }} placeholder="Kod veya ad" /></label>
      <label>İşlem demirbaşı<select className="filter-select" value={item} onChange={(event) => setItem(event.target.value)}>
        <option value="">Demirbaş seçin</option>{options.items.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}{row.is_assigned ? " (zimmetli)" : ""}</option>)}
      </select></label>
      <label>Sorumlu ara<input className="filter-select" value={userSearch} onChange={(event) => { setUserSearch(event.target.value); setUser(""); setOptions((value) => ({ ...value, users: [] })); }} placeholder="Ad veya e-posta" /></label>
      <label>Zimmet sorumlusu<select className="filter-select" value={user} onChange={(event) => setUser(event.target.value)}>
        <option value="">Kişi seçin</option>{options.users.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
      </select></label>
    </div>
    {(options.more_items || options.more_users) && <p>Seçim listeleri ilk 100 kaydı gösterir; diğer kayıtları arayarak bulun.</p>}
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 18 }}>
      <form aria-label="Envanter konumu oluştur" onSubmit={(event) => save(event, "location")} style={{ display: "grid", gap: 10, alignContent: "start" }}>
        <h3>Yeni konum</h3><input className="filter-select" aria-label="Konum adı" name="location_name" maxLength={255} required placeholder="Konum adı" />
        <button className="btn btn-primary" disabled={busy || !branch}>Konumu oluştur</button>
      </form>
      <form aria-label="Demirbaş oluştur" onSubmit={(event) => save(event, "item")} style={{ display: "grid", gap: 10 }}>
        <h3>Yeni demirbaş</h3><input className="filter-select" aria-label="Demirbaş kodu" name="item_code" maxLength={50} required placeholder="Demirbaş kodu" />
        <input className="filter-select" aria-label="Demirbaş adı" name="item_name" maxLength={255} required placeholder="Demirbaş adı" />
        <select className="filter-select" aria-label="Demirbaş konumu" name="location_id"><option value="">Konum seçin</option>{options.locations.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
        <button className="btn btn-primary" disabled={busy || !branch}>Demirbaşı oluştur</button>
      </form>
      <form aria-label="Demirbaş zimmeti" onSubmit={(event) => save(event, "assignment")} style={{ display: "grid", gap: 10 }}>
        <h3>Zimmet oluştur</h3><label>Planlanan iade tarihi<input className="filter-select" name="return_date" type="date" /></label>
        <textarea className="filter-select" aria-label="Zimmet notu" name="notes" placeholder="Not" />
        <button className="btn btn-primary" disabled={busy || !item || !user || assigned}>Zimmeti kaydet</button>
      </form>
      <form aria-label="Bakım talebi oluştur" onSubmit={(event) => save(event, "maintenance")} style={{ display: "grid", gap: 10 }}>
        <h3>Bakım talebi</h3><textarea className="filter-select" aria-label="Bakım açıklaması" name="issue_description" required placeholder="Sorun açıklaması" />
        <select className="filter-select" aria-label="Bakım önceliği" name="priority"><option value="MEDIUM">Normal</option><option value="LOW">Düşük</option><option value="HIGH">Yüksek</option><option value="URGENT">Acil</option></select>
        <select className="filter-select" aria-label="Bakım sorumlusu" name="assigned_to"><option value="">Sorumlu seçin (isteğe bağlı)</option>{options.users.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
        <button className="btn btn-primary" disabled={busy || !item}>Bakım talebini kaydet</button>
      </form>
    </div>
  </section>;
}

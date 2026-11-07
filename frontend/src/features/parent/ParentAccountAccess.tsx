import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, apiMessage } from "../../lib/api";

interface Person { id: string; name: string; email: string }
export function ParentAccountAccess({ parentId }: { parentId: string }) {
  const [people, setPeople] = useState<Person[]>([]), [chosen, setChosen] = useState<string | null>(null);
  const [search, setSearch] = useState(""), [page, setPage] = useState(1), [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState(""), [message, setMessage] = useState("");
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    api.get(`/parents/${parentId}/account-options`, { params: { search, limit: 21, offset: (page - 1) * 20 }, signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return; setPeople(response.data.data.users || []); setChosen((current) => current === null ? response.data.data.user_id || "" : current); setError("");
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [parentId, search, page, revision]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || chosen === null) return; setBusy(true); setMessage(""); setError("");
    try { await api.put(`/parents/${parentId}/account`, { user_id: chosen || null }); setMessage("Veli giriş hesabı bağlantısı kaydedildi"); setRevision((value) => value + 1); }
    catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <section className="card card-pad saas-workspace" aria-label="Veli giriş hesabı" style={{ marginBottom: 18 }}><h2>Veli giriş hesabı</h2>
    <p>İletişim kaydını, kurumunuzdaki etkin ve Veli rolündeki giriş hesabına bağlayın. Veli yalnız bu kayıtla ilişkili öğrencilerini görür.</p>
    <p><Link to="/users/new">Yeni giriş hesabı oluştur</Link> · Hesaba kullanıcı profilinden Veli rolü verin, ardından burada seçin.</p>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <form onSubmit={save}><fieldset disabled={busy} style={{ padding: 0, border: 0, display: "grid", gap: 12 }}>
      <label>Veli hesabı ara<input className="filter-select" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} maxLength={100} /></label>
      <label>Bağlanacak giriş hesabı<select className="filter-select" disabled={loading || chosen === null} value={chosen || ""} onChange={(event) => setChosen(event.target.value)}><option value="">Giriş hesabı bağlantısı yok</option>
        {chosen && !people.some((person) => person.id === chosen) && <option value={chosen}>Seçili giriş hesabı</option>}
        {people.slice(0, 20).map((person) => <option key={person.id} value={person.id}>{person.name} · {person.email}</option>)}
      </select></label>
      <button className="btn btn-primary" disabled={loading || chosen === null}>Giriş hesabı bağlantısını kaydet</button>
    </fieldset></form>
    <nav aria-label="Veli hesabı seçenek sayfaları" style={{ display: "flex", gap: 12, marginTop: 12 }}><button className="btn btn-secondary" disabled={busy || loading || page === 1} onClick={() => setPage((value) => value - 1)}>Önceki</button><span>Sayfa {page}</span><button className="btn btn-secondary" disabled={busy || loading || people.length <= 20} onClick={() => setPage((value) => value + 1)}>Sonraki</button></nav>
  </section>;
}

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Trash2 } from "lucide-react";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { downloadFile } from "../../lib/download";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";

interface Choice { id: string; name: string; student_number?: string }
interface Options { branches: Choice[]; students: Choice[]; teachers: Choice[]; student_count: number }

export function ClubWorkspace({ onChange }: { onChange: () => Promise<void> }) {
  const canWrite = useAuthStore((state) => state.can("clubs.write"));
  const [options, setOptions] = useState<Options>({ branches: [], students: [], teachers: [], student_count: 0 });
  const [branchId, setBranchId] = useState("");
  const [clubId, setClubId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [search, setSearch] = useState("");
  const [clubSearch, setClubSearch] = useState("");
  const [eventSearch, setEventSearch] = useState("");
  const [clubs, setClubs] = useState<DataRecord[]>([]);
  const [events, setEvents] = useState<DataRecord[]>([]);
  const [moreClubs, setMoreClubs] = useState(false);
  const [moreEvents, setMoreEvents] = useState(false);
  const [catalogRevision, setCatalogRevision] = useState(0);
  const [members, setMembers] = useState<DataRecord[]>([]);
  const [certificates, setCertificates] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [memberPage, setMemberPage] = useState(1);
  const [awardPage, setAwardPage] = useState(1);
  const [moreMembers, setMoreMembers] = useState(false);
  const [moreAwards, setMoreAwards] = useState(false);
  const [optionRetry, setOptionRetry] = useState(0);
  const sequence = useRef(0);
  const { showToast } = useToast();

  const loadRecords = useCallback(async () => {
    const request = ++sequence.current;
    setLoading(true);
    setError("");
    try {
      const [memberships, awards] = await Promise.all([
        api.get("/clubs/memberships", { params: { status: "ACTIVE", limit: 21, offset: (memberPage - 1) * 20 } }),
        api.get("/clubs/certificates", { params: { limit: 21, offset: (awardPage - 1) * 20 } }),
      ]);
      if (request !== sequence.current) return;
      setMembers((memberships.data.data || []).slice(0, 20));
      setCertificates((awards.data.data || []).slice(0, 20));
      setMoreMembers((memberships.data.data || []).length > 20);
      setMoreAwards((awards.data.data || []).length > 20);
    } catch (err) { if (request === sequence.current) setError(apiMessage(err)); }
    finally { if (request === sequence.current) setLoading(false); }
  }, [memberPage, awardPage]);
  useEffect(() => { void loadRecords(); }, [loadRecords]);
  useEffect(() => {
    if (!canWrite) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.get("/clubs/options", { params: branchId ? { branch_id: branchId, search } : {}, signal: controller.signal }).then((response) => {
        if (controller.signal.aborted) return;
        const data = response.data.data as Options;
        setOptions(data);
        if (!branchId && data.branches.length) setBranchId(data.branches[0].id);
      }).catch((err) => { if (!controller.signal.aborted) setError(apiMessage(err)); });
    }, branchId && search ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [canWrite, branchId, search, optionRetry]);
  useEffect(() => {
    if (!canWrite || !branchId) { setClubs([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.get("/clubs", { params: { branch_id: branchId, search: clubSearch, limit: 101 }, signal: controller.signal }).then((response) => {
        if (!controller.signal.aborted) { setClubs((response.data.data || []).slice(0, 100)); setMoreClubs((response.data.data || []).length > 100); }
      }).catch((err) => { if (!controller.signal.aborted) setError(apiMessage(err)); });
    }, clubSearch ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [canWrite, branchId, clubSearch, catalogRevision, optionRetry]);
  useEffect(() => {
    if (!canWrite || !clubId) { setEvents([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.get("/clubs/events", { params: { club_id: clubId, search: eventSearch, limit: 101 }, signal: controller.signal }).then((response) => {
        if (!controller.signal.aborted) { setEvents((response.data.data || []).slice(0, 100)); setMoreEvents((response.data.data || []).length > 100); }
      }).catch((err) => { if (!controller.signal.aborted) setError(apiMessage(err)); });
    }, eventSearch ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [canWrite, clubId, eventSearch, catalogRevision, optionRetry]);

  async function save(event: React.FormEvent<HTMLFormElement>, kind: string) {
    event.preventDefault();
    const element = event.currentTarget;
    const form = Object.fromEntries(new FormData(element).entries());
    const body = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value === "" ? null : value]));
    setBusy(kind);
    try {
      if (kind === "club") {
        const response = await api.post("/clubs/clubs", { ...body, branch_id: branchId, max_members: Number(body.max_members || 30) });
        setClubSearch("");
        setClubs((rows) => [...rows, { ...response.data.data, branch_id: branchId }]);
        setClubId(response.data.data.id);
      }
      if (kind === "member") await api.post("/clubs/memberships", { club_id: clubId, student_id: studentId });
      if (kind === "event") await api.post("/clubs/events", { ...body, club_id: clubId });
      if (kind === "certificate") await api.post("/clubs/certificates", { ...body, student_id: studentId, template_id: "scs360" });
      if (kind !== "member") element.reset();
      setCatalogRevision((value) => value + 1);
      showToast("Kulüp kaydı güncellendi");
      await Promise.all([loadRecords(), onChange()]);
    } catch (err) { showToast("İşlem tamamlanamadı", apiMessage(err), "error"); }
    finally { setBusy(""); }
  }
  async function remove(member: DataRecord) {
    if (!window.confirm("Öğrencinin bu kulüp üyeliği sonlandırılsın mı?")) return;
    setBusy("member");
    try {
      await api.delete(`/clubs/memberships/${member.id}`);
      await Promise.all([loadRecords(), onChange()]);
    } catch (err) { showToast("Üyelik sonlandırılamadı", apiMessage(err), "error"); }
    finally { setBusy(""); }
  }
  async function download(record: DataRecord) {
    setBusy(String(record.id));
    try { await downloadFile(`/clubs/certificates/${record.id}/pdf`, `${String(record.title || "SCS360-belge")}.pdf`); }
    catch (err) { showToast("Belge indirilemedi", apiMessage(err), "error"); }
    finally { setBusy(""); }
  }
  const choices = clubs.filter((club) => club.branch_id === branchId);
  return <section aria-label="Kulüp üyelik ve belgeleri" style={{ marginTop: 18 }}>
    {error && <div className="card"><ErrorState message={error} retry={() => { void loadRecords(); setOptionRetry((value) => value + 1); }} /></div>}
    {canWrite && <div className="card card-pad" style={{ marginBottom: 18 }}>
      <h2>Kulüp işlemleri</h2>
      <div className="toolbar" style={{ flexWrap: "wrap", margin: "12px 0" }}>
        <label>İşlem şubesi<select className="filter-select" value={branchId} onChange={(event) => { setBranchId(event.target.value); setClubId(""); setStudentId(""); setSearch(""); setClubSearch(""); setEventSearch(""); setClubs([]); setEvents([]); setOptions((value) => ({ ...value, students: [], teachers: [] })); }}>
          <option value="">Şube seçin</option>{options.branches.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
        </select></label>
        <label>Kulüp ara<input className="filter-select" value={clubSearch} onChange={(event) => { setClubSearch(event.target.value); setClubId(""); setClubs([]); }} placeholder="Kulüp adı" /></label>
        <label>İşlem kulübü<select className="filter-select" value={clubId} onChange={(event) => { setClubId(event.target.value); setEventSearch(""); setEvents([]); }}>
          <option value="">Kulüp seçin</option>{choices.map((row) => <option key={row.id} value={row.id}>{String(row.club_name)}</option>)}
        </select></label>
        <label>Öğrenci ara<input className="filter-select" placeholder="Ad, soyad veya numara" value={search} onChange={(event) => { setSearch(event.target.value); setStudentId(""); setOptions((value) => ({ ...value, students: [] })); }} /></label>
        <label>İşlem öğrencisi<select className="filter-select" value={studentId} onChange={(event) => setStudentId(event.target.value)}>
          <option value="">Öğrenci seçin</option>{options.students.map((row) => <option key={row.id} value={row.id}>{row.name}{row.student_number ? ` · ${row.student_number}` : ""}</option>)}
        </select></label>
      </div>
      {options.student_count > options.students.length && <p>İlk {options.students.length} öğrenci gösteriliyor. Diğer öğrencileri ad veya numarayla arayın.</p>}
      {moreClubs && <p>İlk 100 kulüp gösteriliyor. Diğer kulüpleri adlarıyla arayın.</p>}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 18 }}>
        <form aria-label="Kulüp oluştur" onSubmit={(event) => save(event, "club")} style={{ display: "grid", gap: 10 }}>
          <h3>Yeni kulüp</h3><input className="filter-select" aria-label="Kulüp adı" name="club_name" required maxLength={255} placeholder="Kulüp adı" />
          <label>Kulüp kapasitesi<input className="filter-select" name="max_members" type="number" min={1} max={10000} defaultValue={30} required /></label>
          <select className="filter-select" name="advisor_teacher_id" aria-label="Kulüp danışmanı"><option value="">Danışman seçin</option>{options.teachers.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
          <button className="btn btn-primary" disabled={Boolean(busy) || !branchId}>Kulübü oluştur</button>
        </form>
        <form aria-label="Kulüp üyeliği" onSubmit={(event) => save(event, "member")} style={{ display: "grid", gap: 10, alignContent: "start" }}>
          <h3>Öğrenci üyeliği</h3><p>Seçili öğrenciyi seçili kulübe kaydedin.</p>
          <button className="btn btn-primary" disabled={Boolean(busy) || !clubId || !studentId}>Üyeliği kaydet</button>
        </form>
        <form aria-label="Kulüp etkinliği" onSubmit={(event) => save(event, "event")} style={{ display: "grid", gap: 10 }}>
          <h3>Yeni etkinlik</h3><input className="filter-select" aria-label="Etkinlik adı" name="event_name" required maxLength={255} placeholder="Etkinlik adı" />
          <label>Etkinlik tarihi<input className="filter-select" name="event_date" type="date" required /></label>
          <label>Etkinlik saati<input className="filter-select" name="event_time" type="time" /></label>
          <input className="filter-select" aria-label="Etkinlik konumu" name="location" maxLength={255} placeholder="Konum" />
          <button className="btn btn-primary" disabled={Boolean(busy) || !clubId}>Etkinliği oluştur</button>
        </form>
        <form aria-label="Öğrenci belgesi" onSubmit={(event) => save(event, "certificate")} style={{ display: "grid", gap: 10 }}>
          <h3>Katılım / başarı belgesi</h3><input className="filter-select" aria-label="Belge başlığı" name="title" required maxLength={255} placeholder="Belge başlığı" />
          <select className="filter-select" aria-label="Belge türü" name="certificate_type"><option value="PARTICIPATION">Katılım</option><option value="ACHIEVEMENT">Başarı</option></select>
          <textarea className="filter-select" aria-label="Belge açıklaması" name="description" maxLength={1200} placeholder="Açıklama" />
          <label>Belge etkinliği ara<input className="filter-select" value={eventSearch} onChange={(event) => { setEventSearch(event.target.value); setEvents([]); }} placeholder="Etkinlik adı" /></label>
          <select key={`${clubId}-${eventSearch}`} className="filter-select" aria-label="Belge etkinliği" name="event_id"><option value="">Etkinlik bağımsız belge</option>{events.filter((row) => row.club_id === clubId).map((row) => <option key={row.id} value={row.id}>{String(row.event_name)}</option>)}</select>
          {moreEvents && <p>İlk 100 etkinlik gösteriliyor. Diğer etkinlikleri adlarıyla arayın.</p>}
          <button className="btn btn-primary" disabled={Boolean(busy) || !studentId}>Belgeyi oluştur</button>
        </form>
      </div>
    </div>}
    {loading ? <div className="card"><LoadingState /></div> : <>
      <div className="card card-pad" style={{ marginBottom: 18 }}><h2>Aktif üyelikler</h2>{members.length === 0 ? <p>Aktif kulüp üyeliği bulunmuyor.</p> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Öğrenci</th><th>Kulüp</th><th>Katılım</th><th>İşlem</th></tr></thead><tbody>{members.map((row) => <tr key={row.id}><td>{String(row.student_name || "—")}</td><td>{String(row.club_name || "—")}</td><td>{shortDate(row.joined_date)}</td><td>{canWrite && <button className="btn btn-ghost btn-icon" disabled={Boolean(busy)} onClick={() => remove(row)} aria-label={`${String(row.student_name)} üyeliğini sonlandır`}><Trash2 size={16} /></button>}</td></tr>)}</tbody></table></div>}</div>
      {(moreMembers || memberPage > 1) && <div className="toolbar" aria-label="Üyelik sayfaları" style={{ marginBottom: 18 }}>
        <button className="btn btn-secondary" disabled={memberPage === 1} onClick={() => setMemberPage((value) => value - 1)}>Önceki</button>
        <span>Sayfa {memberPage}</span><button className="btn btn-secondary" disabled={!moreMembers} onClick={() => setMemberPage((value) => value + 1)}>Sonraki</button>
      </div>}
      <div className="card card-pad"><h2>Öğrenci belgeleri</h2>{certificates.length === 0 ? <p>Henüz belge oluşturulmadı.</p> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Belge</th><th>Öğrenci</th><th>Tür</th><th>Tarih</th><th>İndir</th></tr></thead><tbody>{certificates.map((row) => <tr key={row.id}><td>{String(row.title)}</td><td>{String(row.student_name || "—")}</td><td><Badge value={String(row.certificate_type)} /></td><td>{shortDate(row.issue_date)}</td><td><button className="btn btn-ghost btn-icon" disabled={Boolean(busy)} onClick={() => download(row)} aria-label={`${String(row.title)} indir`}><Download size={16} /></button></td></tr>)}</tbody></table></div>}</div>
      {(moreAwards || awardPage > 1) && <div className="toolbar" aria-label="Belge sayfaları" style={{ marginTop: 12 }}>
        <button className="btn btn-secondary" disabled={awardPage === 1} onClick={() => setAwardPage((value) => value - 1)}>Önceki</button>
        <span>Sayfa {awardPage}</span><button className="btn btn-secondary" disabled={!moreAwards} onClick={() => setAwardPage((value) => value + 1)}>Sonraki</button>
      </div>}
    </>}
  </section>;
}

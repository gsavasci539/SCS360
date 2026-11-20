import { getAnalysis } from "../../lib/analysis";
import { ArrowLeft, Plus, RefreshCw, Save, Send, Settings2 } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useForm, type UseFormRegisterReturn } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useAnnouncementScope } from "./useAnnouncementScope";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): DataRecord[] => Array.isArray(data) ? data : data?.items || [];

export function AnnouncementsPage() {
  const scope = useAnnouncementScope();
  if (!scope.active || !scope.canRead) return <p>Duyuru kayıtları için yetkili kurum çalışma alanını açın.</p>;
  return <AnnouncementList key={scope.key} canWrite={scope.canWrite} />;
}

interface CommunicationMetrics {
  total_notifications: number;
  total_recipients: number;
  success_rate: number;
  recommendations?: string[];
}

function AnnouncementList({ canWrite }: { canWrite: boolean }) {
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [metrics, setMetrics] = useState<CommunicationMetrics | null>(null);
  const pending = useRef<AbortController | null>(null);
  const { showToast } = useToast();
  useLayoutEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/announcements", { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) setRows(normalize(response.data.data)); })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    let active = true;
    getAnalysis("/ai/communication-analysis").then((response) => {
      const summary = response.data.data as CommunicationMetrics | null;
      if (active && summary && [summary.total_notifications, summary.total_recipients, summary.success_rate].every(Number.isFinite)) setMetrics(summary);
    }).catch(() => {});
    return () => { active = false; };
  }, [attempt]);
  async function send(row: DataRecord) {
    if (pending.current || !canWrite || row.status !== "DRAFT" || !Array.isArray(row.channels) || !row.channels.length) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      const response = await api.post<ApiResponse<{ announcement_id: string; jobs_created: number; already_queued: boolean }>>(
        `/announcements/${encodeURIComponent(row.id)}/send`, undefined, { signal: controller.signal },
      );
      if (controller.signal.aborted) return;
      const outcome = response.data.data;
      if (outcome?.announcement_id !== row.id || !Number.isInteger(outcome.jobs_created) || outcome.jobs_created < 1 ||
        typeof outcome.already_queued !== "boolean") {
        showToast("Kuyruk doğrulanamadı", "Sunucu seçili duyuru için bir bildirim işi doğrulamadı.", "error");
        return;
      }
      showToast(outcome.already_queued ? "Mevcut kuyruk kaydı doğrulandı" : "Duyuru kuyruğa alındı", `${outcome.jobs_created} bildirim işi`);
      setAttempt((value) => value + 1);
    } catch (reason) {
      if (!controller.signal.aborted) showToast("Duyuru kuyruğa alınamadı", apiMessage(reason), "error");
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  const filtered = useMemo(() => rows.filter((row) => [row.title, row.content, row.audience, row.status].some((value) =>
    String(value ?? "").toLocaleLowerCase("tr-TR").includes(search.trim().toLocaleLowerCase("tr-TR")))), [rows, search]);
  return <>
    <PageHeader eyebrow="İletişim" title="Duyurular" description="Taslakları, hedef kitleyi ve gönderim durumunu yönetin.">
      {canWrite && <Link className="btn btn-primary" to="/announcements/new"><Plus size={16} />Duyuru oluştur</Link>}
    </PageHeader>
    {metrics && <section className="card card-pad" style={{ marginBottom: 18 }} aria-label="Bildirim özeti">
      <h2>Bildirim özeti</h2><p>Bildirim {metrics.total_notifications} · Alıcı {metrics.total_recipients} · Başarı %{metrics.success_rate}</p>
      {!!metrics.recommendations?.length && <ul>{metrics.recommendations.slice(0, 3).map((item, index) => <li key={index}>{item}</li>)}</ul>}
    </section>}
    {loading ? <div className="card"><LoadingState /></div> : error ?
      <div className="card"><ErrorState message={error} retry={() => setAttempt((value) => value + 1)} /></div> :
      <DataTable rows={filtered} columns={[{ key: "title", label: "Başlık", subKey: "content" }, { key: "audience", label: "Hedef kitle" },
        { key: "channels", label: "Kanallar" }, { key: "created_at", label: "Oluşturulma", type: "date" }, { key: "status", label: "Durum", type: "status" }]}
        search={search} onSearch={setSearch} page={1} totalPages={1} total={filtered.length} onPage={() => {}} detailBase="/announcements" editBase="/announcements"
        canEdit={(row) => canWrite && row.status === "DRAFT"} rowActions={(row) =>
          canWrite && row.status === "DRAFT" && Array.isArray(row.channels) && row.channels.length > 0 ?
            <button className="btn btn-secondary" aria-label={`${row.title} duyurusunu kuyruğa al`} disabled={busy} onClick={() => void send(row)}>
              <Send size={15} />Kuyruğa al
            </button> : null} />}
  </>;
}

interface AnnouncementForm { title: string; content: string; audience: string; channels: string[]; branch_id: string; class_id: string; student_id: string }
type AnnouncementApi = Omit<AnnouncementForm, "channels"> & { id: string; channels: string | string[]; status: string };
const targetForAudience = {
  BRANCH_PARENTS: { field: "branch_id", kind: "branches", label: "Şube" },
  CLASS_PARENTS: { field: "class_id", kind: "classes", label: "Sınıf" },
  SINGLE_STUDENT: { field: "student_id", kind: "students", label: "Öğrenci" },
} as const;
type AnnouncementTarget = typeof targetForAudience[keyof typeof targetForAudience];

function AnnouncementTargetSelect({ target, selected, registration, error }: {
  target: AnnouncementTarget; selected: string; registration: UseFormRegisterReturn; error?: string;
}) {
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<{ items: { id: string; name: string }[]; more: boolean } | null>(null);
  const [failed, setFailed] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.get<ApiResponse<{ items: { id: string; name: string }[]; more: boolean }>>("/announcements/targets", {
        params: { kind: target.kind, search: search.trim(), selected_id: selected || undefined }, signal: controller.signal,
      }).then((response) => {
        if (controller.signal.aborted) return;
        if (!Array.isArray(response.data.data?.items)) {
          setFailed("Duyuru hedef listesi doğrulanamadı.");
          return;
        }
        setFailed("");
        setOptions(response.data.data);
      }).catch((reason) => { if (!controller.signal.aborted) setFailed(apiMessage(reason)); });
    }, search ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [target.kind, search, selected, attempt]);
  return <>
    <Field label={`${target.label} ara`}><input value={search} maxLength={100} onChange={(event) => setSearch(event.target.value)} /></Field>
    <Field label={target.label} required error={error}>
      <select {...registration} value={selected}>
        <option value="">{target.label} seçin</option>
        {options?.items.map((choice) => <option key={choice.id} value={choice.id}>{choice.name}</option>)}
      </select>
    </Field>
    {options?.more && <p>Diğer kayıtları adla arayın.</p>}
    {failed && <p role="alert">{failed} <button type="button" className="btn btn-secondary" onClick={() => setAttempt((value) => value + 1)}>Tekrar dene</button></p>}
  </>;
}

export function AnnouncementFormPage() {
  const { id } = useParams();
  const scope = useAnnouncementScope();
  if (!scope.active || !scope.canWrite || !scope.canRead) return <p>Duyuru taslakları için okuma ve yazma yetkisi gerekli.</p>;
  return <ScopedAnnouncementForm key={JSON.stringify([scope.key, id])} id={id} />;
}

function ScopedAnnouncementForm({ id }: { id?: string }) {
  const editing = Boolean(id);
  const { showToast } = useToast();
  const navigate = useNavigate();
  const { register, handleSubmit, watch, formState: { errors, isSubmitting }, reset } = useForm<AnnouncementForm>({
    defaultValues: { audience: "ALL_PARENTS", channels: ["EMAIL"] },
  });
  const audience = watch("audience");
  const target = targetForAudience[audience as keyof typeof targetForAudience];
  const [ready, setReady] = useState(!editing);
  const pending = useRef<AbortController | null>(null);
  useLayoutEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    api.get<ApiResponse<AnnouncementApi>>(`/announcements/${encodeURIComponent(id)}`, { signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return;
      const existing = response.data.data;
      if (existing?.id !== id || existing.status !== "DRAFT") {
        showToast("Taslak doğrulanamadı", "Yalnız seçili taslak düzenlenebilir.", "error");
        return;
      }
      reset({
        title: existing.title, content: existing.content, audience: existing.audience,
        channels: Array.isArray(existing.channels) ? existing.channels : existing.channels?.split(",") ?? [],
        branch_id: existing.branch_id || "", class_id: existing.class_id || "", student_id: existing.student_id || "",
      });
      setReady(true);
    }).catch((reason) => { if (!controller.signal.aborted) showToast("Duyuru yüklenemedi", apiMessage(reason), "error"); });
    return () => controller.abort();
  }, [id, reset, showToast]);

  async function submit(values: AnnouncementForm) {
    if (!ready || pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    const { signal } = controller;
    const body = {
      title: values.title.trim(), content: values.content.trim(), audience: values.audience,
      channels: Array.isArray(values.channels) ? [...new Set(values.channels)] : [],
      branch_id: values.audience === "BRANCH_PARENTS" ? values.branch_id?.trim() || null : null,
      class_id: values.audience === "CLASS_PARENTS" ? values.class_id?.trim() || null : null,
      student_id: values.audience === "SINGLE_STUDENT" ? values.student_id?.trim() || null : null,
    };
    try {
      const path = id ? `/announcements/${encodeURIComponent(id)}` : "/announcements";
      const response = id ? await api.put<ApiResponse<{ id: string }>>(path, body, { signal }) :
        await api.post<ApiResponse<{ id: string }>>(path, body, { signal });
      if (signal.aborted) return;
      const savedId = response.data.data?.id;
      if (!savedId || id && savedId !== id) throw new Error("Sunucu taslak kimliğini doğrulamadı.");
      const read = await api.get<ApiResponse<AnnouncementApi>>(`/announcements/${encodeURIComponent(savedId)}`, { signal });
      if (signal.aborted) return;
      const saved = read.data.data;
      if (saved?.id !== savedId || saved.status !== "DRAFT" || saved.title !== body.title || saved.content !== body.content ||
        saved.audience !== body.audience || !Array.isArray(saved.channels) ||
        saved.channels.length !== body.channels.length || body.channels.some((channel) => !saved.channels.includes(channel)) ||
        (body.branch_id && saved.branch_id !== body.branch_id) || (body.class_id && saved.class_id !== body.class_id) ||
        (body.student_id && saved.student_id !== body.student_id)) {
        showToast("Taslak doğrulanamadı", "Sunucudaki kayıt gönderilen taslakla eşleşmiyor.", "error");
        return;
      }
      showToast(editing ? "Duyuru taslağı güncellendi" : "Duyuru taslağı kaydedildi");
      navigate("/announcements");
    } catch (reason) {
      if (!signal.aborted) showToast("Duyuru taslağı kaydedilemedi", apiMessage(reason), "error");
    } finally {
      pending.current = null;
    }
  }
  return <>
    <PageHeader eyebrow="İletişim" title={editing ? "Duyuru düzenle" : "Duyuru oluştur"} description="Hedef kitleyi ve iletişim kanallarını belirleyin.">
      <Link className="btn btn-secondary" to="/announcements"><ArrowLeft size={16} />Listeye dön</Link>
    </PageHeader>
    <form className="card form-card" onSubmit={handleSubmit(submit)}>
      <fieldset disabled={!ready || isSubmitting} style={{ border: 0, padding: 0 }}>
        <div className="form-section"><h2>Mesaj</h2><div className="form-grid">
          <Field label="Duyuru başlığı" required error={errors.title?.message} full><input {...register("title", { required: "Başlık zorunludur.", minLength: 2, maxLength: 255 })} /></Field>
          <Field label="İçerik" required error={errors.content?.message} full><textarea {...register("content", { required: "İçerik zorunludur.", minLength: 10, maxLength: 10000 })} /></Field>
        </div></div>
        <div className="form-section"><h2>Hedef ve kanallar</h2><div className="form-grid">
          <Field label="Hedef kitle" required><select {...register("audience")}><option value="ALL_PARENTS">Tüm veliler</option><option value="BRANCH_PARENTS">Şube velileri</option><option value="CLASS_PARENTS">Sınıf velileri</option><option value="SINGLE_STUDENT">Tek öğrenci velisi</option></select></Field>
          {target && <AnnouncementTargetSelect key={target.kind} target={target} selected={watch(target.field) || ""}
            registration={register(target.field, { required: `${target.label} seçin.` })} error={errors[target.field]?.message} />}
          <Field label="Gönderim kanalları" full><div className="inline" style={{ gap: 16, flexWrap: "wrap" }}>
            <label className="checkbox-line"><input type="checkbox" value="EMAIL" {...register("channels")} />E-posta</label>
            <label className="checkbox-line"><input type="checkbox" value="SMS" {...register("channels")} />SMS</label>
            <label className="checkbox-line"><input type="checkbox" value="WHATSAPP" {...register("channels")} />WhatsApp</label>
          </div></Field>
        </div></div>
      </fieldset>
      <div className="form-actions"><Link className="btn btn-secondary" to="/announcements">Vazgeç</Link><button className="btn btn-primary" disabled={!ready || isSubmitting}><Save size={16} />Taslak olarak kaydet</button></div>
    </form>
  </>;
}

export function NotificationsPage() {
  const [rows, setRows] = useState<DataRecord[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [search, setSearch] = useState(""); const { showToast } = useToast(); const canWrite = useAuthStore((state) => state.can("notification.write"));
  async function load() { setLoading(true); try { const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/notifications", { params: { page_size: 100 } }); setRows(normalize(r.data.data)); } catch (e) { setError(apiMessage(e)); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  async function retry(id: string) { try { await api.post(`/notifications/${id}/retry`); showToast("Bildirim yeniden sıraya alındı"); await load(); } catch (e) { showToast("Tekrar denenemedi", apiMessage(e), "error"); } }
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(search.toLowerCase()));
  return <><PageHeader eyebrow="İletişim" title="Bildirim hareketleri" description="E-posta, SMS ve WhatsApp gönderim durumlarını takip edin."><Link className="btn btn-secondary" to="/settings/integrations"><Settings2 size={16} />Provider ayarları</Link></PageHeader>{loading ? <div className="card"><LoadingState /></div> : error ? <div className="card"><ErrorState message={error} retry={load} /></div> : rows.length === 0 ? <div className="card"><EmptyState title="Henüz bildirim hareketi yok" /></div> : <DataTable rows={filtered} columns={[{ key: "channel", label: "Kanal" }, { key: "subject", label: "Konu", subKey: "template_code" }, { key: "created_at", label: "Oluşturulma", type: "date" }, { key: "retry_count", label: "Deneme" }, { key: "status", label: "Durum", type: "status" }]} search={search} onSearch={setSearch} page={1} totalPages={1} total={filtered.length} onPage={() => {}} filters={canWrite ? <button className="btn btn-secondary" disabled={!filtered.find((r) => r.status === "FAILED")} onClick={() => { const failed = filtered.find((r) => r.status === "FAILED"); if (failed) retry(failed.id); }}><RefreshCw size={15} />Başarısızı tekrar dene</button> : undefined} />}</>;
}

export function TemplatesPage() {
  const [rows, setRows] = useState<DataRecord[]>([]); const [open, setOpen] = useState(false); const [form, setForm] = useState({ code: "", name: "", channel: "EMAIL", subject: "", body_template: "" }); const { showToast } = useToast(); const canWrite = useAuthStore((state) => state.can("notification.write"));
  async function load() { try { const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/notifications/templates"); setRows(toArray(r.data.data)); } catch (e) { showToast("Şablonlar yüklenemedi", apiMessage(e), "error"); } }
  useEffect(() => { load(); }, []);
  async function save() { try { await api.post("/notifications/templates", form); showToast("Şablon oluşturuldu"); setOpen(false); await load(); } catch (e) { showToast("Kaydedilemedi", apiMessage(e), "error"); } }
  return <><PageHeader eyebrow="İletişim" title="Mesaj şablonları" description="Tekrarlanan bildirimler için tutarlı ve değişken destekli metinler hazırlayın.">{canWrite && <button className="btn btn-primary" onClick={() => setOpen(true)}><Plus size={16} />Şablon ekle</button>}</PageHeader><div className="card">{rows.length === 0 ? <EmptyState title="Henüz şablon yok" /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Şablon</th><th>Kod</th><th>Kanal</th><th>Konu</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td className="cell-main">{String(row.name)}</td><td>{String(row.code)}</td><td>{String(row.channel)}</td><td>{String(row.subject || "—")}</td></tr>)}</tbody></table></div>}</div><Modal open={canWrite && open} title="Yeni mesaj şablonu" onClose={() => setOpen(false)} actions={<><button className="btn btn-secondary" onClick={() => setOpen(false)}>Vazgeç</button><button className="btn btn-primary" onClick={save}><Save size={15} />Kaydet</button></>}><div className="form-grid"><Field label="Şablon adı" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field><Field label="Kod" required><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></Field><Field label="Kanal"><select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })}><option>EMAIL</option><option>SMS</option><option>WHATSAPP</option></select></Field><Field label="Konu"><input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></Field><Field label="Mesaj" full><textarea value={form.body_template} onChange={(e) => setForm({ ...form, body_template: e.target.value })} placeholder="Sayın {{parent_name}}…" /></Field></div></Modal></>;
}

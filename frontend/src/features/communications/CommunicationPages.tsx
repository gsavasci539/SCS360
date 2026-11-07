import { getAnalysis } from "../../lib/analysis";
import { ArrowLeft, Plus, RefreshCw, Save, Send, Settings2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { useAuthStore } from "../../stores/auth";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): DataRecord[] => Array.isArray(data) ? data : data?.items || [];

export function AnnouncementsPage() {
  const [rows, setRows] = useState<DataRecord[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [search, setSearch] = useState(""); const [aiAnalysis, setAiAnalysis] = useState<any>(null); const { showToast } = useToast(); const can = useAuthStore((s) => s.can);
  async function load() { setLoading(true); try { const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/announcements", { params: { page_size: 100, limit: 100 } }); setRows(normalize(r.data.data)); } catch (e) { setError(apiMessage(e)); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  useEffect(() => { getAnalysis("/ai/communication-analysis").then((r) => setAiAnalysis(r.data.data)).catch(() => {}); }, []);
  async function send(id: string) { try { await api.post(`/announcements/${id}/send`); showToast("Duyuru gönderime alındı", "Seçili kanallar için bildirim işleri oluşturuldu."); await load(); } catch (e) { showToast("Gönderilemedi", apiMessage(e), "error"); } }
  const filtered = useMemo(() => rows.filter((row) => JSON.stringify(row).toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))), [rows, search]);
  return <><PageHeader eyebrow="İletişim" title="Duyurular" description="Doğru veli grubuna, doğru kanaldan anlaşılır mesajlar gönderin.">{can("announcement.write") && <Link className="btn btn-primary" to="/announcements/new"><Plus size={16} />Duyuru oluştur</Link>}</PageHeader>{aiAnalysis && <div className="card" style={{ marginBottom: 18 }}><div className="card-head"><div><h2>AI İletişim Analizi</h2><p>Duyuru gönderim istatistikleri ve öneriler</p></div><Send size={20} color="#176b5b" /></div><div className="card-pad"><div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}><div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}><div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Bildirim</div><div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.total_notifications}</div></div><div style={{ padding: 16, borderRadius: 11, background: aiAnalysis.success_rate >= 80 ? "#dcfce7" : "#fef3c7" }}><div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Başarı Oranı</div><div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>%{aiAnalysis.success_rate}</div></div><div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}><div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Alıcı</div><div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.total_recipients}</div></div></div>{aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && <div><h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>{aiAnalysis.recommendations.slice(0, 3).map((rec: string, index: number) => <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}><span style={{ fontSize: 13 }}>{rec}</span></div>)}</div>}</div></div>}{loading ? <div className="card"><LoadingState /></div> : error ? <div className="card"><ErrorState message={error} retry={load} /></div> : <DataTable rows={filtered} columns={[{ key: "title", label: "Başlık", subKey: "content" }, { key: "audience", label: "Hedef kitle" }, { key: "channels", label: "Kanallar" }, { key: "created_at", label: "Oluşturulma", type: "date" }, { key: "status", label: "Durum", type: "status" }]} search={search} onSearch={setSearch} page={1} totalPages={1} total={filtered.length} onPage={() => {}} canEdit={false} filters={can("announcement.write") ? <button className="btn btn-secondary" disabled={!filtered[0]} onClick={() => filtered[0] && send(filtered[0].id)}><Send size={15} />İlk taslağı gönder</button> : undefined} />}</>;
}

interface AnnouncementForm { title: string; content: string; audience: string; channels: string[]; branch_id: string; class_id: string; student_id: string }
type AnnouncementApi = Omit<AnnouncementForm, "channels"> & { channels: string | string[] };
export function AnnouncementFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const user = useWorkspaceUser(); const { showToast } = useToast(); const navigate = useNavigate(); const { register, handleSubmit, watch, formState: { errors, isSubmitting }, reset } = useForm<AnnouncementForm>({ defaultValues: { audience: "ALL_PARENTS", channels: ["EMAIL"] } }); const audience = watch("audience");
  
  useEffect(() => {
    if (!id) return;
    api.get<ApiResponse<AnnouncementApi>>(`/announcements/${id}`).then((response) => {
      const data = response.data.data;
      const channelsValue = data.channels;
      let channelsArray: string[] = ["EMAIL"];
      
      if (typeof channelsValue === "string") {
        channelsArray = channelsValue.split(",");
      } else if (Array.isArray(channelsValue)) {
        channelsArray = channelsValue;
      }
      
      reset({
        title: data.title,
        content: data.content,
        audience: data.audience,
        channels: channelsArray,
        branch_id: data.branch_id || "",
        class_id: data.class_id || "",
        student_id: data.student_id || ""
      });
    }).catch((error) => showToast("Duyuru yüklenemedi", apiMessage(error), "error"));
  }, [id, reset, showToast]);

  async function submit(values: AnnouncementForm) { 
    try { 
      if (editing) {
        await api.put(`/announcements/${id}`, { 
          title: values.title, 
          content: values.content, 
          audience: values.audience, 
          channels: values.channels.join(","), 
          branch_id: values.branch_id || null, 
          class_id: values.class_id || null,
          student_id: values.student_id || null
        });
        showToast("Duyuru güncellendi", "Değişiklikler kaydedildi.");
      } else {
        await api.post("/announcements", { 
          organization_id: user?.organization_id, 
          title: values.title, 
          content: values.content, 
          audience: values.audience, 
          channels: values.channels.join(","), 
          branch_id: values.branch_id || null, 
          status: "DRAFT" 
        });
        showToast("Duyuru kaydedildi", "Taslağı listeden gönderime alabilirsiniz.");
      }
      navigate("/announcements"); 
    } catch (e) { 
      showToast(editing ? "Duyuru güncellenemedi" : "Duyuru kaydedilemedi", apiMessage(e), "error"); 
    } 
  }
  return <><PageHeader eyebrow="İletişim" title={editing ? "Duyuru düzenle" : "Duyuru oluştur"} description="Hedef kitleyi ve iletişim kanallarını belirleyin."><Link className="btn btn-secondary" to="/announcements"><ArrowLeft size={16} />Listeye dön</Link></PageHeader><form className="card form-card" onSubmit={handleSubmit(submit)}><div className="form-section"><h2>Mesaj</h2><p>Veliye ulaşacak açık ve kısa metni hazırlayın.</p><div className="form-grid"><Field label="Duyuru başlığı" required error={errors.title?.message} full><input {...register("title", { required: "Başlık zorunludur.", minLength: { value: 2, message: "En az 2 karakter yazın." } })} /></Field><Field label="İçerik" required error={errors.content?.message} full><textarea {...register("content", { required: "İçerik zorunludur.", minLength: { value: 10, message: "En az 10 karakter yazın." } })} /></Field></div></div><div className="form-section"><h2>Hedef ve kanallar</h2><p>Yalnızca ilgili velilere gönderim yapılır.</p><div className="form-grid"><Field label="Hedef kitle" required><select {...register("audience")}><option value="ALL_PARENTS">Tüm veliler</option><option value="BRANCH_PARENTS">Şube velileri</option><option value="CLASS_PARENTS">Sınıf velileri</option><option value="SINGLE_STUDENT">Tek öğrenci velisi</option></select></Field>{audience === "BRANCH_PARENTS" && <Field label="Şube"><input {...register("branch_id")} placeholder="Şube ID" /></Field>}{audience === "CLASS_PARENTS" && <Field label="Sınıf"><input {...register("class_id")} placeholder="Sınıf ID" /></Field>}{audience === "SINGLE_STUDENT" && <Field label="Öğrenci"><input {...register("student_id")} placeholder="Öğrenci ID" /></Field>}<Field label="Gönderim kanalları" full><div className="inline" style={{ gap: 20, minHeight: 43 }}><label className="checkbox-line"><input type="checkbox" value="EMAIL" {...register("channels")} />E-posta</label><label className="checkbox-line"><input type="checkbox" value="SMS" {...register("channels")} />SMS</label><label className="checkbox-line"><input type="checkbox" value="WHATSAPP" {...register("channels")} />WhatsApp</label></div></Field></div></div><div className="form-actions"><Link className="btn btn-secondary" to="/announcements">Vazgeç</Link><button className="btn btn-primary" disabled={isSubmitting}><Save size={16} />Taslak olarak kaydet</button></div></form></>;
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

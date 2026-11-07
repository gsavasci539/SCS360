import { BookOpen, Download, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { downloadFile } from "../../lib/download";
import { shortDate } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import type { ApiResponse, DataRecord } from "../../types/api";

export function MaterialsPage() {
  const [materials, setMaterials] = useState<DataRecord[]>([]);
  const [classes, setClasses] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [title, setTitle] = useState("");
  const [classId, setClassId] = useState("");
  const [type, setType] = useState("PDF");
  const [visibility, setVisibility] = useState("PUBLIC");
  const fileInput = useRef<HTMLInputElement>(null);
  const canWrite = useAuthStore((state) => state.can("material.write"));
  const user = useWorkspaceUser();
  const teacherScope = !user?.is_super_admin && user?.roles.some((role) => role.slug === "teacher") &&
    !user?.roles.some((role) => ["admin", "administrator", "school_admin", "manager", "principal", "org_admin", "branch_manager", "owner"].includes(role.slug));
  const canReadClasses = useAuthStore((state) => state.can("classes.read"));
  const { showToast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<ApiResponse<DataRecord[]>>("/materials");
      setMaterials(res.data.data || []);
    } catch (err) { setError(apiMessage(err)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!canWrite || !canReadClasses) return;
    api.get("/classes", { params: { page: 1, page_size: 100 } }).then((res) => {
      const data = res.data.data;
      setClasses(Array.isArray(data) ? data : data?.items || []);
    }).catch((err) => showToast("Sınıflar yüklenemedi", apiMessage(err), "error"));
  }, [canWrite, canReadClasses, showToast]);

  async function upload(event: React.FormEvent) {
    event.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file || !canWrite) return;
    if (file.size > 10 * 1024 * 1024) {
      showToast("Dosya yüklenemedi", "Dosya boyutu 10 MB sınırını aşıyor.", "error");
      return;
    }
    setBusy("upload");
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post("/materials/upload", form, { params: {
        title: title.trim(), material_type: type, visibility, ...(classId ? { class_id: classId } : {}),
      } });
      setTitle("");
      if (fileInput.current) fileInput.current.value = "";
      showToast("Materyal yüklendi");
      await load();
    } catch (err) { showToast("Materyal yüklenemedi", apiMessage(err), "error"); }
    finally { setBusy(""); }
  }

  async function download(material: DataRecord) {
    setBusy(String(material.id));
    try {
      await downloadFile(`/materials/${material.id}/file`, String(material.file_name || material.title || "materyal"));
    } catch (err) { showToast("Materyal indirilemedi", apiMessage(err), "error"); }
    finally { setBusy(""); }
  }

  async function remove(material: DataRecord) {
    if (!window.confirm("“" + String(material.title) + "” materyali kaldırılsın mı?")) return;
    setBusy(String(material.id));
    try {
      await api.delete(`/materials/${material.id}`);
      showToast("Materyal kaldırıldı");
      await load();
    } catch (err) { showToast("Materyal kaldırılamadı", apiMessage(err), "error"); }
    finally { setBusy(""); }
  }

  return <>
    <PageHeader eyebrow="Akademik" title="Ders Materyalleri" description="Ders notları, kaynaklar ve dijital kütüphane" />
    {canWrite && <form className="card card-pad" onSubmit={upload} style={{ marginTop: 18 }}>
      <h2>Materyal yükle</h2>
      <div className="toolbar" style={{ flexWrap: "wrap", marginTop: 12 }}>
        <input className="filter-select" aria-label="Materyal başlığı" placeholder="Materyal başlığı" required maxLength={255} value={title} onChange={(event) => setTitle(event.target.value)} />
        <select className="filter-select" aria-label="Materyal türü" value={type} onChange={(event) => setType(event.target.value)}>
          {Object.entries({ PDF: "PDF", DOCUMENT: "Belge", IMAGE: "Görsel", VIDEO: "Video", AUDIO: "Ses", PRESENTATION: "Sunum", OTHER: "Arşiv" }).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select className="filter-select" aria-label="Materyal görünürlüğü" value={visibility} onChange={(event) => setVisibility(event.target.value)}>
          <option value="PUBLIC">Kurumdaki tüm veliler</option>
          <option value="CLASS_ONLY">Yalnız seçili sınıf</option>
          <option value="TEACHER_ONLY">Yalnız öğretmen ve yönetim</option>
        </select>
        <select className="filter-select" aria-label="Materyal sınıfı" value={classId} required={visibility === "CLASS_ONLY"} onChange={(event) => setClassId(event.target.value)}>
          <option value="">Sınıf seçin</option>
          {classes.map((item) => <option key={item.id} value={item.id}>{String(item.name)}</option>)}
        </select>
        <input ref={fileInput} aria-label="Materyal dosyası" type="file" required className="filter-select" />
        <button className="btn btn-primary" type="submit" disabled={Boolean(busy)}><Upload size={16} />{busy === "upload" ? "Yükleniyor…" : "Yükle"}</button>
      </div>
    </form>}
    <div className="card" style={{ marginTop: 18 }}>
      <div className="card-head"><h2>Materyaller</h2><span className="badge badge-green">{materials.length}</span></div>
      <div className="card-pad">
        {loading ? <LoadingState label="Yükleniyor" /> : error ? <ErrorState message={error} retry={load} /> : materials.length === 0 ? <p>Henüz materyal yüklenmedi</p> : <div className="table-wrap"><table className="data-table">
          <thead><tr><th>Başlık</th><th>Sınıf / konu</th><th>Tür</th><th>Yükleme tarihi</th><th>İşlem</th></tr></thead>
          <tbody>{materials.map((material) => <tr key={material.id}>
            <td><BookOpen size={14} /> {String(material.title)}</td>
            <td>{String(material.class_name || material.unit_topic || "Kurum geneli")}</td>
            <td><Badge value={String(material.material_type)} /></td>
            <td>{shortDate(material.created_at)}</td>
            <td><div className="table-actions">
              <button className="btn btn-ghost btn-icon" disabled={Boolean(busy)} onClick={() => download(material)} aria-label={String(material.title) + " indir"}><Download size={16} /></button>
              {canWrite && (!teacherScope || material.teacher_id === user?.id || material.created_by === user?.id) && <button className="btn btn-ghost btn-icon" disabled={Boolean(busy)} onClick={() => remove(material)} aria-label={String(material.title) + " kaldır"}><Trash2 size={16} /></button>}
            </div></td>
          </tr>)}</tbody>
        </table></div>}
      </div>
    </div>
  </>;
}

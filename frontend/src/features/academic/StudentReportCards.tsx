import { useEffect, useState } from "react";
import { EmptyState, ErrorState, Field, LoadingState, Modal } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ReportCardRows({ cards }: { cards: DataRecord[] }) {
  return <>{cards.map((card) => <article key={card.id} className="card" style={{ padding: 16, marginTop: 12 }}>
    <h3>{String(card.academic_year)} · {card.semester === "FALL" ? "Güz" : card.semester === "SPRING" ? "Bahar" : "Yaz"}</h3>
    <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 140px), 1fr))", gap: 12 }}>
      <div><dt>Not ortalaması</dt><dd>{typeof card.gpa === "number" ? `${card.gpa.toFixed(2)} / 4` : "Veri yok"}</dd></div>
      <div><dt>Sınıf sırası</dt><dd>{card.class_rank != null ? `${card.class_rank} / ${card.total_students}` : "Hesaplanmadı"}</dd></div>
      <div><dt>Kayıtlı devam oranı</dt><dd>{typeof card.attendance_rate === "number" ? `%${card.attendance_rate}` : "Veri yok veya erişim kapalı"}</dd></div>
    </dl>
    {card.teacher_comments && <p>Öğretmen: {String(card.teacher_comments)}</p>}
    {card.principal_comments && <p>Yönetim: {String(card.principal_comments)}</p>}
    {card.generated_at && <p>Oluşturulma: {new Date(String(card.generated_at)).toLocaleString("tr-TR")}</p>}
  </article>)}</>;
}

export function StudentReportCards({ student, writable, onClose }: {
  student: { id: string; name: string }; writable: boolean; onClose: () => void;
}) {
  const today = new Date(), month = today.getMonth() + 1, firstYear = today.getFullYear() - (month < 9 ? 1 : 0);
  const [year, setYear] = useState(`${firstYear}-${firstYear + 1}`);
  const [semester, setSemester] = useState(month >= 9 || month <= 1 ? "FALL" : month <= 6 ? "SPRING" : "SUMMER");
  const [teacherComments, setTeacherComments] = useState(""), [principalComments, setPrincipalComments] = useState("");
  const [cards, setCards] = useState<DataRecord[]>([]), [loading, setLoading] = useState(true), [revision, setRevision] = useState(0);
  const [error, setError] = useState(""), [message, setMessage] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get<ApiResponse<DataRecord[]>>(`/exams/report-cards/${student.id}`, { signal: controller.signal })
      .then((reply) => { if (!controller.signal.aborted) setCards(reply.data.data); })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [student.id, revision]);
  async function generate(event: React.FormEvent) {
    event.preventDefault(); if (busy) return; setBusy(true); setError(""); setMessage("");
    try {
      await api.post("/exams/report-cards/generate", { student_id: student.id, academic_year: year, semester,
        teacher_comments: teacherComments.trim() || null, principal_comments: principalComments.trim() || null });
      setMessage("Karne taslağı oluşturuldu. Veliye açmak için yayımlayın."); setRevision((value) => value + 1);
    } catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  async function publish(card: DataRecord) {
    if (busy) return; setBusy(true); setError(""); setMessage("");
    try { await api.put(`/exams/report-cards/${card.id}/publish`); setMessage("Karne veliye yayımlandı."); setRevision((value) => value + 1); }
    catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <Modal open title={`${student.name} · Karneler`} onClose={() => { if (!busy) onClose(); }}>
    <p>Güz: Eylül–Ocak, bahar: Şubat–Haziran, yaz: Temmuz–Ağustos. Yalnız bu dönemin geçerli notları eşit ağırlıkla, tam puana göre hesaplanır.</p>
    <p>Karne oluşturulduğu andaki kayıtların özetidir. Notlar değişirse karneyi yeniden oluşturup yayımlayın.</p>
    <p>Devam oranı kayıtlı günler içindir: mevcut ve geç bir gün, yarım gün 0,5, devamsız ve mazeretli sıfır gün sayılır. Kayıtsız günler oranı etkilemez.</p>
    {message && <p role="status">{message}</p>}
    {error && <div role="alert"><ErrorState message={error} retry={() => setRevision((value) => value + 1)} /></div>}
    {writable && <form onSubmit={generate}>
      <fieldset disabled={busy} style={{ border: 0, padding: 0, minWidth: 0 }}>
        <div className="form-grid">
          <Field label="Akademik yıl" required><input value={year} onChange={(event) => setYear(event.target.value)} required pattern="[0-9]{4}-[0-9]{4}" placeholder="2026-2027" /></Field>
          <Field label="Dönem"><select value={semester} onChange={(event) => setSemester(event.target.value)}>
            <option value="FALL">Güz</option><option value="SPRING">Bahar</option><option value="SUMMER">Yaz</option>
          </select></Field>
          <Field label="Öğretmen yorumu"><textarea value={teacherComments} onChange={(event) => setTeacherComments(event.target.value)} maxLength={2000} /></Field>
          <Field label="Yönetim yorumu"><textarea value={principalComments} onChange={(event) => setPrincipalComments(event.target.value)} maxLength={2000} /></Field>
        </div>
        <button className="btn btn-primary" type="submit">{busy ? "İşleniyor…" : "Karne taslağı oluştur"}</button>
      </fieldset>
    </form>}
    {loading ? <LoadingState label="Karneler yükleniyor" /> : !error && cards.length === 0 ? <EmptyState title="Bu öğrencinin karnesi yok" /> :
      cards.map((card) => <div key={card.id}><ReportCardRows cards={[card]} /><p>{card.is_published ? "Veliye yayımlandı" : "Taslak"}</p>
        {writable && !card.is_published && <button className="btn btn-secondary" disabled={busy} onClick={() => publish(card)}>Veliye yayımla</button>}
      </div>)}
  </Modal>;
}

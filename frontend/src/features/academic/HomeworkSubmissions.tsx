import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

interface Submission {
  id: string; student_id: string; student_name: string; status: string;
  submission_text?: string; score?: number; teacher_feedback?: string;
  attachment_file_name?: string; attachment_url?: string;
}

export function HomeworkSubmissions({ homeworkId, studentId, canGrade = false }: {
  homeworkId: string; studentId?: string; canGrade?: boolean;
}) {
  const [rows, setRows] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [text, setText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const sequence = useRef(0);
  const draftEdited = useRef(false);
  const load = useCallback(async (signal?: AbortSignal) => {
    const request = ++sequence.current;
    setError("");
    try {
      const response = await api.get<ApiResponse<Submission[]>>("/homework/submissions", { params: { homework_id: homeworkId }, signal });
      if (signal?.aborted || request !== sequence.current) return;
      const submissions = response.data.data.filter((row) => !studentId || row.student_id === studentId);
      setRows(submissions);
      if (studentId && !draftEdited.current) setText(submissions[0]?.submission_text || "");
    } catch (reason) { if (!signal?.aborted && request === sequence.current) setError(apiMessage(reason)); }
    finally { if (!signal?.aborted && request === sequence.current) setLoading(false); }
  }, [homeworkId, studentId]);
  useEffect(() => {
    const controller = new AbortController();
    draftEdited.current = false;
    setText(""); setRows([]); setMessage(""); setLoading(true);
    void load(controller.signal);
    return () => { controller.abort(); sequence.current++; };
  }, [load]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!studentId || busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const file = fileInput.current?.files?.[0];
      if (file) {
        const form = new FormData();
        form.append("student_id", studentId); form.append("submission_text", text); form.append("file", file);
        await api.post(`/homework/${homeworkId}/submit-file`, form);
      } else {
        await api.post(`/homework/${homeworkId}/submit`, { student_id: studentId, submission_text: text });
      }
      if (fileInput.current) fileInput.current.value = "";
      draftEdited.current = false;
      await load(); setMessage("Ödev teslimi kaydedildi.");
    } catch (reason) { setError(apiMessage(reason)); }
    finally { setBusy(false); }
  }
  async function download(row: Submission) {
    try {
      const result = await api.get(row.attachment_url!, { responseType: "blob" });
      const url = URL.createObjectURL(result.data);
      const link = document.createElement("a");
      link.href = url; link.download = row.attachment_file_name || "odev"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) { setError(apiMessage(reason)); }
  }
  if (loading) return <p>Ödev teslimleri yükleniyor…</p>;
  return <section aria-label="Ödev teslimi" style={{ marginTop: 16 }}>
    {error && <p role="alert">{error} <button type="button" className="btn btn-secondary" onClick={() => void load()}>Yeniden dene</button></p>}
    {message && <p role="status">{message}</p>}
    {rows.map((row) => <div key={row.id} style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8, marginBottom: 12 }}>
      {!studentId && <strong>{row.student_name}</strong>}
      <p>{row.status === "GRADED" ? `Puan: ${row.score} / 100` : "Teslim alındı"}</p>
      {row.submission_text && <p>{row.submission_text}</p>}
      {row.teacher_feedback && <p>Öğretmen geri bildirimi: {row.teacher_feedback}</p>}
      {row.attachment_url && <button type="button" className="btn btn-secondary" onClick={() => download(row)}>Dosyayı indir: {row.attachment_file_name}</button>}
      {canGrade && <GradeSubmission row={row} onSave={load} />}
    </div>)}
    {studentId && rows[0]?.status !== "GRADED" && <form onSubmit={submit} style={{ display: "grid", gap: 10 }}>
      <label>Teslim metni<textarea className="input" aria-label="Teslim metni" maxLength={10000} value={text} disabled={busy} onChange={(event) => { draftEdited.current = true; setText(event.target.value); }} /></label>
      <label>Ödev dosyası<input ref={fileInput} type="file" aria-label="Ödev dosyası" accept=".pdf,.jpg,.jpeg,.png,.docx" disabled={busy} /></label>
      <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Kaydediliyor…" : "Ödevi teslim et"}</button>
    </form>}
    {!studentId && !rows.length && <p>Henüz teslim yok.</p>}
  </section>;
}

function GradeSubmission({ row, onSave }: { row: Submission; onSave: () => Promise<void> }) {
  const [score, setScore] = useState(String(row.score ?? ""));
  const [feedback, setFeedback] = useState(row.teacher_feedback || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function grade(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await api.put(`/homework/submissions/${row.id}/grade`, { score: Number(score), teacher_feedback: feedback });
      await onSave();
    } catch (reason) { setError(apiMessage(reason)); }
    finally { setBusy(false); }
  }
  return <form onSubmit={grade} style={{ display: "grid", gap: 8, marginTop: 12 }}>
    <label>Puan<input className="input" type="number" min={0} max={100} step="any" required value={score} onChange={(event) => setScore(event.target.value)} /></label>
    <label>Geri bildirim<textarea className="input" value={feedback} onChange={(event) => setFeedback(event.target.value)} /></label>
    <button className="btn btn-secondary" type="submit" disabled={busy}>{busy ? "Kaydediliyor…" : "Notu kaydet"}</button>
    {error && <p role="alert">{error}</p>}
  </form>;
}

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

interface Submission {
  id: string; student_id: string; student_name: string; status: string;
  submission_text?: string; score?: number; teacher_feedback?: string;
  attachment_file_name?: string; attachment_url?: string;
}

type SubmissionReceipt = Pick<Submission, "id" | "status">;

function attachmentPath(id: string) {
  return `/homework/submissions/${encodeURIComponent(id)}/attachment`;
}

async function confirmSubmission(homeworkId: string, studentId: string, receipt: SubmissionReceipt | undefined, status: string, signal: AbortSignal) {
  if (!receipt?.id || receipt.status !== status) throw new Error("Sunucu teslim kaydını doğrulamadı.");
  const response = await api.get<ApiResponse<Submission[]>>("/homework/submissions", {
    params: { homework_id: homeworkId, student_id: studentId, record_id: receipt.id, limit: 1 }, signal,
  });
  const row = response.data.data[0];
  if (row?.id !== receipt.id || row.status !== status) throw new Error("Teslim kaydı yeniden okunamadı.");
  return row;
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
  const [scopeSignal, setScopeSignal] = useState<AbortSignal>();
  const load = useCallback(async (signal?: AbortSignal) => {
    const request = ++sequence.current;
    setError("");
    try {
      const response = await api.get<ApiResponse<Submission[]>>("/homework/submissions", {
        params: { homework_id: homeworkId, ...(studentId ? { student_id: studentId } : {}) }, signal,
      });
      if (signal?.aborted || request !== sequence.current) return;
      const submissions = response.data.data.filter((row) => !studentId || row.student_id === studentId);
      setRows(submissions);
      if (studentId && !draftEdited.current) setText(submissions[0]?.submission_text || "");
    } catch (reason) { if (!signal?.aborted && request === sequence.current) setError(apiMessage(reason)); }
    finally { if (!signal?.aborted && request === sequence.current) setLoading(false); }
  }, [homeworkId, studentId]);
  useEffect(() => {
    const controller = new AbortController();
    setScopeSignal(controller.signal);
    draftEdited.current = false;
    setText(""); setRows([]); setMessage(""); setLoading(true); setBusy(false);
    void load(controller.signal);
    return () => { controller.abort(); sequence.current++; };
  }, [load]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const signal = scopeSignal;
    if (!studentId || !signal || busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const file = fileInput.current?.files?.[0];
      const trimmed = text.trim();
      let receipt: SubmissionReceipt;
      if (file) {
        const form = new FormData();
        form.append("student_id", studentId); form.append("submission_text", trimmed); form.append("file", file);
        receipt = (await api.post<ApiResponse<SubmissionReceipt>>(`/homework/${homeworkId}/submit-file`, form, { signal })).data.data;
      } else {
        receipt = (await api.post<ApiResponse<SubmissionReceipt>>(`/homework/${homeworkId}/submit`,
          { student_id: studentId, homework_id: homeworkId, submission_text: trimmed }, { signal })).data.data;
      }
      if (signal.aborted) return;
      const stored = await confirmSubmission(homeworkId, studentId, receipt, "SUBMITTED", signal);
      if (signal.aborted) return;
      if (stored.student_id !== studentId || (stored.submission_text ?? "") !== trimmed ||
          (file && (stored.attachment_file_name !== file.name || stored.attachment_url !== attachmentPath(stored.id)))) {
        throw new Error("Teslim içeriği sunucudan doğrulanamadı.");
      }
      if (fileInput.current) fileInput.current.value = "";
      draftEdited.current = false;
      setRows([stored]);
      setMessage("Ödev teslimi kaydedildi.");
    } catch (reason) { if (!signal.aborted) setError(apiMessage(reason)); }
    finally { if (!signal.aborted) setBusy(false); }
  }
  async function download(row: Submission) {
    const signal = scopeSignal;
    try {
      const result = await api.get(attachmentPath(row.id), { responseType: "blob", signal });
      if (signal?.aborted) return;
      const url = URL.createObjectURL(result.data);
      const link = document.createElement("a");
      link.href = url; link.download = row.attachment_file_name || "odev"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) { if (!signal?.aborted) setError(apiMessage(reason)); }
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
      {row.attachment_url === attachmentPath(row.id) && <button type="button" className="btn btn-secondary" onClick={() => download(row)}>Dosyayı indir: {row.attachment_file_name}</button>}
      {canGrade && <GradeSubmission row={row} homeworkId={homeworkId} signal={scopeSignal}
        onSave={(stored) => setRows((previous) => previous.map((item) => item.id === stored.id ? stored : item))} />}
    </div>)}
    {studentId && rows[0]?.status !== "GRADED" && <form onSubmit={submit} style={{ display: "grid", gap: 10 }}>
      <label>Teslim metni<textarea className="input" aria-label="Teslim metni" maxLength={10000} value={text} disabled={busy} onChange={(event) => { draftEdited.current = true; setText(event.target.value); }} /></label>
      <label>Ödev dosyası<input ref={fileInput} type="file" aria-label="Ödev dosyası" accept=".pdf,.jpg,.jpeg,.png,.docx" disabled={busy} /></label>
      <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Kaydediliyor…" : "Ödevi teslim et"}</button>
    </form>}
    {!studentId && !rows.length && <p>Henüz teslim yok.</p>}
  </section>;
}

function GradeSubmission({ row, homeworkId, signal, onSave }: {
  row: Submission; homeworkId: string; signal?: AbortSignal; onSave: (stored: Submission) => void;
}) {
  const [score, setScore] = useState(String(row.score ?? ""));
  const [feedback, setFeedback] = useState(row.teacher_feedback || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function grade(event: FormEvent) {
    event.preventDefault();
    if (!signal || busy) return;
    setBusy(true); setError("");
    try {
      const points = Number(score);
      const remarks = feedback.trim();
      const response = await api.put<ApiResponse<SubmissionReceipt>>(`/homework/submissions/${row.id}/grade`,
        { score: points, teacher_feedback: remarks }, { signal });
      if (signal.aborted) return;
      if (response.data.data.id !== row.id) throw new Error("Sunucu farklı bir teslim kaydı döndürdü.");
      const stored = await confirmSubmission(homeworkId, row.student_id, response.data.data, "GRADED", signal);
      if (signal.aborted) return;
      if (stored.student_id !== row.student_id || Number(stored.score) !== points || (stored.teacher_feedback ?? "") !== remarks) {
        throw new Error("Puan ve geri bildirim sunucudan doğrulanamadı.");
      }
      onSave(stored);
    } catch (reason) { if (!signal.aborted) setError(apiMessage(reason)); }
    finally { if (!signal.aborted) setBusy(false); }
  }
  return <form onSubmit={grade} style={{ display: "grid", gap: 8, marginTop: 12 }}>
    <label>Puan<input className="input" type="number" min={0} max={100} step="any" required value={score} onChange={(event) => setScore(event.target.value)} /></label>
    <label>Geri bildirim<textarea className="input" value={feedback} onChange={(event) => setFeedback(event.target.value)} /></label>
    <button className="btn btn-secondary" type="submit" disabled={busy}>{busy ? "Kaydediliyor…" : "Notu kaydet"}</button>
    {error && <p role="alert">{error}</p>}
  </form>;
}

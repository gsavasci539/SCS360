import { useState } from "react";
import { useForm } from "react-hook-form";
import { Field, Modal } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { DataRecord } from "../../types/api";
import { ResourceChoice } from "../resources/ResourceChoice";

type Values = Record<string, string | number | boolean>;
export function ExamEditor({ exam, onClose, onSaved }: { exam: DataRecord | null; onClose: () => void; onSaved: () => void }) {
  const [error, setError] = useState(""), [saving, setSaving] = useState(false);
  const { register, control, handleSubmit } = useForm<Values>({ defaultValues: {
    title: String(exam?.title ?? ""), class_id: String(exam?.class_id ?? ""), exam_type: String(exam?.exam_type ?? "QUIZ"),
    exam_date: String(exam?.exam_date ?? ""), start_time: String(exam?.start_time ?? "").slice(0, 5),
    duration_minutes: Number(exam?.duration_minutes ?? 60), max_score: Number(exam?.max_score ?? 100),
    weight: Number(exam?.weight ?? 1), description: String(exam?.description ?? ""),
  } });
  const locked = Number(exam?.result_count ?? 0) > 0;
  async function save(values: Values) {
    if (saving) return;
    setSaving(true); setError("");
    const payload = { class_id: String(values.class_id), title: String(values.title).trim(),
      exam_type: values.exam_type, exam_date: values.exam_date, start_time: values.start_time || null,
      duration_minutes: Number(values.duration_minutes), max_score: Number(values.max_score), weight: Number(values.weight),
      description: String(values.description).trim() || null, teacher_id: exam?.teacher_id ?? null, subject_id: exam?.subject_id ?? null };
    try {
      if (exam) await api.put(`/exams/${exam.id}`, payload); else await api.post("/exams", payload);
      onSaved();
    } catch (reason) { setError(apiMessage(reason)); }
    finally { setSaving(false); }
  }
  return <Modal open title={exam ? "Sınavı düzenle" : "Yeni sınav"} onClose={() => { if (!saving) onClose(); }}>
    <form onSubmit={handleSubmit(save)}>
      {error && <p role="alert">{error}</p>}
      <fieldset disabled={saving} style={{ border: 0, padding: 0, minWidth: 0 }}>
        <div className="form-grid">
          <Field label="Sınav adı" required><input {...register("title", { required: true })} required maxLength={255} /></Field>
          {locked ? <Field label="Sınıf"><input value={String(exam?.class_name ?? "Sınav sınıfı")} readOnly /></Field> :
            <ResourceChoice field={{ name: "class_id", label: "Sınıf", type: "select", required: true,
              optionSource: exam ? `/exams/class-options?exam_id=${exam.id}` : "/exams/class-options", searchable: true }} control={control} />}
          <Field label="Sınav türü" required><select {...register("exam_type")}>
            <option value="QUIZ">Kısa sınav</option><option value="MIDTERM">Ara sınav</option><option value="FINAL">Dönem sonu</option>
            <option value="MAKEUP">Telafi</option><option value="PROJECT">Proje</option><option value="OTHER">Diğer</option>
          </select></Field>
          <Field label="Sınav tarihi" required><input type="date" {...register("exam_date", { required: true })} required /></Field>
          <Field label="Başlangıç saati"><input type="time" {...register("start_time")} /></Field>
          <Field label="Süre (dakika)" required><input type="number" min={15} max={300} step={1} {...register("duration_minutes")} required /></Field>
          <Field label="Tam puan" required><input type="number" min="0.01" max="999.99" step="0.01" readOnly={locked} {...register("max_score")} required /></Field>
          <Field label="Sınav ağırlığı"><input type="number" min={0} max={2} step="0.01" {...register("weight")} required /></Field>
          <Field label="Açıklama" full><textarea {...register("description")} maxLength={1000} /></Field>
        </div>
        {locked && <p>Not girilmiş sınavın sınıfı ve tam puanı korunur.</p>}
        <div className="head-actions" style={{ marginTop: 18 }}><button type="button" className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
          <button type="submit" className="btn btn-primary">{saving ? "Kaydediliyor…" : "Sınavı kaydet"}</button></div>
      </fieldset>
    </form>
  </Modal>;
}

import { useCallback, useEffect, useRef, useState } from "react";
import { Field, Modal } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, Paginated } from "../../types/api";

type Choice = { id: string; name: string };
type Slot = { start_time: string; end_time: string; duration_minutes: number };
type Draft = {
  request_id: string; student_id: string; teacher_id: string; slot_datetime: string;
  parent_note: string; duration_minutes: number;
};
type Recorded = {
  id: string; student_id: string; teacher_id: string; appointment_date: string; appointment_time: string;
  notes: string | null; duration_minutes: number;
};

async function options(signal: AbortSignal, studentId?: string) {
  const result = new Map<string, Choice>();
  for (let page = 1; ; page++) {
    const { data } = await api.get<ApiResponse<Paginated<Choice>>>("/appointments/options", {
      params: { student_id: studentId, page, page_size: 100 }, signal,
    });
    if (!data.success || data.data.page !== page) throw new Error("Randevu seçenekleri doğrulanamadı.");
    data.data.items.forEach((row) => result.set(row.id, row));
    if (page >= data.data.total_pages) return [...result.values()];
  }
}

export function AppointmentCreateModal({ parent, onClose, onSuccess }: {
  parent: boolean; onClose: () => void; onSuccess: () => void;
}) {
  const { showToast } = useToast();
  const [students, setStudents] = useState<Choice[]>([]);
  const [teachers, setTeachers] = useState<Choice[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [studentId, setStudentId] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [note, setNote] = useState("");
  const [optionsError, setOptionsError] = useState("");
  const [revision, reload] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Draft | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    options(controller.signal).then((list) => { if (!controller.signal.aborted) setStudents(list); })
      .catch((error) => { if (!controller.signal.aborted) setOptionsError(apiMessage(error)); });
    return () => controller.abort();
  }, [revision]);
  useEffect(() => {
    if (!studentId) return;
    const controller = new AbortController();
    options(controller.signal, studentId).then((list) => { if (!controller.signal.aborted) setTeachers(list); })
      .catch((error) => { if (!controller.signal.aborted) setOptionsError(apiMessage(error)); });
    return () => controller.abort();
  }, [studentId, revision]);
  useEffect(() => {
    if (!parent || !teacherId || !date) return;
    const controller = new AbortController();
    api.get<ApiResponse<Slot[]>>(`/appointments/teacher-slots/${teacherId}`, {
      params: { date }, signal: controller.signal,
    }).then(({ data }) => {
      if (!controller.signal.aborted) setSlots(data.data.filter((row) => row.duration_minutes >= 15 && row.duration_minutes <= 60));
    }).catch((error) => { if (!controller.signal.aborted) setOptionsError(apiMessage(error)); });
    return () => controller.abort();
  }, [parent, teacherId, date, revision]);

  const close = useCallback(() => { if (!request.current) onClose(); }, [onClose]);
  const selectedSlot = slots.find((row) => row.start_time === time);
  const valid = students.some((row) => row.id === studentId) && teachers.some((row) => row.id === teacherId) &&
    !!date && !!time && (!parent || !!selectedSlot) && !optionsError;
  const locked = busy || !!pending;

  async function submit() {
    if (request.current || (!pending && !valid)) return;
    const draft = pending ?? {
      request_id: crypto.randomUUID(), student_id: studentId, teacher_id: teacherId,
      slot_datetime: `${date}T${time}`, parent_note: note, duration_minutes: selectedSlot?.duration_minutes ?? 30,
    };
    const controller = new AbortController();
    request.current = controller;
    const config = { signal: controller.signal };
    setBusy(true);
    setError("");
    let received = false;
    try {
      if (!pending) {
        const { data } = await api.post<ApiResponse<{ id: string }>>(
          parent ? "/appointments/request" : "/appointments", draft, config,
        );
        received = true;
        if (!data.success || data.data.id !== draft.request_id) throw new Error("Randevu doğrulanamadı.");
      }
      const { data } = await api.get<ApiResponse<Recorded>>(`/appointments/${draft.request_id}`, config);
      if (controller.signal.aborted) return;
      const row = data.data;
      if (data.success && row.id === draft.request_id && row.student_id === draft.student_id &&
          row.teacher_id === draft.teacher_id && `${row.appointment_date}T${row.appointment_time}` === draft.slot_datetime &&
          row.duration_minutes === draft.duration_minutes && (row.notes ?? "") === draft.parent_note) {
        showToast("Randevu oluşturuldu", "Kayıt sunucuda doğrulandı.");
        onClose();
        onSuccess();
      } else {
        setPending(draft);
        setError("Kayıt doğrulanamadı. Sonucu tekrar kontrol edebilirsiniz.");
      }
    } catch (failure) {
      if (controller.signal.aborted) return;
      const status = (failure as { response?: { status?: number } })?.response?.status ?? 0;
      if (!pending && !received && [401, 403, 404, 422].includes(status)) setError(apiMessage(failure));
      else {
        setPending(draft);
        setError("Kayıt doğrulanamadı. Sonucu tekrar kontrol edebilirsiniz.");
      }
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <Modal open title="Yeni randevu" onClose={close} actions={<>
    <button className="btn btn-secondary" disabled={busy} onClick={close}>Kapat</button>
    <button className="btn btn-primary" disabled={busy || (!pending && !valid)} onClick={() => void submit()}>
      {pending ? "Sonucu kontrol et" : "Oluştur"}
    </button>
  </>}>
    <div className="form-grid">
      <Field label="Öğrenci" required><select disabled={locked || students.length === 0} value={studentId}
        onChange={(event) => {
          setStudentId(event.target.value); setTeacherId(""); setTeachers([]); setSlots([]); setTime(""); setOptionsError("");
        }}><option value="">Seçin</option>{students.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>
      <Field label="Öğretmen" required><select disabled={locked || teachers.length === 0} value={teacherId}
        onChange={(event) => { setTeacherId(event.target.value); setSlots([]); if (parent) setTime(""); setOptionsError(""); }}>
        <option value="">Seçin</option>{teachers.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>
      <Field label="Tarih" required><input type="date" disabled={locked} value={date}
        onChange={(event) => { setDate(event.target.value); setSlots([]); if (parent) setTime(""); setOptionsError(""); }} /></Field>
      <Field label="Saat" required>{parent
        ? <select disabled={locked || slots.length === 0} value={time} onChange={(event) => setTime(event.target.value)}>
          <option value="">Seçin</option>{slots.map((row) => <option key={row.start_time} value={row.start_time}>
            {row.start_time} – {row.end_time}</option>)}</select>
        : <input type="time" disabled={locked} value={time} onChange={(event) => setTime(event.target.value)} />}</Field>
      <Field label="Görüşme notu" full><textarea disabled={locked} value={note} onChange={(event) => setNote(event.target.value)} /></Field>
    </div>
    {optionsError && <p role="alert">{optionsError} <button className="btn btn-ghost" disabled={locked}
      onClick={() => { setOptionsError(""); reload((value) => value + 1); }}>Seçenekleri yenile</button></p>}
    {error && <p role="alert">{error}</p>}
  </Modal>;
}

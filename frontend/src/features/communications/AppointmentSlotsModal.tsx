import { useCallback, useEffect, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { Field, Modal } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

type Slot = {
  id: string; teacher_id: string; date: string; start_time: string; end_time: string; is_available: boolean;
};
type Edit = { submit: (signal: AbortSignal) => Promise<unknown>; confirmed: (rows: Slot[]) => boolean };
const schoolDate = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Istanbul" }).format(new Date());
const minutes = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));

export function AppointmentSlotsModal({ teacherId, onClose }: { teacherId: string; onClose: () => void }) {
  const [day, setDay] = useState(schoolDate);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Edit | null>(null);
  const [candidate, setCandidate] = useState<Slot | null>(null);
  const active = useRef<AbortController | null>(null);
  const close = useCallback(() => { if (!active.current) onClose(); }, [onClose]);
  const editable = !busy && !pending;
  const duration = minutes(end) - minutes(start);

  const refresh = useCallback(async (date: string, edit?: Edit, submit = true) => {
    if (!date || active.current) return;
    const control = new AbortController();
    active.current = control;
    const { signal } = control;
    setBusy(true);
    setError("");
    let received = false;
    try {
      if (edit && submit) {
        await edit.submit(signal);
        received = true;
      }
      const { data } = await api.get<ApiResponse<Slot[]>>("/appointments/slots", { signal, params: { date } });
      if (signal.aborted) return;
      if (!data.success || data.data.some((row) => row.teacher_id !== teacherId || row.date !== date)) {
        throw new Error("Uygunluk listesi doğrulanamadı.");
      }
      setSlots(data.data);
      if (edit && !edit.confirmed(data.data)) {
        setPending(edit);
        setError("Değişiklik listede doğrulanamadı.");
      } else if (edit) {
        setPending(null);
        setStart("");
        setEnd("");
      }
    } catch (e) {
      if (signal.aborted) return;
      setError(apiMessage(e));
      const rejected = submit && !received && isAxiosError(e) && [401, 403, 409, 422].includes(e.response?.status ?? 0);
      if (edit && !rejected) setPending(edit);
    } finally {
      if (active.current === control) {
        active.current = null;
        setBusy(false);
      }
    }
  }, [teacherId]);

  useEffect(() => {
    void refresh(schoolDate());
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [refresh]);

  return (
    <Modal open title="Uygunluk saatlerim" onClose={close}>
      <form onSubmit={(event) => {
        event.preventDefault();
        if (!editable || !start || !end || duration < 15 || duration > 60) return;
        void refresh(day, {
          submit: (signal) => api.post("/appointments/slots", {
            teacher_id: teacherId, date: day, start_time: start, end_time: end, is_available: true,
          }, { signal }),
          confirmed: (rows) => rows.some((row) => row.start_time === start && row.end_time === end && row.is_available),
        });
      }}>
        <Field label="Tarih">
          <input type="date" value={day} disabled={!editable} required onChange={(event) => {
            setDay(event.target.value); setSlots(null); setError(""); setCandidate(null);
          }} />
        </Field>
        <button type="button" className="btn btn-secondary" disabled={!editable || !day} onClick={() => void refresh(day)}>
          Saatleri getir
        </button>
        {busy && <p role="status">Yükleniyor…</p>}
        {error && <p role="alert">{error}</p>}
        {slots?.length === 0 && <p>Bu tarihte kayıtlı saat yok.</p>}
        {slots?.map((slot) => <div key={slot.id}>
          <span>{slot.start_time} – {slot.end_time}{!slot.is_available && " · Kapalı"}</span>{" "}
          <button type="button" className="btn btn-secondary" disabled={!editable} onClick={() => setCandidate(slot)}>
            Saati sil
          </button>
        </div>)}
        {candidate && <div role="group" aria-label="Saat silme onayı">
          <p>{candidate.start_time} – {candidate.end_time} silinsin mi?</p>
          <button type="button" className="btn btn-secondary" onClick={() => setCandidate(null)}>Vazgeç</button>{" "}
          <button type="button" className="btn btn-danger" disabled={!editable} onClick={() => {
            const { id } = candidate;
            setCandidate(null);
            void refresh(day, {
              submit: (signal) => api.delete(`/appointments/slots/${id}`, { signal }),
              confirmed: (rows) => rows.every((row) => row.id !== id),
            });
          }}>Sil</button>
        </div>}
        <Field label="Başlangıç"><input type="time" value={start} disabled={!editable} required onChange={(event) => setStart(event.target.value)} /></Field>
        <Field label="Bitiş (15–60 dakika)"><input type="time" value={end} disabled={!editable} required onChange={(event) => setEnd(event.target.value)} /></Field>
        <button type="submit" className="btn btn-primary" disabled={!editable || !day || !start || !end || duration < 15 || duration > 60}>Saat ekle</button>
        {pending && <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void refresh(day, pending, false)}>Sonucu kontrol et</button>}
      </form>
    </Modal>
  );
}

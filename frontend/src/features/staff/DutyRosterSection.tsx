import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorState, Field, LoadingState, Modal } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse, Paginated } from "../../types/api";

const route = "/staff/duty-rosters";
const days: Record<string, string> = {
  MONDAY: "Pazartesi", TUESDAY: "Salı", WEDNESDAY: "Çarşamba", THURSDAY: "Perşembe",
  FRIDAY: "Cuma", SATURDAY: "Cumartesi", SUNDAY: "Pazar",
};
const locations: Record<string, string> = {
  GARDEN: "Bahçe & Giriş Kapısı", FLOOR_1: "1. Kat İlkokul Koridoru", FLOOR_2: "2. Kat Ortaokul Koridoru",
  CAFETERIA: "Yemekhane", CANTEEN: "Kantin Çevresi", KINDERGARTEN: "Anaokulu Oyun Alanı",
};
type Option = { id: string; name: string };
type DutyFields = {
  branch_id: string; teacher_id: string; day_of_week: string; duty_location: string; start_time: string; end_time: string;
};
type Duty = DutyFields & { id: string; teacher_name: string; status: string };
type Attempt = DutyFields & { request_id: string; teacher_name: string };
const empty: DutyFields = { branch_id: "", teacher_id: "", day_of_week: "", duty_location: "", start_time: "", end_time: "" };

async function listOptions(signal: AbortSignal, branchId?: string): Promise<Option[]> {
  const choices = new Map<string, Option>();
  let page = 1, totalPages: number;
  do {
    const result = await api.get<ApiResponse<Paginated<Option>>>(route + "/options", {
      params: { page, page_size: 100, branch_id: branchId }, signal,
    });
    const data = result.data.data;
    if (data.page !== page) throw new Error("Nöbet seçenekleri doğrulanamadı.");
    data.items.forEach((option) => choices.set(option.id, option));
    totalPages = data.total_pages;
    page++;
  } while (page <= totalPages);
  return [...choices.values()];
}

function matches(row: Duty, attempt: Attempt) {
  return row.id === attempt.request_id && row.status === "ACTIVE" &&
    (Object.keys(empty) as (keyof DutyFields)[]).every((key) => row[key] === attempt[key]);
}

export function DutyRosterSection() {
  const user = useAuthStore((s) => s.user);
  const session = useAuthStore((s) => s.sessionVersion);
  const workspace = usePlatformWorkspace((s) => s.workspace?.id);
  const canWrite = useAuthStore((s) => s.can("user.write"));
  return <ScopedRoster key={JSON.stringify([session, user?.id, user?.organization_id, workspace, user?.branch_ids, canWrite])} canWrite={canWrite} />;
}

function ScopedRoster({ canWrite }: { canWrite: boolean }) {
  const [rows, setRows] = useState<Duty[] | null>(null);
  const [listError, setListError] = useState("");
  const [listRevision, refresh] = useState(0);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setListError("");
    api.get<ApiResponse<Duty[]>>(route, { signal: controller.signal }).then((result) => {
      if (!controller.signal.aborted) setRows(result.data.data);
    }).catch((error) => { if (!controller.signal.aborted) setListError(apiMessage(error)); });
    return () => controller.abort();
  }, [listRevision]);
  return <section className="card" style={{ marginBlock: 18 }}>
    <div className="card-head">
      <h2>Nöbet çizelgesi</h2>
      {canWrite && <button className="btn btn-primary" disabled={!rows || !!listError} onClick={() => setOpen(true)}>Nöbet oluştur</button>}
    </div>
    {listError ? <ErrorState message={listError} retry={() => refresh((value) => value + 1)} /> :
      !rows ? <LoadingState /> :
      rows.length === 0 ? <p className="card-pad">Kayıtlı nöbet yok.</p> :
      <div className="table-wrap"><table className="data-table">
        <thead><tr><th>Öğretmen</th><th>Gün</th><th>Nöbet yeri</th><th>Saat</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id}><td>{row.teacher_name}</td>
          <td>{days[row.day_of_week] ?? row.day_of_week}</td>
          <td>{locations[row.duty_location] ?? row.duty_location}</td>
          <td>{row.start_time} – {row.end_time}</td></tr>)}</tbody>
      </table></div>}
    {open && canWrite && <DutyModal onClose={() => setOpen(false)} onSaved={(confirmed) => {
      setRows(confirmed); setListError(""); setOpen(false);
    }} />}
  </section>;
}

function DutyModal({ onClose, onSaved }: { onClose: () => void; onSaved: (rows: Duty[]) => void }) {
  const [form, setForm] = useState(empty);
  const [branches, setBranches] = useState<Option[]>([]);
  const [teachers, setTeachers] = useState<Option[]>([]);
  const [optionsError, setOptionsError] = useState("");
  const [revision, reload] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState<Attempt | null>(null);
  const operation = useRef<AbortController | null>(null);
  useEffect(() => () => operation.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    listOptions(controller.signal).then((options) => {
      if (!controller.signal.aborted) setBranches(options);
    }).catch((failure) => { if (!controller.signal.aborted) setOptionsError(apiMessage(failure)); });
    return () => controller.abort();
  }, [revision]);
  useEffect(() => {
    if (!form.branch_id) return;
    const controller = new AbortController();
    listOptions(controller.signal, form.branch_id).then((options) => {
      if (!controller.signal.aborted) setTeachers(options);
    }).catch((failure) => { if (!controller.signal.aborted) setOptionsError(apiMessage(failure)); });
    return () => controller.abort();
  }, [form.branch_id, revision]);
  const selectedTeacher = teachers.find((option) => option.id === form.teacher_id);
  const valid = branches.some((option) => option.id === form.branch_id) && selectedTeacher &&
    form.day_of_week in days && form.duty_location in locations &&
    form.start_time !== "" && form.end_time !== "" && form.start_time < form.end_time;
  const close = useCallback(() => { if (!operation.current) onClose(); }, [onClose]);
  const change = (field: keyof DutyFields, value: string) => setForm((current) => ({ ...current, [field]: value }));

  async function submit() {
    if (operation.current || (!uncertain && (!valid || optionsError))) return;
    const attempt = uncertain ?? { ...form, teacher_name: selectedTeacher!.name, request_id: crypto.randomUUID() };
    const controller = new AbortController();
    operation.current = controller;
    setBusy(true);
    setError("");
    try {
      if (!uncertain) {
        const ack = await api.post<ApiResponse<Duty>>(route, attempt, { signal: controller.signal });
        if (!ack.data.success || !matches(ack.data.data, attempt)) throw new Error("Nöbet kaydı doğrulanamadı.");
      }
      const result = await api.get<ApiResponse<Duty[]>>(route, { signal: controller.signal });
      if (controller.signal.aborted) return;
      if (result.data.data.some((row) => matches(row, attempt))) onSaved(result.data.data);
      else { setUncertain(attempt); setError("Kayıt henüz listede görünmüyor."); }
    } catch (failure) {
      if (!controller.signal.aborted) {
        const status = (failure as { response?: { status?: number } })?.response?.status;
        if (!uncertain && [401, 403, 404, 422].includes(status ?? 0)) setError(apiMessage(failure));
        else { setUncertain(attempt); setError("Kayıt doğrulanamadı. Sonucu tekrar kontrol edebilirsiniz."); }
      }
    } finally {
      operation.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const locked = busy || uncertain !== null;
  return <Modal open title="Nöbet oluştur" onClose={close} actions={<>
    <button className="btn btn-secondary" disabled={busy} onClick={close}>Kapat</button>
    <button className="btn btn-primary" disabled={busy || (!uncertain && (!valid || !!optionsError))}
      onClick={() => void submit()}>{uncertain ? "Sonucu kontrol et" : "Kaydet"}</button>
  </>}>
    <div className="form-grid">
      <Field label="Şube" required><select disabled={locked} value={form.branch_id} onChange={(event) => {
        setTeachers([]); setOptionsError("");
        setForm({ ...form, branch_id: event.target.value, teacher_id: "" });
      }}><option value="">Seçin</option>{branches.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></Field>
      <Field label="Öğretmen" required><select disabled={locked || !teachers.length} value={form.teacher_id}
        onChange={(event) => change("teacher_id", event.target.value)}><option value="">Seçin</option>
        {teachers.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></Field>
      <Field label="Gün" required><select disabled={locked} value={form.day_of_week} onChange={(event) => change("day_of_week", event.target.value)}>
        <option value="">Seçin</option>{Object.entries(days).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
      <Field label="Nöbet yeri" required><select disabled={locked} value={form.duty_location} onChange={(event) => change("duty_location", event.target.value)}>
        <option value="">Seçin</option>{Object.entries(locations).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
      <Field label="Başlangıç" required><input type="time" disabled={locked} value={form.start_time} onChange={(event) => change("start_time", event.target.value)} /></Field>
      <Field label="Bitiş" required><input type="time" disabled={locked} value={form.end_time} onChange={(event) => change("end_time", event.target.value)} /></Field>
    </div>
    {optionsError && <ErrorState message={optionsError} retry={() => { setOptionsError(""); reload((value) => value + 1); }} />}
    {error && <p role="alert">{error}</p>}
  </Modal>;
}

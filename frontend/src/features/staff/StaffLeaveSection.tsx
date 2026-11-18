import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorState, Field, LoadingState, Modal } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse, AuthUser } from "../../types/api";

const route = "/staff/leave-requests";
const leaveTypes = ["Mazeret İzni", "Sevk / Sağlık", "İdari İzin", "Yıllık İzin"];
const statuses = { PENDING: "Bekliyor", APPROVED: "Onaylandı", REJECTED: "Reddedildi" };
type Decision = "APPROVED" | "REJECTED";
type LeaveInput = { leave_type: string; start_date: string; end_date: string; reason: string };
type Leave = LeaveInput & {
  id: string; staff_id: string; staff_name: string; days_count: number;
  status: keyof typeof statuses; admin_comment: string | null;
};
type Dialog = { kind: "create"; user: AuthUser } | { kind: "review"; row: Leave; status: Decision };
type Attempt = {
  kind: "create"; body: LeaveInput & { staff_id: string; staff_name: string; days_count: number; request_id: string };
} | {
  kind: "review"; id: string; body: { status: Decision; admin_comment: string };
};

async function loadLeaves(signal: AbortSignal) {
  const response = await api.get<ApiResponse<Leave[]>>(route, { signal });
  if (!response.data.success || !Array.isArray(response.data.data)) throw new Error("İzin listesi doğrulanamadı.");
  return response.data.data;
}

function matches(row: Leave, attempt: Attempt) {
  if (attempt.kind === "review") {
    return row.id === attempt.id && row.status === attempt.body.status &&
      (row.admin_comment ?? "") === attempt.body.admin_comment;
  }
  const body = attempt.body;
  return row.id === body.request_id && row.staff_id === body.staff_id && row.days_count === body.days_count &&
    row.leave_type === body.leave_type && row.reason === body.reason &&
    row.start_date === body.start_date && row.end_date === body.end_date;
}

function daysBetween(start: string, end: string) {
  if (!start || !end || end < start) return 0;
  return (Date.parse(end) - Date.parse(start)) / 86_400_000 + 1;
}

export function StaffLeaveSection() {
  const user = useAuthStore((s) => s.user);
  const session = useAuthStore((s) => s.sessionVersion);
  const workspace = usePlatformWorkspace((s) => s.workspace?.id);
  const canReview = useAuthStore((s) => s.can("user.write"));
  const canRead = useAuthStore((s) => s.can("user.read"));
  if (!canRead) return null;
  const self = user?.organization_id && !user.is_super_admin ? user : null;
  return <ScopedLeaves key={JSON.stringify([session, user?.id, user?.organization_id, workspace, user?.branch_ids, canReview])}
    self={self} canReview={canReview} />;
}

function ScopedLeaves({ self, canReview }: { self: AuthUser | null; canReview: boolean }) {
  const [rows, setRows] = useState<Leave[] | null>(null);
  const [error, setError] = useState("");
  const [revision, refresh] = useState(0);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const close = useCallback(() => setDialog(null), []);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    loadLeaves(controller.signal).then((result) => {
      if (!controller.signal.aborted) setRows(result);
    }).catch((failure) => { if (!controller.signal.aborted) setError(apiMessage(failure)); });
    return () => controller.abort();
  }, [revision]);
  return <section className="card" style={{ marginBlock: 18 }}>
    <div className="card-head">
      <h2>İzin talepleri</h2>
      {self && <button className="btn btn-primary" disabled={!rows || !!error}
        onClick={() => setDialog({ kind: "create", user: self })}>İzin talebi oluştur</button>}
    </div>
    {error ? <ErrorState message={error} retry={() => refresh((n) => n + 1)} /> :
      !rows ? <LoadingState /> :
      rows.length === 0 ? <p className="card-pad">Kayıtlı izin talebi yok.</p> :
      <div className="table-wrap"><table className="data-table">
        <thead><tr><th>Personel</th><th>İzin</th><th>Tarih</th><th>Gerekçe</th><th>Durum</th><th>Değerlendirme notu</th>
          {canReview && <th>İşlemler</th>}</tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id}>
          <td>{row.staff_name}</td><td>{row.leave_type} ({row.days_count} gün)</td><td>{row.start_date} – {row.end_date}</td>
          <td style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{row.reason}</td><td>{statuses[row.status] ?? row.status}</td>
          <td style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{row.admin_comment || "—"}</td>
          {canReview && <td>{row.status === "PENDING" && <div className="table-actions">
            <button className="btn btn-secondary btn-sm" onClick={() => setDialog({ kind: "review", row, status: "APPROVED" })}>Onayla</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setDialog({ kind: "review", row, status: "REJECTED" })}>Reddet</button>
          </div>}</td>}
        </tr>)}</tbody>
      </table></div>}
    {dialog && <LeaveModal dialog={dialog} onClose={close} onSaved={(confirmed) => {
      setRows(confirmed); setError(""); close();
    }} />}
  </section>;
}

function LeaveModal({ dialog, onClose, onSaved }: { dialog: Dialog; onClose: () => void; onSaved: (rows: Leave[]) => void }) {
  const [draft, setDraft] = useState<LeaveInput>({ leave_type: leaveTypes[0], start_date: "", end_date: "", reason: "" });
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState<Attempt | null>(null);
  const operation = useRef<AbortController | null>(null);
  useEffect(() => () => operation.current?.abort(), []);
  const close = useCallback(() => { if (!operation.current) onClose(); }, [onClose]);
  const days = daysBetween(draft.start_date, draft.end_date);
  const valid = dialog.kind === "review" || (Number.isInteger(days) && days > 0 && draft.reason.trim() !== "");
  const locked = busy || uncertain !== null;
  const edit = (field: keyof LeaveInput, value: string) => setDraft((previous) => ({ ...previous, [field]: value }));

  async function submit() {
    if (operation.current || (!valid && !uncertain)) return;
    const attempt: Attempt = uncertain ?? (dialog.kind === "create" ? {
      kind: "create", body: { ...draft, days_count: days, staff_id: dialog.user.id,
        staff_name: [dialog.user.first_name, dialog.user.last_name].join(" "), request_id: crypto.randomUUID() },
    } : { kind: "review", id: dialog.row.id, body: { status: dialog.status, admin_comment: comment } });
    const controller = new AbortController();
    const config = { signal: controller.signal };
    operation.current = controller;
    setBusy(true);
    setError("");
    let received = false;
    try {
      if (!uncertain) {
        const response = attempt.kind === "create"
          ? await api.post<ApiResponse<Leave>>(route, attempt.body, config)
          : await api.put<ApiResponse<Leave>>(`${route}/${attempt.id}/review`, attempt.body, config);
        received = true;
        if (!response.data.success || !matches(response.data.data, attempt)) throw new Error("İzin kaydı doğrulanamadı.");
      }
      const rows = await loadLeaves(controller.signal);
      if (controller.signal.aborted) return;
      if (rows.some((row) => matches(row, attempt))) onSaved(rows);
      else { setUncertain(attempt); setError("Değişiklik henüz listede görünmüyor."); }
    } catch (failure) {
      if (!controller.signal.aborted) {
        const status = (failure as { response?: { status?: number } })?.response?.status;
        if (!uncertain && !received && [401, 403, 404, 422].includes(status ?? 0)) setError(apiMessage(failure));
        else { setUncertain(attempt); setError("İşlem doğrulanamadı. Sonucu tekrar kontrol edebilirsiniz."); }
      }
    } finally {
      operation.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const title = dialog.kind === "create" ? "İzin talebi oluştur" :
    dialog.status === "APPROVED" ? "İzin talebini onayla" : "İzin talebini reddet";
  return <Modal open title={title} onClose={close} actions={<>
    <button className="btn btn-secondary" disabled={busy} onClick={close}>Kapat</button>
    <button className="btn btn-primary" disabled={busy || (!uncertain && !valid)} onClick={() => void submit()}>
      {uncertain ? "Sonucu kontrol et" : dialog.kind === "review" ? "Değerlendirmeyi kaydet" : "Talebi gönder"}
    </button>
  </>}>
    {dialog.kind === "create" ? <div className="form-grid">
      <Field label="İzin türü" required full><select disabled={locked} value={draft.leave_type}
        onChange={(event) => edit("leave_type", event.target.value)}>
        {leaveTypes.map((type) => <option key={type}>{type}</option>)}
      </select></Field>
      <Field label="Başlangıç" required><input type="date" disabled={locked} value={draft.start_date}
        onChange={(event) => edit("start_date", event.target.value)} /></Field>
      <Field label="Bitiş" required><input type="date" disabled={locked} value={draft.end_date} min={draft.start_date}
        onChange={(event) => edit("end_date", event.target.value)} /></Field>
      {days > 0 && <p className="field-full">{days} gün</p>}
      <Field label="İzin gerekçesi" required full><textarea disabled={locked} value={draft.reason}
        onChange={(event) => edit("reason", event.target.value)} /></Field>
    </div> : <>
      <p><strong>{dialog.row.staff_name}</strong> {dialog.row.start_date} – {dialog.row.end_date}</p>
      <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{dialog.row.reason}</p>
      <Field label="Değerlendirme notu (isteğe bağlı)"><textarea disabled={locked} value={comment}
        onChange={(event) => setComment(event.target.value)} /></Field>
    </>}
    {error && <p role="alert">{error}</p>}
  </Modal>;
}

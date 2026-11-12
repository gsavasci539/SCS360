import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Field, Modal } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage, API_BASE_URL } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse } from "../../types/api";
import { expenseAmount, expenseDate, expenseScope, finishExpenseAttempt, readExpenseAttempt, saveExpenseAttempt, verifyExpenseAck,
  type ExpenseAttempt } from "./expenseAttempt";

type Values = { description: string; category: string; amount: string; expense_date: string; notes: string; branch: string };
type Branches = { items: { id: string; name: string }[]; total: number; total_pages: number; allows_organization_wide: boolean };
export function ExpenseCreateModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const user = useAuthStore((s) => s.user), session = useAuthStore((s) => s.sessionVersion);
  const workspace = usePlatformWorkspace((s) => s.workspace);
  const scope = expenseScope(user, workspace), key = scope ? `${API_BASE_URL}:${scope.key}` : null;
  return <ExpenseForm key={JSON.stringify([key, session, user?.permissions])} scope={scope} storageKey={key}
    session={session} workspaceId={user?.is_super_admin ? workspace?.id : null} onClose={onClose} onSuccess={onSuccess} />;
}
function ExpenseForm({ scope, storageKey, session, workspaceId, onClose, onSuccess }: {
  scope: ReturnType<typeof expenseScope>; storageKey: string | null; session: number; workspaceId?: string | null; onClose: () => void; onSuccess: () => void;
}) {
  const can = useAuthStore((s) => s.can), { showToast } = useToast();
  const [stored] = useState(() => readExpenseAttempt(storageKey));
  const [attempt, setAttempt] = useState<ExpenseAttempt | null>(stored.attempt), [error, setError] = useState(stored.error);
  const [branches, setBranches] = useState<Branches | null>(null), [branchError, setBranchError] = useState("");
  const [busy, setBusy] = useState(false), inFlight = useRef(false), controller = useRef(new AbortController());
  const body = stored.attempt?.request;
  const { register, handleSubmit } = useForm<Values>({ defaultValues: body ? { ...body, notes: body.notes || "", expense_date: body.expense_date.slice(0, 10), branch: body.branch_id || "organization" } :
    { description: "", category: "", amount: "", expense_date: "", notes: "", branch: "" } });
  function config() { return { signal: controller.current.signal, _scsSession: session, _scsWorkspace: workspaceId || null, _scsOperator: scope?.actor }; }
  useEffect(() => {
    const abort = new AbortController(); controller.current = abort;
    async function load() {
      try {
        const items: Branches["items"] = []; let total = -1, pages = 1, wide = false;
        for (let page = 1; page <= pages; page++) {
          const { data: { data: result } } = await api.get<ApiResponse<Branches>>("/expenses/branch-options", { ...config(), params: { page, page_size: 100 } });
          if (abort.signal.aborted) return;
          if (!Array.isArray(result.items) || !Number.isInteger(result.total) || result.total < 0 || !Number.isInteger(result.total_pages) || result.total_pages < 1 || result.total_pages > 1000 ||
              typeof result.allows_organization_wide !== "boolean" || total >= 0 && (total !== result.total || pages !== result.total_pages || wide !== result.allows_organization_wide)) throw new Error("Şube listesi doğrulanamadı.");
          total = result.total; pages = result.total_pages; wide = result.allows_organization_wide;
          for (const item of result.items) {
            if (!/^[0-9a-f-]{36}$/i.test(item.id) || typeof item.name !== "string" || !item.name || items.some((row) => row.id === item.id)) throw new Error("Şube listesi doğrulanamadı.");
            items.push(item);
          }
        }
        if (items.length !== total) throw new Error("Şube listesi eksik. Tekrar açıp deneyin.");
        if (!abort.signal.aborted) setBranches({ items, total, total_pages: pages, allows_organization_wide: wide });
      } catch (reason) { if (!abort.signal.aborted) setBranchError(apiMessage(reason)); }
    }
    if (scope && can("finance.write")) void load();
    return () => abort.abort();
  }, []);
  async function submit(values: Values) {
    if (inFlight.current || !scope || !can("finance.write") || stored.error || attempt?.acknowledged || controller.current.signal.aborted) return;
    setError("");
    let pending = attempt;
    if (!pending) {
      const amount = expenseAmount(values.amount), date = expenseDate(values.expense_date);
      const branch = values.branch === "organization" ? null : values.branch;
      if (!branches || !amount || !date || !values.description.trim() || !values.category.trim() ||
          (branch === null ? !branches.allows_organization_wide : !branches.items.some((row) => row.id === branch))) {
        setError("Açıklama, kategori, geçerli tarih, pozitif kuruşlu tutar ve yetkili gider kapsamı seçin."); return;
      }
      pending = { version: 1, acknowledged: false, request: { request_id: crypto.randomUUID(), branch_id: branch,
        description: values.description.trim(), category: values.category.trim(), amount, expense_date: date, notes: values.notes.trim() || null } };
    }
    try { saveExpenseAttempt(storageKey, pending); } catch (reason) { setError(apiMessage(reason)); return; }
    setAttempt(pending); inFlight.current = true; setBusy(true);
    try {
      const response = await api.post<ApiResponse<unknown>>("/finance/expenses", pending.request, config());
      if (controller.current.signal.aborted) return;
      verifyExpenseAck(response.data.data, pending.request, scope);
      const accepted = { ...pending, acknowledged: true };
      saveExpenseAttempt(storageKey, accepted); setAttempt(accepted);
      showToast("Gider oluşturuldu", "Sunucudaki gider kaydı doğrulandı.");
    } catch (reason) { if (!controller.current.signal.aborted) setError(apiMessage(reason)); }
    finally { inFlight.current = false; if (!controller.current.signal.aborted) setBusy(false); }
  }
  function finish() {
    if (!attempt?.acknowledged) return;
    try { finishExpenseAttempt(storageKey, attempt.request); onSuccess(); onClose(); }
    catch (reason) { setError(apiMessage(reason)); }
  }
  return <Modal open title="Yeni gider" description="Bağlantı kesilirse aynı kayıtla tekrar deneyin." onClose={onClose} actions={<>
    <button className="btn btn-secondary" onClick={onClose}>Kapat</button>
    {attempt?.acknowledged ? <button className="btn btn-primary" onClick={finish}>Tamam</button> :
      <button className="btn btn-primary" disabled={busy || !scope || !can("finance.write") || Boolean(stored.error) || !attempt && (!branches || Boolean(branchError))}
        onClick={handleSubmit(submit)}>{busy ? "Kaydediliyor…" : attempt ? "Aynı kaydı doğrula" : "Oluştur"}</button>}
  </>}>
    {error && <p role="alert">{error}</p>}{branchError && <p role="alert">{branchError}</p>}
    {attempt && <p role="status">{attempt.acknowledged ? "Gider sunucuda doğrulandı." : "Sonuç bekleniyor. İşlem kimliği ve gönderilen bilgiler korunuyor; aynı kaydı doğrulayın."}</p>}
    {!can("finance.write") && <p role="alert">Gider oluşturma yetkiniz yok.</p>}
    <fieldset disabled={busy || Boolean(attempt) || Boolean(stored.error) || !can("finance.write")} style={{ border: 0, padding: 0, minWidth: 0 }}><div className="form-grid">
      <Field label="Gider kapsamı" required><select {...register("branch")}><option value="">Seçiniz</option>
        {branches?.allows_organization_wide && <option value="organization">Kurum geneli</option>}
        {branches?.items.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>
      <Field label="Açıklama" required><input maxLength={500} {...register("description")} /></Field>
      <Field label="Kategori" required><select {...register("category")}><option value="">Seçiniz</option>
        <option value="SALARY">Maaş</option><option value="UTILITIES">Faturalar</option><option value="MAINTENANCE">Bakım</option><option value="SUPPLIES">Malzeme</option><option value="OTHER">Diğer</option></select></Field>
      <Field label="Tutar" required><input type="number" min="0.01" max="9999999999.99" step="0.01" {...register("amount")} /></Field>
      <Field label="Tarih" required><input type="date" {...register("expense_date")} /></Field>
      <Field label="Notlar" full><textarea maxLength={2000} {...register("notes")} /></Field>
    </div></fieldset>
  </Modal>;
}

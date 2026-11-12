import type { AuthUser } from "../../types/api";
import type { PlatformWorkspace } from "../../stores/platformWorkspace";

export type ExpenseRequest = { request_id: string; branch_id: string | null; description: string; category: string; amount: string; expense_date: string; notes: string | null };
export type ExpenseAttempt = { version: 1; request: ExpenseRequest; acknowledged: boolean };
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function expenseScope(user: AuthUser | null, workspace: PlatformWorkspace | null) {
  const organization = user?.is_super_admin ? workspace?.operatorId === user.id ? workspace.id : null : user?.organization_id;
  return user && organization ? { actor: user.id, organization,
    key: `scs360-expense:v1:${JSON.stringify([user.id, organization, [...user.branch_ids].sort()])}` } : null;
}
export function expenseAmount(value: unknown): string | null {
  const raw = String(value);
  return /^(?:0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(raw) && Number(raw) > 0 ? Number(raw).toFixed(2) : null;
}
export function expenseDate(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value ? `${value}T00:00:00+03:00` : null;
}
function valid(value: unknown): value is ExpenseAttempt {
  if (!value || typeof value !== "object") return false;
  const row = value as ExpenseAttempt, body = row.request;
  return row.version === 1 && typeof row.acknowledged === "boolean" && Boolean(body) && uuid.test(body.request_id) &&
    (body.branch_id === null || typeof body.branch_id === "string" && uuid.test(body.branch_id)) &&
    typeof body.description === "string" && Boolean(body.description.trim()) && body.description.length <= 500 &&
    typeof body.category === "string" && Boolean(body.category.trim()) && body.category.length <= 100 &&
    typeof body.amount === "string" && expenseAmount(body.amount) === body.amount &&
    typeof body.expense_date === "string" && expenseDate(body.expense_date.slice(0, 10)) === body.expense_date &&
    (body.notes === null || typeof body.notes === "string" && body.notes.length <= 2000);
}
export function readExpenseAttempt(key: string | null): { attempt: ExpenseAttempt | null; error: string } {
  if (!key) return { attempt: null, error: "Gider için kurum çalışma alanını açın." };
  try {
    const raw = sessionStorage.getItem(key);
    if (raw === null) return { attempt: null, error: "" };
    const attempt: unknown = JSON.parse(raw);
    if (!valid(attempt)) throw new Error("invalid recovery record");
    const b = attempt.request;
    return { attempt: { version: 1, acknowledged: attempt.acknowledged, request: {
      request_id: b.request_id, branch_id: b.branch_id, description: b.description, category: b.category,
      amount: b.amount, expense_date: b.expense_date, notes: b.notes,
    } }, error: "" };
  } catch { return { attempt: null, error: "Önceki gider bilgisi okunamadı. Yeni kayıt açmadan gider geçmişini kontrol edin." }; }
}
export function saveExpenseAttempt(key: string | null, attempt: ExpenseAttempt) {
  if (!key || !valid(attempt)) throw new Error("Gider bilgileri doğrulanamadı.");
  const current = readExpenseAttempt(key);
  if (current.error || current.attempt && JSON.stringify(current.attempt.request) !== JSON.stringify(attempt.request))
    throw new Error("Önceki gider işlemi değişti. Sayfayı yenileyip sonucunu kontrol edin.");
  const serialized = JSON.stringify(attempt);
  try {
    sessionStorage.setItem(key, serialized);
    if (sessionStorage.getItem(key) !== serialized) throw new Error("storage mismatch");
  } catch { throw new Error("Gider işlem kimliği saklanamadı. Tarayıcı depolamasını kontrol edin; yeni kayıt gönderilmedi."); }
}
export function finishExpenseAttempt(key: string | null, request: ExpenseRequest) {
  const current = readExpenseAttempt(key);
  if (!key || current.error || !current.attempt?.acknowledged || JSON.stringify(current.attempt.request) !== JSON.stringify(request))
    throw new Error("Gider sonucu saklanamadı veya işlem değişti. Yeni kayıt açmadan sonucu kontrol edin.");
  sessionStorage.removeItem(key);
  if (sessionStorage.getItem(key) !== null) throw new Error("İşlem bilgisi temizlenemedi.");
}
export function verifyExpenseAck(value: unknown, request: ExpenseRequest, scope: { actor: string; organization: string }) {
  const row = value as Record<string, unknown> | null;
  if (!row || row.id !== request.request_id || row.organization_id !== scope.organization || row.created_by !== scope.actor ||
      row.branch_id !== request.branch_id || row.description !== request.description || row.category !== request.category ||
      expenseAmount(row.amount) !== request.amount || row.notes !== request.notes ||
      typeof row.expense_date !== "string" || new Date(row.expense_date.endsWith("Z") || /[+-]\d\d:\d\d$/.test(row.expense_date) ? row.expense_date : `${row.expense_date}Z`).getTime() !== new Date(request.expense_date).getTime())
    throw new Error("Sunucu yanıtı gönderilen giderle eşleşmedi. Aynı işlem kimliğiyle tekrar doğrulayın.");
}

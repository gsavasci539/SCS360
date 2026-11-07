import type { AuthUser } from "../../types/api";
import type { PlatformWorkspace } from "../../stores/platformWorkspace";

export type CheckoutPurpose = "staff" | "parent";
export type CheckoutState = "INITIALIZING" | "PENDING" | "FRAUD_REVIEW" | "PAID_REVIEW" | "COMPLETED" | "FAILED" | "REFUNDED";
export type SchoolCheckoutAttempt = { version: 1; request_id: string; debt_id: string; amount: string; status: CheckoutState };
export type SchoolCheckoutResult = { conversation_id: string; status: CheckoutState; debt_id?: string; amount?: string;
  checkout_url?: string; payment_page_url?: string; message?: string; payment_id?: string; can_resume?: boolean; can_refresh?: boolean };
const states = new Set<CheckoutState>(["INITIALIZING", "PENDING", "FRAUD_REVIEW", "PAID_REVIEW", "COMPLETED", "FAILED", "REFUNDED"]);
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function checkoutIdentifier(value: unknown): string | null {
  return typeof value === "string" && uuid.test(value) ? value : null;
}
export function checkoutAmount(value: unknown): string | null {
  if ((typeof value !== "number" && typeof value !== "string") || !/^(?:0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(String(value))) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 && parsed <= 9999999999.99 ? parsed.toFixed(2) : null;
}
export function checkoutScope(user: AuthUser | null, workspace: PlatformWorkspace | null, purpose: CheckoutPurpose): string | null {
  if (!user) return null;
  const organization = user.is_super_admin ? workspace?.operatorId === user.id ? workspace.id : null : user.organization_id;
  if (!organization || purpose === "parent" && user.is_super_admin) return null;
  return JSON.stringify([user.id, organization, purpose, [...user.branch_ids].sort()]);
}
export function checkoutAttemptKey(scope: string | null, debtId: string): string | null {
  return scope && checkoutIdentifier(debtId) ? `scs360-school-checkout:v1:${scope}:${debtId}` : null;
}
function validAttempt(value: unknown): value is SchoolCheckoutAttempt {
  if (!value || typeof value !== "object") return false;
  const row = value as SchoolCheckoutAttempt;
  return row.version === 1 && Boolean(checkoutIdentifier(row.request_id)) && Boolean(checkoutIdentifier(row.debt_id)) &&
    checkoutAmount(row.amount) === row.amount && states.has(row.status);
}
function sanitized(value: SchoolCheckoutAttempt): SchoolCheckoutAttempt {
  // Only the recovery identity and public ledger metadata may reach storage.
  return { version: 1, request_id: value.request_id, debt_id: value.debt_id, amount: value.amount, status: value.status };
}
export function readSchoolCheckout(key: string | null): { attempt: SchoolCheckoutAttempt | null; error: string } {
  if (!key) return { attempt: null, error: "Ödeme için hesabınızı ve kurum çalışma alanını kontrol edin." };
  try {
    const raw = sessionStorage.getItem(key);
    if (raw === null) return { attempt: null, error: "" };
    const value: unknown = JSON.parse(raw);
    if (!validAttempt(value) || !key.endsWith(`:${value.debt_id}`)) throw new Error("invalid checkout recovery record");
    return { attempt: sanitized(value), error: "" };
  } catch {
    return { attempt: null, error: "Önceki ödeme kimliği okunamadı. Yeni ödeme başlatmadan önce işlem sonucunu kurumunuzla kontrol edin." };
  }
}
export function saveSchoolCheckout(key: string | null, value: SchoolCheckoutAttempt): void {
  if (!key || !validAttempt(value) || !key.endsWith(`:${value.debt_id}`)) throw new Error("Ödeme kimliği ve borç bilgileri doğrulanamadı.");
  try {
    const raw = JSON.stringify(sanitized(value)); sessionStorage.setItem(key, raw);
    if (sessionStorage.getItem(key) !== raw) throw new Error("storage mismatch");
  } catch { throw new Error("Ödeme kimliği bu tarayıcıda saklanamadı. Güvenli tekrar deneme için tarayıcı depolamasına izin verin."); }
}
export function clearSchoolCheckout(key: string | null, requestId: string): void {
  const current = readSchoolCheckout(key);
  if (current.error || current.attempt?.request_id !== requestId) throw new Error("Önceki ödeme kaydı değişti; yeni ödeme açılmadı.");
  try {
    sessionStorage.removeItem(key!);
    if (sessionStorage.getItem(key!) !== null) throw new Error("storage mismatch");
  } catch { throw new Error("Önceki ödeme kimliği temizlenemedi; yeni ödeme açılmadı."); }
}
export function checkoutResult(value: unknown, expectedId: string): SchoolCheckoutResult {
  if (!value || typeof value !== "object") throw new Error("Ödeme sonucu doğrulanamadı.");
  const row = value as SchoolCheckoutResult;
  const identifier = checkoutIdentifier(row.conversation_id);
  if (!identifier || identifier !== expectedId || !states.has(row.status)) throw new Error("Ödeme sonucu bu işlemle eşleşmiyor.");
  return row;
}
export function checkoutBase(purpose: CheckoutPurpose) {
  return purpose === "parent" ? "/parent/payments/checkouts" : "/payments/iyzico/checkouts";
}

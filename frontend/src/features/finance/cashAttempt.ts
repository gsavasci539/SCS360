import type { AuthUser } from "../../types/api";
import type { PlatformWorkspace } from "../../stores/platformWorkspace";

export type CashReceipt = { payment_id?: string; receipt_id: string; receipt_number: string; remaining_debt: string };
export type CashRequest = { debt_id: string; amount: string; payment_method: string; notes: string | null; request_id: string };
export type CashAttempt = { version: 1; request: CashRequest; receipt: CashReceipt | null };
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const methods = new Set(["CASH", "CREDIT_CARD", "BANK_TRANSFER", "EFT", "OTHER"]);

export function cashAttemptKey(user: AuthUser | null, workspace: PlatformWorkspace | null): string | null {
  if (!user) return null;
  const organization = user.is_super_admin ? workspace?.operatorId === user.id ? workspace.id : null : user.organization_id;
  return organization ? `scs360-cash-attempt:v1:${JSON.stringify([user.id, organization, [...user.branch_ids].sort()])}` : null;
}

function validReceipt(value: unknown): value is CashReceipt {
  if (!value || typeof value !== "object") return false;
  const row = value as CashReceipt;
  return typeof row.receipt_id === "string" && row.receipt_id.length > 0 && row.receipt_id.length <= 100 &&
    typeof row.receipt_number === "string" && row.receipt_number.length > 0 && row.receipt_number.length <= 30 &&
    typeof row.remaining_debt === "string" && row.remaining_debt.trim() !== "" &&
    Number.isFinite(Number(row.remaining_debt)) && Number(row.remaining_debt) >= 0;
}

function validAttempt(value: unknown): value is CashAttempt {
  if (!value || typeof value !== "object") return false;
  const attempt = value as CashAttempt, body = attempt.request;
  return attempt.version === 1 && Boolean(body) && typeof body.debt_id === "string" && uuid.test(body.debt_id) &&
    typeof body.request_id === "string" && uuid.test(body.request_id) &&
    typeof body.amount === "string" && body.amount.trim() !== "" && Number.isFinite(Number(body.amount)) && Number(body.amount) > 0 &&
    methods.has(body.payment_method) && (body.notes === null || typeof body.notes === "string" && body.notes.length <= 2000) &&
    (attempt.receipt === null || validReceipt(attempt.receipt));
}

export function readCashAttempt(key: string | null): { attempt: CashAttempt | null; error: string } {
  if (!key) return { attempt: null, error: "Tahsilat için kurum çalışma alanını açın." };
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return { attempt: null, error: "" };
    const value: unknown = JSON.parse(raw);
    if (!validAttempt(value)) throw new Error("invalid cash attempt");
    return { attempt: value, error: "" };
  } catch {
    // Do not silently discard a possibly committed transaction and mint a new ID.
    return { attempt: null, error: "Önceki tahsilat bilgisi okunamadı. Yeni işlem açmadan önce tahsilat geçmişini yetkili personelle kontrol edin." };
  }
}

export function writeCashAttempt(key: string | null, attempt: CashAttempt): void {
  if (!key || !validAttempt(attempt)) throw new Error("Tahsilat bilgilerini kontrol edin.");
  try {
    const serialized = JSON.stringify(attempt);
    sessionStorage.setItem(key, serialized);
    if (sessionStorage.getItem(key) !== serialized) throw new Error("storage mismatch");
  } catch {
    throw new Error("İşlem kimliği bu tarayıcıda saklanamadı. Güvenli tekrar deneme için tarayıcı depolamasına izin verip tekrar deneyin.");
  }
}

export function clearCashAttempt(key: string | null): void {
  try {
    if (!key) throw new Error("missing scope");
    sessionStorage.removeItem(key);
    if (sessionStorage.getItem(key) !== null) throw new Error("storage mismatch");
  } catch { throw new Error("Önceki işlem bilgisi temizlenemedi. Yeni tahsilat açılmadı."); }
}

export function completeCashAttempt(key: string | null, original: CashAttempt, receipt: CashReceipt): void {
  const current = readCashAttempt(key);
  if (!current.error && current.attempt?.request.request_id === original.request.request_id) {
    writeCashAttempt(key, { ...original, receipt });
  }
}

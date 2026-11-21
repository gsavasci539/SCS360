import { api } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

function sameInvoice(left: DataRecord | undefined, right: DataRecord) {
  return Boolean(left?.id && right.id && left.id === right.id && left.organization_id && left.organization_id === right.organization_id &&
    left.plan_id === right.plan_id && left.currency && left.currency === right.currency &&
    String(left.amount ?? "").trim() && String(right.amount ?? "").trim() &&
    Number.isFinite(Number(left.amount)) && Number(left.amount) === Number(right.amount));
}

async function confirmInvoice(scope: "platform" | "subscription", invoice: DataRecord, written: DataRecord,
  checkout?: { status: unknown; id?: unknown }) {
  if (!sameInvoice(written, invoice) || typeof written.status !== "string" || !written.status) {
    throw new Error("Üyelik ödeme kaydı doğrulanamadı.");
  }
  const result = await api.get<ApiResponse<DataRecord[]>>(`/${scope}/invoices`, {
    params: { record_id: invoice.id, limit: 1, ...(scope === "platform" ? { organization_id: invoice.organization_id } : {}) },
  });
  const rows = result.data.data;
  const saved = Array.isArray(rows) && rows.length === 1 ? rows[0] : undefined;
  if (result.data.success !== true || !saved || !sameInvoice(saved, written) || saved.status !== written.status ||
    (checkout && (saved.checkout_status !== checkout.status || (checkout.id !== undefined && saved.checkout_id !== checkout.id)))) {
    throw new Error("Sunucudan okunan üyelik ödeme durumu doğrulanamadı.");
  }
  return saved;
}

export function confirmPlatformInvoice(invoice: DataRecord, written: DataRecord, review = false) {
  return confirmInvoice("platform", invoice, written, review ? { status: written.checkout_status } : undefined);
}

export function confirmPaymentStatus(scope: "platform" | "subscription", invoice: DataRecord, response: { invoice?: DataRecord; status?: string; checkout_id?: string | null }) {
  if (!response?.invoice || typeof response.status !== "string" || !("checkout_id" in response) ||
    (response.checkout_id !== null && !response.checkout_id) ||
    (response.checkout_id === null && response.status !== response.invoice.status)) {
    throw new Error("Ödeme durumu yanıtı doğrulanamadı.");
  }
  return confirmInvoice(scope, invoice, response.invoice, {
    status: response.checkout_id ? response.status : null,
    id: response.checkout_id,
  });
}

export function confirmOwnerInvoice(written: DataRecord, target = written) {
  return confirmInvoice("subscription", target, written);
}

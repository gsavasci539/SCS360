import { api } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export async function confirmPlatformInvoice(invoice: DataRecord, written: DataRecord, review = false) {
  if (written?.id !== invoice.id || written.organization_id !== invoice.organization_id ||
    written.currency !== invoice.currency || Number(written.amount) !== Number(invoice.amount)) {
    throw new Error("Üyelik ödeme kaydı doğrulanamadı.");
  }
  const result = await api.get<ApiResponse<DataRecord[]>>("/platform/invoices", {
    params: { record_id: invoice.id, organization_id: invoice.organization_id, limit: 1 },
  });
  const rows = result.data.data;
  const saved = Array.isArray(rows) && rows.length === 1 ? rows[0] : undefined;
  if (result.data.success !== true || saved?.id !== written.id || saved.organization_id !== written.organization_id ||
    saved.currency !== written.currency || Number(saved.amount) !== Number(written.amount) || saved.status !== written.status ||
    (review && saved.checkout_status !== written.checkout_status)) {
    throw new Error("Sunucudan okunan üyelik ödeme durumu doğrulanamadı.");
  }
}

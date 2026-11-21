import { isAxiosError } from "axios";
import { api } from "../../lib/api";
import type { DataRecord } from "../../types/api";

export const outboxStatuses: Record<string, string> = {
  PENDING: "Kuyrukta",
  SENT: "Sağlayıcı kabul etti",
  FAILED: "Başarısız",
  CANCELLED: "İptal edildi",
};

export const outboxScope = (row: DataRecord) => row.branch_id ? { branch_id: row.branch_id } : {};

export async function deleteOutboxRecord(row: DataRecord) {
  const path = `/outbox/${row.id}`;
  const params = outboxScope(row);
  await api.delete(path, { params });
  try {
    await api.get(path, { params });
  } catch (reason) {
    if (isAxiosError(reason) && reason.response?.status === 404) return;
    throw reason;
  }
  throw new Error("Gönderim kaydının kaldırıldığı doğrulanamadı.");
}

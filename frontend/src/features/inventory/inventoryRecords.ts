import { api } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

type InventoryPath = "/inventory/locations" | "/inventory/items" | "/inventory/assignments" | "/inventory/maintenance-requests";
type Fields = Record<string, string | null>;

export async function verifyInventoryRecord(path: InventoryPath, id: unknown, branch: string | null, expected: Fields) {
  if (typeof id !== "string" || !id) throw new Error("Envanter kayıt kimliği alınamadı");
  const response = await api.get<ApiResponse<DataRecord[]>>(path, {
    params: { record_id: id, branch_id: branch || undefined, limit: 1 },
  });
  const rows = response.data.data;
  const row = Array.isArray(rows) && rows.length === 1 ? rows[0] : undefined;
  if (!response.data.success || !row || row.id !== id || (branch && row.branch_id !== branch)
      || Object.entries(expected).some(([key, value]) => row[key] !== value)) {
    throw new Error("Envanter kaydı sunucuda doğrulanamadı");
  }
}

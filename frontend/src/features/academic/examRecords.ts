import { api } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export async function readExamRecord(id: string, branch: string | undefined) {
  const reply = await api.get<ApiResponse<DataRecord[]>>("/exams", { params: { record_id: id, branch_id: branch, limit: 1 } });
  const rows = reply.data.data;
  const row = Array.isArray(rows) && rows.length === 1 ? rows[0] : null;
  if (!reply.data.success || !row || row.id !== id || (branch && row.branch_id !== branch)) {
    throw new Error("Kalıcı sınav kaydı doğrulanamadı");
  }
  return row;
}

import { afterEach, expect, it, vi } from "vitest";
import { canAnalyze, getAnalysis } from "../lib/analysis";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() } }));
afterEach(() => { vi.resetAllMocks(); useAuthStore.getState().clearSession(); });

it("birleşik raporun tüm alanlarını ister, öğretmen devam izninin eşdeğerini kabul eder", () => {
  const permissions = new Set(["classes.read", "academic.read", "teacher.view_attendance"]);
  expect(canAnalyze("/ai/class-analysis/class-uuid", (permission) => permissions.has(permission))).toBe(true);
  expect(canAnalyze("/ai/ai-financial-predictions", (permission) => permissions.has(permission))).toBe(false);
  expect(canAnalyze("/ai/insights-report", (permission) => permission === "report.read")).toBe(false);
});

it("yetkisiz opsiyonel kart için API isteği yapmaz, yetkili sorguyu parametreleriyle gönderir", async () => {
  const denied = await getAnalysis("/ai/payment-forecast");
  expect(denied.data.data).toBeNull(); expect(api.get).not.toHaveBeenCalled();
  useAuthStore.setState({ user: { id: "finance", organization_id: "school", first_name: "Finance", last_name: "Test", email: "finance@test.invalid",
    is_super_admin: false, roles: [], branch_ids: [], permissions: ["finance.read"] } });
  vi.mocked(api.get).mockResolvedValue({ data: { data: { collected: "125.50" } } });
  await getAnalysis("/ai/payment-forecast?months=3"); expect(api.get).toHaveBeenCalledWith("/ai/payment-forecast?months=3", undefined);
});

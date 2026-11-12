import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ExpenseCreateModal } from "../features/finance/ExpenseCreateModal";
import { expenseScope, readExpenseAttempt, saveExpenseAttempt, finishExpenseAttempt, expenseDate, type ExpenseRequest } from "../features/finance/expenseAttempt";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
const mocks = vi.hoisted(() => ({ toast: vi.fn() }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast: mocks.toast }) }));
vi.mock("../lib/api", () => ({ API_BASE_URL: "/api", api: { get: vi.fn(), post: vi.fn() }, apiMessage: (e: unknown) => e instanceof Error ? e.message : "Hata" }));
const actor = "00000000-0000-4000-8000-000000000001", org = "00000000-0000-4000-8000-000000000002", branch = "00000000-0000-4000-8000-000000000003";
const onClose = vi.fn(), onSuccess = vi.fn();
function view() { return render(<ExpenseCreateModal onClose={onClose} onSuccess={onSuccess} />); }
function key() { return `/api:${expenseScope(useAuthStore.getState().user, usePlatformWorkspace.getState().workspace)!.key}`; }
function ack(body: ExpenseRequest) { return { data: { data: { ...body, id: body.request_id, organization_id: org, created_by: actor, expense_date: "2026-11-11T21:00:00", amount: "100.01" } } }; }
async function fill() {
  await screen.findByRole("option", { name: "Gerçek şube" });
  for (const [label, value] of [["Gider kapsamı", branch], ["Açıklama", "Kırtasiye"], ["Kategori", "SUPPLIES"], ["Tutar", "100.01"], ["Tarih", "2026-11-12"], ["Notlar", "Belge no 12"]])
    fireEvent.change(screen.getByLabelText(new RegExp(label)), { target: { value } });
}
beforeEach(() => {
  sessionStorage.clear(); usePlatformWorkspace.setState({ workspace: null });
  useAuthStore.setState({ sessionVersion: 1, user: { id: actor, organization_id: org, email: "staff@example.invalid", first_name: "Test", last_name: "Staff", is_super_admin: false, permissions: ["finance.write"], branch_ids: [branch], roles: [] } });
  vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [{ id: branch, name: "Gerçek şube" }], total: 1, total_pages: 1, allows_organization_wide: false } } });
  vi.mocked(api.post).mockImplementation(async (_path, body) => ack(body as ExpenseRequest));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.resetAllMocks(); onClose.mockReset(); onSuccess.mockReset(); sessionStorage.clear(); });
it("kayıp ACK ve yeniden açmada aynı kalıcı kimlik/gövdeyi doğrular; Tamam öncesi yeni gider açmaz", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("ACK kayboldu"));
  const first = view(); await fill(); fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));
  await screen.findByText("ACK kayboldu");
  const original = vi.mocked(api.post).mock.calls[0][1] as ExpenseRequest;
  expect(readExpenseAttempt(key()).attempt?.request).toEqual(original);
  expect(original).toEqual({ request_id: expect.stringMatching(/^[0-9a-f-]{36}$/i), branch_id: branch, description: "Kırtasiye", category: "SUPPLIES", amount: "100.01", expense_date: "2026-11-12T00:00:00+03:00", notes: "Belge no 12" });
  expect(onClose).not.toHaveBeenCalled(); expect(mocks.toast).not.toHaveBeenCalled();
  first.unmount(); view();
  expect(screen.getByLabelText(/Tutar/)).toHaveValue(100.01); expect(screen.getByLabelText(/Tutar/)).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Aynı kaydı doğrula" }));
  await screen.findByText("Gider sunucuda doğrulandı.");
  expect(vi.mocked(api.post).mock.calls[1][1]).toEqual(original);
  expect(readExpenseAttempt(key()).attempt?.acknowledged).toBe(true); expect(onSuccess).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Tamam" }));
  expect(onSuccess).toHaveBeenCalledTimes(1); expect(onClose).toHaveBeenCalledTimes(1); expect(readExpenseAttempt(key()).attempt).toBeNull();
});
it("yanlış kurum ACK başarı göstermez ve kimliği korur", async () => {
  vi.mocked(api.post).mockImplementation(async (_path, request) => { const result = ack(request as ExpenseRequest); result.data.data.organization_id = branch; return result; });
  view(); await fill(); fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("eşleşmedi");
  expect(mocks.toast).not.toHaveBeenCalled(); expect(readExpenseAttempt(key()).attempt?.acknowledged).toBe(false);
});
it("depolama hatasında veya bozuk önceki kayıtta HTTP göndermeden durur", async () => {
  const page = view(); await fill();
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
  fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("saklanamadı"); expect(api.post).not.toHaveBeenCalled();
  vi.restoreAllMocks(); page.unmount(); sessionStorage.setItem(key(), "corrupt"); view();
  await screen.findByRole("option", { name: "Gerçek şube" });
  expect(screen.getByRole("button", { name: "Oluştur" })).toBeDisabled(); expect(screen.getByRole("alert")).toHaveTextContent("okunamadı");
});
it("açık kapsam seçimi ve geçerli tarih/kuruş olmadan göndermez", async () => {
  view(); await fill();
  fireEvent.change(screen.getByLabelText(/Gider kapsamı/), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Oluştur" })); await screen.findByRole("alert"); expect(api.post).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText(/Gider kapsamı/), { target: { value: branch } });
  fireEvent.change(screen.getByLabelText(/Tutar/), { target: { value: "1.001" } });
  fireEvent.click(screen.getByRole("button", { name: "Oluştur" })); await waitFor(() => expect(api.post).not.toHaveBeenCalled());
  expect(expenseDate("2026-02-30")).toBeNull();
});
it("kapsam/yetki değişimi geç yanıtı başarıya çeviremez; Root açık kurum olmadan gönderemez", async () => {
  let resolve!: (result: ReturnType<typeof ack>) => void;
  vi.mocked(api.post).mockImplementation(() => new Promise((done) => { resolve = done; }));
  view(); await fill(); fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  const request = vi.mocked(api.post).mock.calls[0][1] as ExpenseRequest, oldKey = key();
  act(() => { useAuthStore.setState({ user: { ...useAuthStore.getState().user!, organization_id: branch, permissions: [] } }); });
  await act(async () => { resolve(ack(request)); });
  expect(mocks.toast).not.toHaveBeenCalled(); expect(readExpenseAttempt(oldKey).attempt?.acknowledged).toBe(false);
  act(() => { useAuthStore.setState({ user: { ...useAuthStore.getState().user!, is_super_admin: true, permissions: ["finance.write"] } }); });
  expect(screen.getByRole("button", { name: "Oluştur" })).toBeDisabled();
});
it("başka editörün yeni isteğini eski ACK ile üzerine yazmaz veya silmez", async () => {
  const page = view(); await fill(); fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));
  await screen.findByText("Gider sunucuda doğrulandı.");
  const old = readExpenseAttempt(key()).attempt!; page.unmount(); finishExpenseAttempt(key(), old.request);
  const next = { ...old, acknowledged: false, request: { ...old.request, request_id: crypto.randomUUID(), amount: "20.00" } };
  saveExpenseAttempt(key(), next);
  expect(() => saveExpenseAttempt(key(), old)).toThrow("değişti"); expect(() => finishExpenseAttempt(key(), old.request)).toThrow("değişti");
  expect(readExpenseAttempt(key()).attempt).toEqual(next);
});
it("tüm şube sayfalarını yükler; eksik ikinci sayfada ilk şubeyi varsaymaz", async () => {
  vi.mocked(api.get).mockImplementation(async (_path, config) => ({ data: { data: {
    items: (config?.params as { page: number } | undefined)?.page === 1 ? [{ id: branch, name: "Gerçek şube" }] : [],
    total: 2, total_pages: 2, allows_organization_wide: false,
  } } }));
  view();
  expect(await screen.findByRole("alert")).toHaveTextContent("eksik");
  expect(api.get).toHaveBeenCalledTimes(2);
  expect(screen.getByRole("button", { name: "Oluştur" })).toBeDisabled(); expect(api.post).not.toHaveBeenCalled();
});
it("çift tıklamada tek POST yapar; yanlış kuruş ACK aynı istekle kurtarılır ve doğrulanmış sonuç yeniden açılır", async () => {
  let resolve!: (value: ReturnType<typeof ack>) => void;
  vi.mocked(api.post).mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
  const page = view(); await fill();
  const submit = screen.getByRole("button", { name: "Oluştur" });
  fireEvent.click(submit); fireEvent.click(submit);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  const request = vi.mocked(api.post).mock.calls[0][1] as ExpenseRequest, wrong = ack(request);
  wrong.data.data.amount = "100.00";
  await act(async () => { resolve(wrong); });
  expect(screen.getByRole("alert")).toHaveTextContent("eşleşmedi"); expect(mocks.toast).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Aynı kaydı doğrula" }));
  await screen.findByText("Gider sunucuda doğrulandı.");
  page.unmount(); view();
  expect(screen.getByRole("button", { name: "Tamam" })).toBeEnabled();
  expect(api.post).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api.post).mock.calls[1][1]).toEqual(request);
  await screen.findByRole("option", { name: "Gerçek şube" });
});

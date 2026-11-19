import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn(async () => null) }));
vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  unwrap: (response: { data: { data: unknown } }) => response.data.data,
  apiMessage: (error: Error) => error.message,
}));

const actor: AuthUser = {
  id: "teacher", organization_id: "school", first_name: "Test", last_name: "Öğretmen", email: "teacher@test.invalid",
  roles: [{ id: "legacy-teacher", slug: "teacher2", name: "Öğretmen" }],
  permissions: ["dashboard.read", "students.read", "messaging.read", "messaging.send"],
  is_super_admin: false, branch_ids: ["branch"],
};
const response = (data: unknown) => ({ data: { data } });
const renderDashboard = () => render(<MemoryRouter><DashboardPage /></MemoryRouter>);

afterEach(() => {
  cleanup();
  useAuthStore.getState().clearSession();
  vi.resetAllMocks();
});

it("keeps the dialog and draft open after a lost response until the stored reply is verified", async () => {
  useAuthStore.getState().setUser(actor);
  const endpoint = "/teacher/chat/student";
  const content = "Haftalık ders planı güncellendi.";
  let requestId = "";
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/teacher/chat-branches") return response([{ id: "branch", name: "Test Şubesi" }]);
    if (path === "/teacher/chat-contacts") return response({ page: 1, total_pages: 1, items: [
      { student_id: "student", student_name: "Kayıtlı öğrenci", parent_id: "guardian", parent_name: "Kayıtlı veli",
        branch_id: "branch", class_name: "Sınıf A" },
    ] });
    if (path === endpoint) return response([]);
    if (path === `${endpoint}/sent/${requestId}`) return response({
      id: requestId, content, is_current_user: true, is_read: false, sent_at: "2026-11-19T12:00:00Z",
    });
    return response({});
  });
  vi.mocked(api.post).mockImplementation(async (_, data) => {
    requestId = (data as { request_id: string }).request_id;
    throw new Error("Test yanıtı kesildi.");
  });
  renderDashboard();
  fireEvent.click(await screen.findByRole("button", { name: "Hızlı mesaj" }));
  const dialog = within(screen.getByRole("dialog", { name: "Hızlı mesaj" }));
  fireEvent.click(await dialog.findByRole("button", { name: /Kayıtlı öğrenci.*Kayıtlı veli/ }));
  const draft = dialog.getByRole("textbox", { name: "Sohbet mesajı" });
  fireEvent.change(draft, { target: { value: content } });
  fireEvent.click(dialog.getByRole("button", { name: "Gönder" }));
  expect(await dialog.findByRole("alert")).toHaveTextContent("Test yanıtı kesildi.");
  expect(draft).toHaveValue(content);
  expect(api.post).toHaveBeenCalledWith(endpoint, { message: content, request_id: requestId },
    expect.objectContaining({ params: { parent_id: "guardian", branch_id: "branch" } }));
  fireEvent.click(dialog.getByRole("button", { name: "Gönderimi kontrol et" }));
  await dialog.findByText(content);
  expect(draft).toHaveValue("");
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(api.get).not.toHaveBeenCalledWith("/users");
});

it("hides the quick-chat entry when the legacy role lacks student access", async () => {
  useAuthStore.getState().setUser({ ...actor, permissions: ["dashboard.read", "messaging.read"] });
  vi.mocked(api.get).mockResolvedValue(response({}));
  renderDashboard();
  await screen.findByRole("heading", { name: "Günaydın, öğretmen paneli hazır." });
  expect(screen.queryByRole("button", { name: "Hızlı mesaj" })).not.toBeInTheDocument();
  expect(screen.queryByText("Bildirimler", { exact: true })).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes("chat-"))).toBe(false);
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/notifications/unread-count")).toBe(false);
});

it("shows the API unread count for an authorized teacher, including a verified zero", async () => {
  const authorized = { ...actor, permissions: [...actor.permissions, "notification.read"] };
  let count = 7;
  useAuthStore.getState().setUser(authorized);
  vi.mocked(api.get).mockImplementation(async (path) =>
    response(path === "/notifications/unread-count" ? { unread_count: count } : {}));
  renderDashboard();
  let card = (await screen.findByText("Okunmamış bildirimler")).closest(".stat-card");
  expect(card).toHaveTextContent("7");
  count = 0;
  act(() => useAuthStore.getState().setUser({ ...authorized, branch_ids: ["other-branch"] }));
  card = (await screen.findByText("Okunmamış bildirimler")).closest(".stat-card");
  expect(card).toHaveTextContent("0");
});

it("holds an unavailable state while ignoring a previous actor's unread response", async () => {
  const authorized = { ...actor, permissions: [...actor.permissions, "notification.read"] };
  useAuthStore.getState().setUser(authorized);
  let priorSignal: AbortSignal | undefined;
  let finish!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path !== "/notifications/unread-count") return response({});
    if (priorSignal) throw new Error("Test bağlantısı kesildi.");
    priorSignal = config?.signal as AbortSignal;
    return new Promise((resolve) => { finish = resolve; });
  });
  renderDashboard();
  await waitFor(() => expect(priorSignal).toBeDefined());
  act(() => useAuthStore.getState().setUser({ ...authorized, id: "next-teacher" }));
  const card = (await screen.findByText("Bildirim sayısı alınamadı")).closest(".stat-card");
  expect(priorSignal?.aborted).toBe(true);
  await act(async () => finish(response({ unread_count: 99 })));
  expect(card).toHaveTextContent("—");
  expect(card).not.toHaveTextContent(/0|99/);
});

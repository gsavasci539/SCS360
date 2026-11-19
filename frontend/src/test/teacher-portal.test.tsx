import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import TeacherPortalPage from "../features/teacher/TeacherPortalPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Program alınamadı",
  unwrap: (result: { data: { data: unknown } }) => result.data.data }));
const classrooms = [{ id: "class-a", name: "Sınıf A", student_count: 2 }, { id: "class-b", name: "Sınıf B", student_count: 2 }];
const response = (data: unknown) => ({ data: { data } });
beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async (path) => response(path === "/teacher/my-classes" ? classrooms : path === "/teacher/pending-tasks" ? { tasks: [] } : []));
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("program isteği başarısızsa sahte boş program yerine görünür hata ve yeniden deneme sunar", async () => {
  const normal = vi.mocked(api.get).getMockImplementation()!;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/teacher/today-schedule") throw new Error("Network");
    return normal(path, config);
  });
  render(<TeacherPortalPage />);
  await screen.findByText("Program alınamadı");
  vi.mocked(api.get).mockImplementation(normal);
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  await screen.findByRole("cell", { name: "Sınıf A" });
});

it("sağlık talimatı yetkisi olmadan ilaç sekmesini ve isteğini açmaz", async () => {
  useAuthStore.getState().clearSession(); render(<TeacherPortalPage />);
  await screen.findByRole("cell", { name: "Sınıf A" });
  expect(screen.queryByRole("button", { name: "İlaç Talepleri" })).not.toBeInTheDocument();
  expect(api.get).not.toHaveBeenCalledWith("/teacher/medicine-requests");
});

it("Mesajlar sekmesi atanmış öğrenci ve velileri sayfalı sohbet dizininden yükler", async () => {
  useAuthStore.getState().setUser({
    id: "teacher", organization_id: "school", first_name: "Test", last_name: "Öğretmen", email: "teacher@test.invalid",
    permissions: ["students.read", "messaging.read"], roles: [], branch_ids: [], is_super_admin: false,
  });
  const normal = vi.mocked(api.get).getMockImplementation()!;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/teacher/chat-contacts") return response({ page: 1, total_pages: 1, items: [
      { student_id: "new", student_name: "Güncel öğrenci", parent_id: "parent", parent_name: "Veli", branch_id: "branch" },
    ] });
    return normal(path, config);
  });
  render(<TeacherPortalPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Mesajlar" }));
  await screen.findByText("Güncel öğrenci");
  expect(api.get).toHaveBeenCalledWith("/teacher/chat-contacts", expect.objectContaining({
    params: { branch_id: undefined, search: "", page: 1 },
  }));
});

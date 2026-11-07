import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import TeacherPortalPage from "../features/teacher/TeacherPortalPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Program alınamadı" }));
vi.mock("../features/parent/ChatInterface", () => ({ ChatInterface: () => <div>Sohbet</div> }));
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

it("hızlı sınıf değişiminde eski yanıt yeni sınıfın öğrencilerini değiştiremez", async () => {
  const normal = vi.mocked(api.get).getMockImplementation()!;
  let old!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/teacher/class/class-a/students") return new Promise((resolve) => { old = resolve; });
    if (path === "/teacher/class/class-b/students") return response([{ student_id: "new", student_name: "Güncel öğrenci", parent_id: "parent", parent_name: "Veli", is_primary: true }]);
    return normal(path, config);
  });
  render(<TeacherPortalPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Mesajlar" }));
  fireEvent.click(screen.getByRole("button", { name: "Sınıf A 2 öğrenci" }));
  fireEvent.click(screen.getByRole("button", { name: "Sınıf B 2 öğrenci" }));
  await screen.findByText("Güncel öğrenci");
  await act(async () => old(response([{ student_id: "old", student_name: "Eski öğrenci", parent_id: "parent", parent_name: "Veli" }])));
  expect(screen.queryByText("Eski öğrenci")).not.toBeInTheDocument();
});

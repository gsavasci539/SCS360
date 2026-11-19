import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("finans izni olmayan velinin panosu finans isteği yapmaz ve ödeme kartı göstermez", async () => {
  useAuthStore.setState({ user: { id: "parent", organization_id: "school", email: "parent@test.invalid", first_name: "Veli", last_name: "Test",
    is_super_admin: false, roles: [], branch_ids: [], permissions: ["parent.view_children"] } });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data:
    path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz", last_name: "Test" }]
      : String(path).endsWith("/insights") ? { title: "Kayıt özeti", metrics: [{ label: "Not ortalaması", value: "Henüz değerlendirme kaydı yok" }] }
      : String(path).endsWith("/timeline") ? { events: [] } : {} } }));
  render(<MemoryRouter><ParentPortalPage view="dashboard" /></MemoryRouter>);
  await screen.findByText("Henüz değerlendirme kaydı yok", { exact: false });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/parent/child/child/insights", expect.anything()));
  expect(vi.mocked(api.get).mock.calls.some(([path]) => String(path).includes("financial-invoices"))).toBe(false);
  expect(screen.queryByText("Kalan Ödeme")).not.toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("çocuk değiştiğinde yalnız yeni çocuğun karne etkinliklerini gösterir", async () => {
  let finishOldChild!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/parent/my-children") return { data: { data: [
      { student_id: "child-1", first_name: "Deniz", last_name: "Test" },
      { student_id: "child-2", first_name: "Ada", last_name: "Test" },
    ] } };
    if (path === "/parent/child/child-1/today-status") return new Promise((resolve) => { finishOldChild = resolve; });
    if (path === "/parent/child/child-2/today-status") return { data: { data: { student_id: "child-2", date: "2026-11-03",
      daily_report: { activities: ["Kitap okuma", "Çizim"], teacher_notes: "Yeni çocuğun karne notu" } } } };
    if (path === "/parent/child/child-2/timeline") return { data: { data: { student_id: "child-2", date: "2026-11-03", events: [] } } };
    return { data: { data: null } };
  });
  render(<MemoryRouter><ParentPortalPage view="children" /></MemoryRouter>);
  const picker = await screen.findByRole("combobox", { name: "Öğrenci Seçin" });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/parent/child/child-1/today-status", expect.anything()));
  const oldRequest = vi.mocked(api.get).mock.calls.find(([path]) => path === "/parent/child/child-1/today-status")?.[1];
  fireEvent.change(picker, { target: { value: "child-2" } });
  expect(await screen.findByText("Kitap okuma, Çizim")).toBeInTheDocument();
  expect(oldRequest?.signal?.aborted).toBe(true);
  await act(async () => { finishOldChild({ data: { data: { student_id: "child-1", date: "2026-11-03",
    daily_report: { teacher_notes: "Eski çocuğun karne notu" } } } }); });
  expect(screen.queryByText("Eski çocuğun karne notu")).not.toBeInTheDocument();
  expect(screen.getByText("Yeni çocuğun karne notu")).toBeInTheDocument();
});

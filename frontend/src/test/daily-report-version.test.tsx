import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DailyReportsDetailPage, DailyReportsPage } from "../features/academic/DailyReportsPage";
import { getAnalysis } from "../lib/analysis";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

const { showToast } = vi.hoisted(() => ({ showToast: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, apiMessage: (error: Error) => error.message }));
vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn(async () => null) }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast }) }));

const version = "b".repeat(64);
const row = { id: "report", version, student_name: "Ada Test", date: "2026-11-19", meal_status: "Kahvaltı: Tümünü Yedi",
  mood: "Sakin", sleep_status: "30 dk", teacher_notes: "İlk not" };
const user = { id: "teacher", organization_id: "school", first_name: "Ada", last_name: "Test",
  email: "test@example.invalid", permissions: ["daily_reports.read", "daily_reports.write"], roles: [], branch_ids: [], is_super_admin: false };

beforeEach(() => {
  useAuthStore.getState().setUser(user);
  vi.mocked(api.get).mockResolvedValue({ data: { data: row } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.restoreAllMocks(); vi.clearAllMocks(); });

function openReport() {
  return render(<MemoryRouter initialEntries={["/daily-reports/report"]}><Routes>
    <Route path="/daily-reports/:id" element={<DailyReportsDetailPage />} />
  </Routes></MemoryRouter>);
}

it("preserves recorded native observations and the open draft when a conditional update is rejected", async () => {
  vi.mocked(api.put).mockRejectedValue(new Error("Günlük karne değişti."));
  openReport();
  fireEvent.click(await screen.findByRole("button", { name: "Düzenle" }));
  const editor = within(screen.getByRole("dialog"));
  const note = editor.getByLabelText("Öğretmen Notları");
  fireEvent.change(note, { target: { value: "Web taslağı" } });
  fireEvent.click(editor.getByRole("button", { name: "Kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/daily-reports/report", {
    teacher_notes: "Web taslağı", meal_status: row.meal_status, mood: row.mood, sleep_status: row.sleep_status,
  }, { headers: { "If-Match": `"${version}"` } }));
  expect(note).toHaveValue("Web taslağı");
});

it("uses the displayed version for confirmed deletion", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.mocked(api.delete).mockRejectedValue(new Error("Günlük karne değişti."));
  openReport();
  fireEvent.click(await screen.findByRole("button", { name: "Sil" }));
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/daily-reports/report", { headers: { "If-Match": `"${version}"` } }));
  expect(screen.getByText("İlk not")).toBeInTheDocument();
});

it.each(["daily_reports.write", "academic.write"])("creates a dated report without list or analysis access for %s", async (permission) => {
  useAuthStore.getState().setUser({ ...user, permissions: [permission] });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/daily-reports/student-options"
    ? { items: [{ id: "server-student", name: "Atanmış öğrenci · KARNE-11" }], total_pages: 1 }
    : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: row } });
  render(<MemoryRouter><DailyReportsPage /></MemoryRouter>);

  expect(screen.getByText("Kayıtlı karneleri görüntüleme yetkiniz yok.")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Yeni karne" }));
  const form = within(screen.getByRole("dialog"));
  await form.findByRole("option", { name: "Atanmış öğrenci · KARNE-11" });
  fireEvent.change(form.getByRole("combobox", { name: /Öğrenci/ }), { target: { value: "server-student" } });
  fireEvent.click(form.getByRole("button", { name: "Oluştur" }));
  await form.findByText("Karne tarihini seçin.");
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.change(form.getByLabelText(/Tarih/), { target: { value: "2026-11-19" } });
  fireEvent.click(form.getByRole("button", { name: "Oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/daily-reports", expect.objectContaining({
    student_id: "server-student", date: "2026-11-19",
  })));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(vi.mocked(api.get).mock.calls.every(([path]) => path === "/daily-reports/student-options")).toBe(true);
  expect(getAnalysis).not.toHaveBeenCalled();
});

it.each(["daily_reports.read", "academic.read"])("keeps %s read-only and applies the analysis permission", async (permission) => {
  useAuthStore.getState().setUser({ ...user, permissions: [permission] });
  vi.mocked(api.get).mockResolvedValue({ data: { data: [row] } });
  render(<MemoryRouter><DailyReportsPage /></MemoryRouter>);

  expect(await screen.findByText("Ada Test")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Yeni karne" })).not.toBeInTheDocument();
  expect(getAnalysis).toHaveBeenCalledTimes(permission === "daily_reports.read" ? 1 : 0);
});

it("shows a recorded zero rate separately from missing observations", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: [] } });
  vi.mocked(getAnalysis).mockResolvedValueOnce({ data: { data: {
    report_stats: { total: 2, mood_rate: 0, mood_observations: 1, sleep_rate: null, sleep_observations: 0,
      meal_rate: 66.7, meal_observations: 3 },
    students_needing_attention: [], recommendations: [],
  } } });
  render(<MemoryRouter><DailyReportsPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "Günlük Karne Analizi" })).toBeInTheDocument();
  expect(screen.getByText("%0")).toBeInTheDocument();
  expect(screen.getAllByText("Gözlem yok")).toHaveLength(1);
  expect(screen.getByText("%66,7")).toBeInTheDocument();
  expect(screen.getByText("3 öğün kaydı")).toBeInTheDocument();
});

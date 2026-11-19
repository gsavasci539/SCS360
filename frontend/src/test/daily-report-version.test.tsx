import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DailyReportsDetailPage } from "../features/academic/DailyReportsPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

const { showToast } = vi.hoisted(() => ({ showToast: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn(), delete: vi.fn() }, apiMessage: (error: Error) => error.message }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast }) }));

const version = "b".repeat(64);
const row = { id: "report", version, student_name: "Ada Test", date: "2026-11-19", meal_status: "Kahvaltı: Tümünü Yedi",
  mood: "Sakin", sleep_status: "30 dk", teacher_notes: "İlk not" };
const user = { id: "teacher", organization_id: "school", first_name: "Ada", last_name: "Test",
  email: "test@example.invalid", permissions: ["daily_reports.write"], roles: [], branch_ids: [], is_super_admin: false };

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

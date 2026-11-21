import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MonthlyAttendanceReport } from "../features/attendance/MonthlyAttendanceReport";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: (error: Error) => error.message }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("aylık yoklama gerçek gün ve sınıf satırlarını gösterir ve tutarsız kapsamı reddeder", async () => {
  let wrongClass = true;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/classes") return { data: { success: true, data: [{ id: "school-class", name: "Yetkili sınıf" }] } };
    const params = config?.params as { year: number; month: number; class_id?: string };
    const date = `${params.year}-${String(params.month).padStart(2, "0")}-12`;
    const active = params.class_id;
    return { data: { success: true, data: { year: params.year, month: params.month, total: 6, class_id: active || null, rows: [{
      date, class_id: active && wrongClass ? "other-class" : "school-class", class_name: "Yetkili sınıf",
      total_students: 6, present: 3, absent: 1, excused: 0, late: 1, half_day: 1,
    }] } } };
  });
  render(<MonthlyAttendanceReport />);
  const row = await screen.findByRole("row", { name: /Yetkili sınıf/ });
  expect(within(row).getByText("50%")).toBeInTheDocument();
  expect(screen.getByText("Kayıt bulunan gün")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Sınıf filtresi"), { target: { value: "school-class" } });
  await screen.findByText("Yoklama raporu doğrulanamadı.");
  expect(screen.queryByRole("row", { name: /Yetkili sınıf/ })).not.toBeInTheDocument();
  wrongClass = false;
  fireEvent.click(screen.getByRole("button", { name: /Tekrar dene|Yeniden dene/i }));
  expect(await screen.findByRole("row", { name: /Yetkili sınıf/ })).toBeInTheDocument();
});

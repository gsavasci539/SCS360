import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { AppointmentsPage } from "../features/communications/AppointmentsPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İşlem tamamlanamadı" }));
const auth = useAuthStore.getState();
afterEach(() => { cleanup(); useAuthStore.setState(auth); vi.resetAllMocks(); });

async function openBooking(loseResponse: boolean) {
  useAuthStore.setState({ can: () => true });
  let saved: Record<string, unknown> | null = null;
  vi.mocked(api.get).mockImplementation(async (url, config) => {
    if (url === "/appointments/options") {
      const student = (config?.params as { student_id?: string } | undefined)?.student_id;
      return { data: { success: true, data: { page: 1, total_pages: 1, items: student
        ? [{ id: "teacher", name: "Kayıtlı öğretmen" }] : [{ id: "student", name: "Kayıtlı öğrenci" }] } } };
    }
    return { data: { success: true, data: url === "/appointments" ? (saved ? [saved] : []) : saved } };
  });
  vi.mocked(api.post).mockImplementation(async (_url, body) => {
    const draft = body as Record<string, unknown>;
    saved = { ...draft, id: draft.request_id, student_name: "Kayıtlı öğrenci", teacher_name: "Kayıtlı öğretmen",
      appointment_date: "2027-01-03", appointment_time: "13:30", status: "CONFIRMED", notes: "" };
    if (loseResponse) throw new Error("Lost response");
    return { data: { success: true, data: { id: draft.request_id } } };
  });
  render(<MemoryRouter><ToastProvider><AppointmentsPage /></ToastProvider></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Yeni randevu" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByRole("button", { name: "Oluştur" })).toBeDisabled();
  await dialog.findByRole("option", { name: "Kayıtlı öğrenci" });
  fireEvent.change(dialog.getByLabelText(/Öğrenci/), { target: { value: "student" } });
  await dialog.findByRole("option", { name: "Kayıtlı öğretmen" });
  fireEvent.change(dialog.getByLabelText(/Öğretmen/), { target: { value: "teacher" } });
  fireEvent.change(dialog.getByLabelText(/Tarih/), { target: { value: "2027-01-03" } });
  fireEvent.change(dialog.getByLabelText(/Saat/), { target: { value: "13:30" } });
  fireEvent.click(dialog.getByRole("button", { name: "Oluştur" }));
  return dialog;
}

it("sends authorized choices and school local time without browser conversion", async () => {
  await openBooking(false);
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/appointments", expect.objectContaining({
    slot_datetime: "2027-01-03T13:30", student_id: "student", teacher_id: "teacher", request_id: expect.any(String),
  }), expect.any(Object)));
  expect(await screen.findByText("Kayıt sunucuda doğrulandı.")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("checks the same booking after a lost response without creating it twice", async () => {
  const dialog = await openBooking(true);
  fireEvent.click(await dialog.findByRole("button", { name: "Sonucu kontrol et" }));
  expect(await screen.findByText("Kayıt sunucuda doğrulandı.")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

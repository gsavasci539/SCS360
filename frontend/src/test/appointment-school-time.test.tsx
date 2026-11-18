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

it("sends the appointment time as entered in school local time without browser conversion", async () => {
  useAuthStore.setState({ can: () => true });
  vi.mocked(api.get).mockResolvedValue({ data: { data: [] } });
  vi.mocked(api.post).mockResolvedValue({ data: { success: true, data: { id: "scheduled" } } });
  render(<MemoryRouter><ToastProvider><AppointmentsPage /></ToastProvider></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Yeni randevu" }));
  const dialog = within(screen.getByRole("dialog"));
  fireEvent.change(dialog.getByLabelText(/Öğrenci/), { target: { value: "student" } });
  fireEvent.change(dialog.getByLabelText(/Öğretmen/), { target: { value: "teacher" } });
  fireEvent.change(dialog.getByLabelText(/Tarih/), { target: { value: "2027-01-03" } });
  fireEvent.change(dialog.getByLabelText(/Saat/), { target: { value: "13:30" } });
  fireEvent.click(dialog.getByRole("button", { name: "Oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/appointments", expect.objectContaining({
    slot_datetime: "2027-01-03T13:30", student_id: "student", teacher_id: "teacher",
  })));
});

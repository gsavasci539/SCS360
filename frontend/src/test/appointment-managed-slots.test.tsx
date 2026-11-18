import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { AppointmentSlotsModal } from "../features/communications/AppointmentSlotsModal";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  apiMessage: () => "Yanıt alınamadı.",
}));

it("recovers a lost create response by readback and verifies the subsequent deletion", async () => {
  let rows: Record<string, unknown>[] = [];
  vi.mocked(api.get).mockImplementation(async () => ({ data: { success: true, data: rows } }));
  vi.mocked(api.post).mockImplementation(async (_path, payload) => {
    rows = [{ ...(payload as object), id: "persisted-slot" }];
    throw new Error("Response lost");
  });
  vi.mocked(api.delete).mockImplementation(async () => {
    rows = [];
    return { data: { success: true } };
  });
  render(<AppointmentSlotsModal teacherId="teacher" onClose={() => undefined} />);
  await screen.findByText("Bu tarihte kayıtlı saat yok.");
  fireEvent.change(screen.getByLabelText("Tarih"), { target: { value: "2027-01-04" } });
  fireEvent.change(screen.getByLabelText("Başlangıç"), { target: { value: "14:00" } });
  fireEvent.change(screen.getByLabelText("Bitiş (15–60 dakika)"), { target: { value: "14:30" } });
  fireEvent.click(screen.getByRole("button", { name: "Saat ekle" }));
  fireEvent.click(await screen.findByRole("button", { name: "Sonucu kontrol et" }));
  await screen.findByText("14:00 – 14:30");
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(api.post).toHaveBeenCalledWith("/appointments/slots", {
    teacher_id: "teacher", date: "2027-01-04", start_time: "14:00", end_time: "14:30", is_available: true,
  }, expect.any(Object));
  fireEvent.click(screen.getByRole("button", { name: "Saati sil" }));
  fireEvent.click(screen.getByRole("button", { name: "Sil" }));
  await screen.findByText("Bu tarihte kayıtlı saat yok.");
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/appointments/slots/persisted-slot", expect.any(Object)));
});

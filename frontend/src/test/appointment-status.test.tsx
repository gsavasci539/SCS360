import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { AppointmentsPage } from "../features/communications/AppointmentsPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), patch: vi.fn() },
  apiMessage: () => "İşlem tamamlanamadı",
}));

const previous = useAuthStore.getState();
afterEach(() => { cleanup(); useAuthStore.setState(previous); vi.resetAllMocks(); });

function open(role: string) {
  useAuthStore.setState({
    can: () => true,
    user: { id: "person", is_super_admin: false, roles: [{ id: role, name: role, slug: role }] } as AuthUser,
  });
  let row = { id: "meeting", student_name: "Öğrenci", status: "PENDING", feedback_notes: "Kayıtlı not" };
  vi.mocked(api.get).mockImplementation(async () => ({ data: { success: true, data: row } }));
  render(<MemoryRouter initialEntries={["/appointments/meeting"]}><ToastProvider><Routes>
    <Route path="/appointments/:id" element={<AppointmentsPage />} />
  </Routes></ToastProvider></MemoryRouter>);
  return (edit: Partial<typeof row>) => { row = { ...row, ...edit }; return row; };
}

it("reads back an approval after a lost response, preserves the note, then verifies explicit note editing", async () => {
  const update = open("teacher");
  vi.mocked(api.patch).mockImplementationOnce(async () => {
    update({ status: "APPROVED" });
    throw new Error("Lost response");
  });
  fireEvent.click(await screen.findByRole("button", { name: "Onayla" }));
  const retry = await screen.findByRole("button", { name: "Sonucu kontrol et" });
  expect(screen.queryByText("Değişiklik sunucuda doğrulandı.")).toBeNull();
  fireEvent.click(retry);
  await screen.findByText("Değişiklik sunucuda doğrulandı.");
  expect(api.patch).toHaveBeenCalledTimes(1);
  expect(api.put).toHaveBeenCalledWith("/appointments/meeting/status", { status: "APPROVED" }, expect.any(Object));
  expect(screen.getByText("Kayıtlı not")).toBeInTheDocument();
  vi.mocked(api.patch).mockImplementationOnce(async () => ({
    data: { success: true, data: update({ feedback_notes: "Güncel öğretmen notu" }) },
  }));
  fireEvent.click(screen.getByRole("button", { name: "Notu düzenle" }));
  fireEvent.change(screen.getByLabelText("Öğretmen notu"), { target: { value: "Güncel öğretmen notu" } });
  fireEvent.click(screen.getByRole("button", { name: "Notu kaydet" }));
  await screen.findByText("Güncel öğretmen notu");
  expect(api.put).toHaveBeenLastCalledWith("/appointments/meeting/status", {
    status: "APPROVED", feedback_notes: "Güncel öğretmen notu",
  }, expect.any(Object));
});

it("shows cancellation as the only parent status action", async () => {
  const update = open("parent");
  vi.mocked(api.patch).mockImplementationOnce(async () => ({
    data: { success: true, data: update({ status: "CANCELLED" }) },
  }));
  fireEvent.click(await screen.findByRole("button", { name: "İptal et" }));
  await screen.findByText("İptal edildi");
  expect(screen.queryByRole("button", { name: /Onayla|Reddet|Notu düzenle/ })).toBeNull();
  expect(api.put).toHaveBeenCalledWith("/appointments/meeting/status", { status: "CANCELLED" }, expect.any(Object));
});

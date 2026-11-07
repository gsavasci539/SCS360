import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { TutoringPage } from "../features/tutoring/TutoringPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, apiMessage: () => "Saat kapasitesi dolu" }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.com", organization_id: "org", is_super_admin: false, roles: [], permissions: ["tutoring.read", "tutoring.write"], branch_ids: [] };
const choices = { students: [{ id: "child", name: "Deniz Kabul" }], teachers: [{ id: "teacher", name: "Test Öğretmen" }], today: "2026-11-03" };
const request = { id: "request", student_id: "child", student_name: "Deniz Kabul", teacher_id: "teacher", subject: "Matematik", requested_date: "2026-11-05", preferred_time_start: "10:00", preferred_time_end: "11:00", status: "PENDING" };
let requests = [request]; let sessions: Record<string, unknown>[] = [];
beforeEach(() => {
  requests = [request]; sessions = []; useAuthStore.setState({ user: manager });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/tutoring/options" ? choices : path === "/tutoring/summary" ? { total_sessions: 214, pending_requests: 45 } : path === "/tutoring/requests" ? requests : path === "/tutoring/sessions" ? sessions : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } }); vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = (entry = "/tutoring") => render(<MemoryRouter initialEntries={[entry]}><ToastProvider><TutoringPage /></ToastProvider></MemoryRouter>);

it("salt okuma yetkisinde gerçek toplamları gösterir ve bütün yazma formlarını gizler", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["tutoring.read"] } }); open();
  expect(await screen.findByLabelText("Etüt özeti")).toHaveTextContent("Toplam ders: 214");
  await screen.findByRole("link", { name: "Deniz Kabul" });
  expect(screen.queryByRole("region", { name: "Etüt işlemleri" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Talebi onayla", hidden: true })).not.toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Talebi reddet Deniz Kabul", hidden: true })).not.toBeInTheDocument();
});

it("müsaitlik ve öğrenci seçiminden önce yazmayı engeller, başarısız ders taslağını korur", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("conflict")); open();
  await screen.findByRole("option", { name: "Deniz Kabul" });
  expect(screen.getByRole("button", { name: "Dersi planla" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Etüt öğrencisi"), { target: { value: "child" } });
  await waitFor(() => expect(screen.getByLabelText("Etüt öğretmeni")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Etüt öğretmeni"), { target: { value: "teacher" } });
  const form = screen.getByRole("form", { name: "Etüt planla" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Dersi planla" })).toBeEnabled());
  fireEvent.change(within(form).getByLabelText("Ders adı"), { target: { value: "Korunacak taslak" } });
  fireEvent.click(within(form).getByRole("button", { name: "Dersi planla" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tutoring/sessions", expect.objectContaining({ student_id: "child", teacher_id: "teacher", subject: "Korunacak taslak", start_time: "09:00", end_time: "10:00" })));
  expect(await screen.findByText("Saat kapasitesi dolu")).toBeInTheDocument();
  expect(within(form).getByLabelText("Ders adı")).toHaveValue("Korunacak taslak");
});

it("talep kararını JSON ile gönderir ve onaylı talepten gerçek ders formunu doldurur", async () => {
  requests = [{ ...request, status: "APPROVED" }]; open();
  const table = screen.getByRole("region", { name: "Ders talepleri" });
  await within(table).findByText("Kaydı aç"); fireEvent.click(within(table).getByText("Kaydı aç"));
  fireEvent.click(within(table).getByRole("button", { name: "Bu talep için ders planla" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Dersi planla" })).toBeEnabled());
  const form = screen.getByRole("form", { name: "Etüt planla" });
  expect(within(form).getByLabelText("Etüt tarihi")).toHaveValue("2026-11-05");
  expect(within(form).getByLabelText("Başlangıç saati")).toHaveValue("10:00");
  fireEvent.click(within(form).getByRole("button", { name: "Dersi planla" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tutoring/sessions", expect.objectContaining({ subject: "Matematik", session_date: "2026-11-05" })));
});

it("ret gerekçesi ve devam puanı doğru kayıt yollarına gider, listeler sayfalanır", async () => {
  sessions = Array.from({ length: 21 }, (_, index) => ({ id: `session${index}`, student_id: "child", student_name: "Deniz Kabul", teacher_id: "teacher", status: "SCHEDULED" })); open();
  const requestsTable = screen.getByRole("region", { name: "Ders talepleri" });
  await within(requestsTable).findByText("Kaydı aç"); fireEvent.click(within(requestsTable).getByText("Kaydı aç"));
  fireEvent.change(within(requestsTable).getByLabelText("Ret gerekçesi"), { target: { value: "Başka tarih seçin" } });
  fireEvent.click(within(requestsTable).getByRole("button", { name: "Talebi reddet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tutoring/requests/request/reject", { rejection_reason: "Başka tarih seçin" }));
  const table = screen.getByRole("region", { name: "Etüt oturumları" }); await within(table).findAllByText("Kaydı aç");
  fireEvent.click(within(table).getAllByText("Kaydı aç")[0]);
  const form = within(table).getAllByRole("form", { name: "Devam kaydı Deniz Kabul" })[0];
  await waitFor(() => expect(within(form).getByRole("button", { name: "Devamı kaydet" })).toBeEnabled());
  fireEvent.change(within(form).getByLabelText("İlerleme puanı"), { target: { value: "87" } });
  fireEvent.click(within(form).getByRole("button", { name: "Devamı kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tutoring/sessions/session0/attendance", expect.objectContaining({ progress_score: "87", attendance_status: "PRESENT" })));
  await waitFor(() => expect(within(table).getByRole("button", { name: "Sonraki" })).toBeEnabled());
  fireEvent.click(within(table).getByRole("button", { name: "Sonraki" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/tutoring/sessions", expect.objectContaining({ params: expect.objectContaining({ limit: 21, offset: 20 }) })));
});

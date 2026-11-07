import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { HealthPage } from "../features/health/HealthPage";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: () => "Sağlık kaydı başarısız" }));
const user: AuthUser = { id: "nurse", first_name: "Clinic", last_name: "User", email: "clinic@example.com", organization_id: "org", is_super_admin: false, roles: [], permissions: ["health.read", "health.write"], branch_ids: [] };
const record = { id: "record", student_id: "child", student_name: "Deniz Kabul", blood_type: "A+", allergies: "Alerji bilgisi", emergency_contact_phone: "05000000000" };
let programStatus = "PENDING";
beforeEach(() => {
  programStatus = "PENDING"; useAuthStore.setState({ user });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/infirmary/options" ? { students: [{ id: "child", name: "Deniz Kabul" }], today: "2026-11-03", time: "10:30" } : path === "/infirmary/summary" ? { total_records: 231, recent_visits: 40 } : path === "/infirmary/health-records" ? [record] : path === "/infirmary/medicine-requests" ? [{ id: "program", student_id: "child", student_name: "Deniz Kabul", medicine_name: "Kabul talimatı", status: programStatus }] : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } }); vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = (entry = "/health") => render(<MemoryRouter initialEntries={[entry]}><ToastProvider><HealthPage /></ToastProvider></MemoryRouter>);

it("salt okuma görünümünde gerçek sağlık alanlarını ve toplamları gösterir, yazma kontrollerini gizler", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["health.read"] } }); open();
  await screen.findByText(/Alerji: Alerji bilgisi/);
  expect(screen.getByLabelText("Revir özeti")).toHaveTextContent("Sağlık dosyası: 231");
  expect(screen.queryByRole("region", { name: "Revir işlemleri" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "İlaç talebini onayla", hidden: true })).not.toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Sağlık dosyaları" })).not.toHaveTextContent("undefined");
});

it("mevcut sağlık dosyasını doldurur, başarısız güncellemede taslağı ve girilmeyen sigorta alanını korur", async () => {
  vi.mocked(api.put).mockRejectedValue(new Error("failed")); open("/health?student=child");
  await screen.findByText(/Alerji: Alerji bilgisi/);
  const form = screen.getByRole("form", { name: "Sağlık dosyasını düzenle" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Sağlık dosyasını kaydet" })).toBeEnabled());
  expect(within(form).getByLabelText("Alerji bilgisi")).toHaveValue("Alerji bilgisi");
  fireEvent.change(within(form).getByLabelText("Alerji bilgisi"), { target: { value: "Korunacak güncelleme" } });
  fireEvent.click(within(form).getByRole("button", { name: "Sağlık dosyasını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/infirmary/health-records/child", expect.objectContaining({ student_id: "child", allergies: "Korunacak güncelleme" })));
  expect(vi.mocked(api.put).mock.calls[0][1]).not.toHaveProperty("insurance_info");
  expect(await screen.findByText("Sağlık kaydı başarısız")).toBeInTheDocument();
  expect(within(form).getByLabelText("Alerji bilgisi")).toHaveValue("Korunacak güncelleme");
});

it("onaylı program için öğrencisine bağlı günlük doz kaydeder", async () => {
  programStatus = "APPROVED"; open();
  const table = screen.getByRole("region", { name: "İlaç programları ve talepler" });
  await within(table).findByText("Kaydı aç"); fireEvent.click(within(table).getByText("Kaydı aç"));
  const form = within(table).getByRole("form", { name: "Doz kaydı Kabul talimatı" });
  fireEvent.change(within(form).getByLabelText("Planlanan doz saati"), { target: { value: "10:00" } });
  fireEvent.change(within(form).getByLabelText("Doz sonucu"), { target: { value: "SKIPPED" } });
  fireEvent.click(within(form).getByRole("button", { name: "Doz sonucunu kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/infirmary/medication/mark-given", expect.objectContaining({ schedule_id: "program", student_id: "child", scheduled_date: "2026-11-03", scheduled_time: "10:00", status: "SKIPPED" })));
  expect(vi.mocked(api.post).mock.calls[0][1]).not.toHaveProperty("given_by");
});

it("onay ve ret gerçek talep yoluna gider, ziyaret ve doz tarihi liste sorgularına uygulanır", async () => {
  open(); const table = screen.getByRole("region", { name: "İlaç programları ve talepler" });
  await within(table).findByText("Kaydı aç"); fireEvent.click(within(table).getByText("Kaydı aç"));
  fireEvent.click(within(table).getByRole("button", { name: "İlaç talebini reddet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/infirmary/medicine-requests/program", { status: "REJECTED" }));
  await waitFor(() => expect(screen.getByLabelText("Ziyaret ve doz günü")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Ziyaret ve doz günü"), { target: { value: "2026-11-02" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/infirmary/medication-logs", expect.objectContaining({ params: expect.objectContaining({ date: "2026-11-02" }) })));
  expect(api.get).toHaveBeenCalledWith("/infirmary/infirmary-visits", expect.objectContaining({ params: expect.objectContaining({ start_date: "2026-11-02", end_date: "2026-11-02" }) }));
});

it("veli ilaç yazma yetkisi olmadan talimat formu göstermez", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["parent.view_children"] } });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/parent/my-children" ? [{ id: "child", student_id: "child", student_name: "Deniz Kabul" }] : path === "/parent/child/child/medicine-requests" ? { medicine_requests: [] } : {} } }));
  render(<MemoryRouter><ToastProvider><ParentPortalPage view="health" /></ToastProvider></MemoryRouter>);
  await screen.findByText("Mevcut Talepler");
  expect(screen.queryByRole("form", { name: "İlaç talimatı gönder" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Talimatı Gönder" })).not.toBeInTheDocument();
});

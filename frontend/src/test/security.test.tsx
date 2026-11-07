import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { SecurityPage } from "../features/security/SecurityPage";
import { api } from "../lib/api";
import { downloadFile } from "../lib/download";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "Güvenlik isteği tamamlanamadı" }));
vi.mock("../lib/download", () => ({ downloadFile: vi.fn() }));
const user: AuthUser = { id: "gate", email: "gate@test.invalid", first_name: "Gate", last_name: "User", organization_id: "org", is_super_admin: false, roles: [], branch_ids: [], permissions: ["security.read", "security.write"] };
const token = { id: "token", student_id: "child", student_name: "Deniz Kabul", token: "credential", barcode_number: "SCS360CODE", status: "ACTIVE", stored_status: "ACTIVE", qr_code_url: "/api/security/digital-ids/token/qr-code" };
let tokens = [token];
beforeEach(() => {
  tokens = [token]; useAuthStore.setState({ user });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/security/options" ? { students: [{ id: "child", name: "Deniz Kabul", active: true }], today: "2026-11-03" } : path === "/security/digital-ids" ? tokens : path === "/security/gate-logs/stats" ? { total_entries: 234, total_exits: 232, currently_in_school: 1 } : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } }); vi.mocked(downloadFile).mockResolvedValue(undefined);
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = () => render(<MemoryRouter><ToastProvider><SecurityPage /></ToastProvider></MemoryRouter>);

it("salt okuma kullanıcı kimlik oluşturmaz, korumalı QR dosyasını doğru API yolundan indirir", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["security.read"] } }); open();
  const table = screen.getByRole("region", { name: "Öğrenci kimlikleri" }); await within(table).findByText("Kimliği aç");
  expect(screen.queryByRole("region", { name: "Güvenlik işlemleri" })).not.toBeInTheDocument();
  fireEvent.click(within(table).getByText("Kimliği aç")); fireEvent.click(within(table).getByRole("button", { name: "QR kodunu indir" }));
  await waitFor(() => expect(downloadFile).toHaveBeenCalledWith("/security/digital-ids/token/qr-code", "SCS360-kimlik-child.svg"));
  expect(api.post).not.toHaveBeenCalled(); expect(api.get).not.toHaveBeenCalledWith("/students");
  expect(screen.getByLabelText("Kapı özeti")).toHaveTextContent("234");
});

it("başarısız kimlik oluşturma tekrarı aynı istek UUID'sini ve süreyi korur", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")); open();
  await screen.findByRole("option", { name: "Deniz Kabul" });
  expect(screen.getByRole("button", { name: "Öğrenci kimliğini oluştur" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Kimlik öğrencisi"), { target: { value: "child" } });
  const form = screen.getByRole("form", { name: "Öğrenci kimliği oluştur" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Öğrenci kimliğini oluştur" })).toBeEnabled());
  fireEvent.change(within(form).getByLabelText("Geçerlilik süresi (saat)"), { target: { value: "8" } });
  fireEvent.click(within(form).getByRole("button", { name: "Öğrenci kimliğini oluştur" }));
  await screen.findByText("Güvenlik isteği tamamlanamadı");
  fireEvent.click(within(form).getByRole("button", { name: "Öğrenci kimliğini oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(vi.mocked(api.post).mock.calls[1]);
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual(expect.objectContaining({ student_id: "child", expires_hours: 8, request_id: expect.any(String) }));
});

it("eşleşmeyen kodu görünür ret olarak gösterir ve girilen kodu korur", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { data: { authorized: false, message: "Kimlik eşleşmedi" } } }); open();
  const form = screen.getByRole("form", { name: "Kapı geçişi kaydet" });
  fireEvent.change(within(form).getByLabelText("QR / barkod değeri"), { target: { value: "unknown-code" } });
  fireEvent.click(within(form).getByRole("button", { name: "Kodu doğrula ve geçişi kaydet" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Kimlik eşleşmedi");
  expect(within(form).getByLabelText("QR / barkod değeri")).toHaveValue("unknown-code");
  const body = vi.mocked(api.post).mock.calls[0][1];
  expect(body).toEqual(expect.objectContaining({ token: "unknown-code", direction: "IN", verification_method: "QR", request_id: expect.any(String) }));
  expect(body).not.toHaveProperty("verified_by"); expect(body).not.toHaveProperty("parent_pickup_permission");
});

it("kimlik iptali, tarih süzmesi ve sonraki kimlik sayfası gerçek adresleri kullanır", async () => {
  tokens = Array.from({ length: 21 }, (_, index) => ({ ...token, id: `token${index}` })); open();
  const table = screen.getByRole("region", { name: "Öğrenci kimlikleri" }); await within(table).findAllByText("Kimliği aç");
  fireEvent.click(within(table).getAllByText("Kimliği aç")[0]); fireEvent.click(within(table).getAllByRole("button", { name: "Kimliği iptal et", hidden: true })[0]);
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/security/digital-ids/token0/revoke"));
  await waitFor(() => expect(screen.getByLabelText("Kapı kaydı günü")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Kapı kaydı günü"), { target: { value: "2026-11-02" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/security/gate-logs", expect.objectContaining({ params: expect.objectContaining({ start_date: "2026-11-02", end_date: "2026-11-02" }) })));
  const pager = within(screen.getByLabelText("Kimlik sayfaları")); await waitFor(() => expect(pager.getByRole("button", { name: "Sonraki" })).toBeEnabled());
  fireEvent.click(pager.getByRole("button", { name: "Sonraki" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/security/digital-ids", expect.objectContaining({ params: expect.objectContaining({ offset: 20, limit: 21 }) })));
});

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { PayrollPage } from "../features/payroll/PayrollPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "Kayıt kaydedilemedi" }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.com", organization_id: "org", is_super_admin: false, roles: [], permissions: ["payroll.read", "payroll.write"], branch_ids: [] };
beforeEach(() => {
  useAuthStore.setState({ user: manager });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/payroll/options" ? { staff: [{ id: "teacher", name: "Test Öğretmen", organization_name: "Okul" }], today: "2026-11-03" } : path === "/payroll/summary" ? { total_payroll: 214, pending_approvals: 5, net_salary_total: 500000, total_timesheets: 400 } : path === "/payroll/records" ? [{ id: "record", staff_id: "teacher", staff_name: "Test Öğretmen", status: "DRAFT", net_salary: 50000 }] : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = () => render(<MemoryRouter><ToastProvider><PayrollPage /></ToastProvider></MemoryRouter>);

it("salt okuma yetkisinde dönem toplamı görünür, oluşturma ve onay düğmeleri gizlidir", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["payroll.read"] } }); open();
  await screen.findByText(/Bordro: 214/);
  expect(screen.queryByRole("region", { name: "Bordro işlemleri" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Bordroyu onayla", hidden: true })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Test Öğretmen" })).toHaveAttribute("href", "/payroll?staff=teacher");
});

it("seçili personel ve dönemde bordro taslağı oluşturur, başarısız kayıt taslağı korur", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("failed")); open();
  await screen.findByRole("option", { name: "Test Öğretmen · Okul" });
  fireEvent.change(screen.getByLabelText("Bordro personeli"), { target: { value: "teacher" } });
  const form = await screen.findByRole("form", { name: "Bordro taslağı oluştur" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Bordro taslağını kaydet" })).toBeEnabled());
  fireEvent.change(within(form).getByLabelText("Temel tutar"), { target: { value: "50000.25" } });
  fireEvent.click(within(form).getByRole("button", { name: "Bordro taslağını kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/payroll/records", expect.objectContaining({ staff_id: "teacher", year: 2026, month: 11, period: "MONTHLY", base_salary: "50000.25" })));
  expect(await screen.findByText("Kayıt kaydedilemedi")).toBeInTheDocument();
  expect(within(form).getByLabelText("Temel tutar")).toHaveValue(50000.25);
});

it("onay işlemi gerçek kayıt yolunu kullanır ve üç aylık aralık yıl sınırını geçer", async () => {
  open(); const region = await screen.findByRole("region", { name: "Bordro kayıtları" });
  await within(region).findByText("Kaydı aç"); fireEvent.click(within(region).getByText("Kaydı aç"));
  fireEvent.click(within(region).getByRole("button", { name: "Bordroyu onayla" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/payroll/records/record/approve"));
  await waitFor(() => expect(screen.getByLabelText("Dönem türü")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Dönem türü"), { target: { value: "QUARTERLY" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/payroll/timesheets", expect.objectContaining({ params: expect.objectContaining({ start_date: "2026-11-01", end_date: "2027-01-31" }) })));
});

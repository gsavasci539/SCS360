import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { PlatformPage } from "../features/saas/PlatformPage";
import { SubscriptionPage } from "../features/saas/SubscriptionPage";
import { api } from "../lib/api";
import { getHomePath } from "../lib/home";
import { useAuthStore } from "../stores/auth";
import type { AuthUser, OrganizationAccess } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
const access: OrganizationAccess = { status: "PAST_DUE", restricted: true, billing_path: "/subscription", warning: "Üyeliğinizi yenileyin", period_end: "2026-10-01T10:00:00Z", grace_end: "2026-10-11T10:00:00Z", days_remaining: 0 };
const user: AuthUser = { id: "owner", email: "owner@example.com", first_name: "Okul", last_name: "Sahibi", is_super_admin: false, organization_id: "school", roles: [{ id: "owner-role", name: "Sahip", slug: "owner" }], branch_ids: [], permissions: ["users.read"], organization_access: access };
const plan = { id: "plan", code: "SMALL", name: "Okul Paketi", price: "1200.50", currency: "TRY", branch_limit: 2, student_limit: 50, user_limit: 10, period_months: 1, is_active: true };
const tenant = { id: "school", name: "Kabul Okulu", is_active: true, access, package: plan, usage: { branch_limit: 1, student_limit: 4, user_limit: 2 }, owner_user_id: "owner", period_start: "2026-09-01T10:00:00Z" };
beforeEach(() => {
  useAuthStore.setState({ user, accessToken: "access", refreshToken: "refresh" });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/subscription/access" ? { access, can_manage: true, package: plan, usage: tenant.usage, online_payment_available: false }
    : path === "/subscription/plans" || path === "/platform/plans" ? [plan] : path === "/platform/tenants" ? [tenant]
    : path === "/platform/tenants/school/users" ? [{ id: "owner", name: "Okul Sahibi", email: user.email }] : path === "/platform/summary" ? { total_institutions: 1 } : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } }); vi.mocked(api.put).mockResolvedValue({ data: { data: {} } }); vi.mocked(api.patch).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = (page: "platform" | "subscription") => render(<MemoryRouter><ToastProvider>{page === "platform" ? <PlatformPage /> : <SubscriptionPage />}</ToastProvider></MemoryRouter>);

it("öğretmen ve veli ödeme ekranında kurum faturalarını veya fiyatlarını istemez", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { access, can_manage: false } } }); open("subscription");
  expect(await screen.findByText(/okul veya kurum sahibinizle iletişime/)).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledTimes(1); expect(screen.queryByLabelText("Yenileme paketi")).not.toBeInTheDocument();
  expect(getHomePath(user)).toBe("/subscription");
});

it("yenileme zaman aşımından sonra aynı istek kimliğiyle tekrar edilir, fiyat istemciden gönderilmez", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")); open("subscription");
  await screen.findByRole("option", { name: /Okul Paketi/ });
  await waitFor(() => expect(screen.getByRole("button", { name: "Yenileme talebi oluştur" })).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Yenileme paketi"), { target: { value: "plan" } });
  fireEvent.click(screen.getByRole("button", { name: "Yenileme talebi oluştur" }));
  await screen.findByText("İstek tamamlanamadı"); fireEvent.click(screen.getByRole("button", { name: "Yenileme talebi oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(vi.mocked(api.post).mock.calls[1]);
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual({ plan_id: "plan", request_id: expect.any(String) });
  expect(screen.queryByRole("button", { name: "Ödemeye geç" })).not.toBeInTheDocument();
});

it("kurum sahibi seçeneği geç yüklenince mevcut ödeme yetkilisini silmez ve kapatma gerçek API'yi kullanır", async () => {
  const fallback = vi.mocked(api.get).getMockImplementation()!;
  let closed = false;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/platform/tenants" && config?.params && "record_id" in Object(config.params)) {
      return { data: { success: true, data: [{ ...tenant, is_active: !closed, owner_user_id: "older-owner",
        admin_status: closed ? "SUSPENDED" : "ACTIVE", period_end: access.period_end }] } };
    }
    return fallback(path, config);
  });
  vi.mocked(api.put).mockImplementation(async (_path, body) => ({
    data: { success: true, data: { ...(body as Record<string, unknown>), organization_id: tenant.id } },
  }));
  vi.mocked(api.patch).mockImplementation(async () => {
    closed = true;
    return { data: { success: true, data: { id: tenant.id, is_active: false } } };
  });
  useAuthStore.setState({ user: { ...user, is_super_admin: true } }); open("platform");
  await screen.findByText("Kabul Okulu"); fireEvent.click(screen.getByRole("button", { name: "Üyeliği yönet" }));
  await screen.findByRole("option", { name: /Okul Sahibi · owner/ });
  expect(screen.getByLabelText("Ödeme yetkilisi")).toHaveValue("owner");
  const form = screen.getByRole("form", { name: "Kurum üyeliğini düzenle" });
  fireEvent.submit(form); await waitFor(() => expect(api.put).toHaveBeenCalledWith("/platform/tenants/school/subscription", expect.objectContaining({ owner_user_id: "owner", plan_id: "plan" })));
  await screen.findByText("Üyelik güncellenemedi");
  expect(screen.getByLabelText("Ödeme yetkilisi")).toHaveValue("owner");
  await waitFor(() => expect(within(form).getByRole("button", { name: "Üyeliği kaydet" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Kurum hesabını kapat" }));
  await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/platform/tenants/school/status", { is_active: false }));
  await screen.findByText("Kurum hesabı kapatıldı");
  expect(api.get).toHaveBeenCalledWith("/platform/tenants", { params: { record_id: "school", limit: 1 } });
});

it("paket fiyatı ve limitleri kalıcı katalogda eşleşene kadar formu korur", async () => {
  const fallback = vi.mocked(api.get).getMockImplementation()!;
  const written = { ...plan, id: "new-plan", code: "DENE", name: "Girilen paket", price: "12.34" };
  let reads = 0;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/platform/plans" && !config) {
      reads++;
      return { data: { success: true, data: [reads === 1 ? { ...written, student_limit: 1 } : written] } };
    }
    return fallback(path, config);
  });
  vi.mocked(api.post).mockResolvedValue({ data: { success: true, data: written } });
  useAuthStore.setState({ user: { ...user, is_super_admin: true } }); open("platform");
  await screen.findByText("Kabul Okulu");
  const form = screen.getByRole("form", { name: "Paket yönetimi" });
  const edit = (label: RegExp, value: string) => fireEvent.change(within(form).getByLabelText(label), { target: { value } });
  edit(/^Paket kodu$/, "dene"); edit(/^Paket adı$/, "Girilen paket"); edit(/^Paket fiyatı$/, "12.34");
  edit(/^Şube sınırı$/, "2"); edit(/^Öğrenci sınırı$/, "50"); edit(/^Kullanıcı sınırı$/, "10");
  fireEvent.submit(form);
  await screen.findByText("Paket kaydedilemedi");
  expect(within(form).getByLabelText("Paket fiyatı")).toHaveValue(12.34);
  fireEvent.submit(form);
  await screen.findByText("Paket kaydedildi");
  expect(reads).toBe(2);
});

it("üyelik durumunu yalnız faturanın ve aynı ödeme oturumunun geri okumasıyla günceller", async () => {
  const initial = { id: "invoice", organization_id: user.organization_id, plan_id: plan.id, package_name: plan.name,
    amount: "1200.50", currency: "TRY", status: "PENDING", checkout_status: "PENDING", checkout_id: "checkout", can_cancel: false };
  const paid = { ...initial, status: "PAID", checkout_status: "PAID" };
  const fallback = vi.mocked(api.get).getMockImplementation()!;
  let reads = 0;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path !== "/subscription/invoices") return fallback(path, config);
    const params: unknown = config?.params;
    if (!params || typeof params !== "object" || !("record_id" in params)) {
      return { data: { data: [reads > 1 ? paid : initial] } };
    }
    reads++;
    return { data: { success: true, data: [reads === 1 ? { ...paid, checkout_id: "older-checkout" } : paid] } };
  });
  vi.mocked(api.post).mockResolvedValue({ data: { success: true, data: { invoice: paid, status: "PAID", checkout_id: "checkout" } } });
  open("subscription");
  fireEvent.click(await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  await screen.findByText("İstek tamamlanamadı");
  expect(screen.queryByText("Üyelik ödemesi tamamlandı")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  await screen.findByText("Üyelik ödemesi tamamlandı");
  expect(api.post).toHaveBeenCalledWith("/subscription/invoices/invoice/payment-status");
  expect(api.get).toHaveBeenCalledWith("/subscription/invoices", { params: { record_id: "invoice", limit: 1 } });
});

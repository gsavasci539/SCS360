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
  useAuthStore.setState({ user: { ...user, is_super_admin: true } }); open("platform");
  await screen.findByText("Kabul Okulu"); fireEvent.click(screen.getByRole("button", { name: "Üyeliği yönet" }));
  await screen.findByRole("option", { name: /Okul Sahibi · owner/ });
  expect(screen.getByLabelText("Ödeme yetkilisi")).toHaveValue("owner");
  const form = screen.getByRole("form", { name: "Kurum üyeliğini düzenle" });
  fireEvent.submit(form); await waitFor(() => expect(api.put).toHaveBeenCalledWith("/platform/tenants/school/subscription", expect.objectContaining({ owner_user_id: "owner", plan_id: "plan" })));
  await waitFor(() => expect(within(form).getByRole("button", { name: "Üyeliği kaydet" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Kurum hesabını kapat" }));
  await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/platform/tenants/school/status", { is_active: false }));
});

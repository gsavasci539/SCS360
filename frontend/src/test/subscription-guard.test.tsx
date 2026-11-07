import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { SubscriptionGuard } from "../routes/SubscriptionGuard";
import { useAuthStore } from "../stores/auth";
import { subscriptionAccessFromError } from "../lib/subscription";
import type { AuthUser, OrganizationAccess } from "../types/api";

const access: OrganizationAccess = { status: "PAST_DUE", restricted: true, warning: "Üyelik süresi doldu", period_end: "2026-11-03T00:00:00Z", grace_end: "2026-11-13T00:00:00Z", days_remaining: 0, billing_path: "/subscription" };
const user: AuthUser = { id: "owner", email: "owner@example.com", first_name: "School", last_name: "Owner", organization_id: "org", is_super_admin: false, roles: [], permissions: ["users.read"], branch_ids: [], organization_access: access };
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); });
function open(value: AuthUser) {
  useAuthStore.setState({ user: value });
  render(<MemoryRouter initialEntries={["/users"]}><Routes><Route element={<SubscriptionGuard />}><Route path="/users" element={<p>İş verileri</p>} /></Route><Route path="/subscription" element={<p>Üyelik ödemesi</p>} /></Routes></MemoryRouter>);
}

it("süresi geçmiş kurum, kaynak yetkisi olsa bile üyelik ekranına gider", () => {
  open(user); expect(screen.getByText("Üyelik ödemesi")).toBeInTheDocument(); expect(screen.queryByText("İş verileri")).not.toBeInTheDocument();
});
it("ek süre içindeki kurum ve ana yönetici çalışma alanına erişir", () => {
  open({ ...user, organization_access: { ...access, status: "GRACE", restricted: false } });
  expect(screen.getByText("İş verileri")).toBeInTheDocument(); cleanup();
  open({ ...user, is_super_admin: true }); expect(screen.getByText("İş verileri")).toBeInTheDocument();
});
it("API hatasından yalnız doğrulanmış üyelik durumunu okur ve dış yönlendirme kabul etmez", () => {
  expect(subscriptionAccessFromError({ errors: [{ code: "SUBSCRIPTION_REQUIRED", access }] })).toEqual(access);
  expect(subscriptionAccessFromError({ errors: [{ code: "SUBSCRIPTION_REQUIRED", access: { ...access, billing_path: "https://other.example.com" } }] })).toBeNull();
  expect(subscriptionAccessFromError({ errors: [{ code: "SUBSCRIPTION_REQUIRED", access: { ...access, days_remaining: NaN } }] })).toBeNull();
});

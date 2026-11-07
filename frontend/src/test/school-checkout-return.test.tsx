import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PaymentPage } from "../features/payment/PaymentPage";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
const debtId = "00000000-0000-4000-8000-000000000001", checkoutId = "00000000-0000-4000-8000-000000000002";
const metadata = { conversation_id: checkoutId, debt_id: debtId, amount: "25.00", status: "FRAUD_REVIEW", can_resume: false, can_refresh: true };
beforeEach(() => {
  useAuthStore.setState({ user: { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "actor@example.invalid", is_super_admin: false, roles: [], permissions: ["parent.view_children", "parent.view_finances", "parent.make_payment", "finance.write"], branch_ids: [] }, sessionVersion: 1 });
  usePlatformWorkspace.setState({ workspace: null }); sessionStorage.clear();
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).includes("/checkouts/") ? metadata
    : path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz", last_name: "Test" }]
      : String(path).endsWith("/financial-invoices") ? { invoices: [{ debt_id: debtId, remaining_amount: "25.00", amount: "25.00", status: "UNPAID", debt_type: "EDUCATION" }], online_payment_available: true }
        : String(path).endsWith("/insights") ? { recommendations: [] } : {} } }));
});
afterEach(() => { cleanup(); vi.resetAllMocks(); sessionStorage.clear(); });

it("a staff callback query reads its checkout and never trusts URL success or starts a new payment", async () => {
  render(<MemoryRouter initialEntries={[`/payment?checkout=${checkoutId}&success=true`]}><Routes><Route path="/payment" element={<PaymentPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText(/Ödeme incelemede/)).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith(`/payments/iyzico/checkouts/${checkoutId}`, expect.anything());
  expect(api.post).not.toHaveBeenCalled(); expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.queryByText("Ödemeniz doğrulandı ve borcunuza işlendi.")).not.toBeInTheDocument();
});

it("a parent callback uses only the parent-purpose status and refresh routes", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { data: { ...metadata, status: "PAID_REVIEW", can_resume: false } } });
  render(<MemoryRouter initialEntries={[`/parent/finances?checkout=${checkoutId}`]}><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  expect(await screen.findByText(/Ödeme alınmış, kayıt uzlaştırması bekleniyor/)).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith(`/parent/payments/checkouts/${checkoutId}/refresh`, {}, expect.anything());
  expect(vi.mocked(api.get).mock.calls.some(([path]) => String(path).includes("/payments/iyzico/"))).toBe(false);
});

it("the real parent invoice modal initializes with the persisted nonce and hides payment entry when permission is absent", async () => {
  vi.mocked(api.post).mockImplementation(async (_path, body) => ({ data: { data: { ...metadata,
    conversation_id: (body as { request_id: string }).request_id, status: "PENDING", can_resume: true,
    checkout_url: "https://sandbox-api.iyzipay.com/checkoutform/test" } } }));
  const view = render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Öde" }));
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/parent/payments/initialize", expect.objectContaining({ debt_id: debtId, amount: "25.00", request_id: expect.any(String) }), expect.anything()));
  view.unmount(); useAuthStore.setState({ user: { ...useAuthStore.getState().user!, permissions: ["parent.view_children", "parent.view_finances"] } });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  await screen.findByText("Ödenmedi", { exact: true }); expect(screen.queryByRole("button", { name: "Öde" })).not.toBeInTheDocument();
});

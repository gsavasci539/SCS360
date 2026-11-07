import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PaymentPage } from "../features/payment/PaymentPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
beforeEach(() => { useAuthStore.setState({ user: { id: "staff", organization_id: "school", first_name: "Test", last_name: "User", email: "staff@example.invalid", is_super_admin: false, roles: [], permissions: ["finance.write"], branch_ids: [] }, sessionVersion: 1 }); usePlatformWorkspace.setState({ workspace: null }); sessionStorage.clear(); });
afterEach(() => { cleanup(); vi.resetAllMocks(); sessionStorage.clear(); });
const debtId = "00000000-0000-4000-8000-000000000001";
const debt = { id: debtId, remaining_amount: "250.00", status: "UNPAID", online_payment_available: true };
function open() { render(<MemoryRouter initialEntries={[`/payment/${debtId}/0.01`]}><Routes><Route path="/payment/:debtId/:amount" element={<PaymentPage />} /></Routes></MemoryRouter>); }

it("URL tutarı yerine sunucudaki borcu gösterir ve kullanıcı istemeden ödeme açmaz", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).includes("/checkouts/")
    ? { conversation_id: String(path).split("/").at(-1), debt_id: debtId, amount: "250.00", status: "PENDING", can_resume: true, can_refresh: true } : debt } }));
  vi.mocked(api.post).mockImplementation(async (_path, body) => ({ data: { data: { checkout_url: "https://sandbox-api.iyzipay.com/checkoutform/test",
    conversation_id: (body as { request_id: string }).request_id, debt_id: debtId, amount: "250.00", status: "PENDING", can_resume: true, can_refresh: true } } }));
  open(); await screen.findByText(/Güncel kalan tutar/); expect(api.post).not.toHaveBeenCalled();
  const form = screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" });
  fireEvent.submit(form); await screen.findByRole("link", { name: "Güvenli ödeme sayfasını aç" });
  expect(api.post).toHaveBeenCalledWith("/payments/iyzico/initialize", expect.objectContaining({ debt_id: debtId, amount: "250.00", request_id: expect.any(String) }), expect.anything());
  expect(screen.queryByText(/Ödemeniz doğrulandı/)).not.toBeInTheDocument();
  const checkoutId = (vi.mocked(api.post).mock.calls[0][1] as { request_id: string }).request_id;
  vi.mocked(api.post).mockResolvedValue({ data: { data: { conversation_id: checkoutId, debt_id: debtId, amount: "250.00", status: "COMPLETED", can_resume: false, can_refresh: false } } });
  fireEvent.click(screen.getByRole("button", { name: "Ödeme sonucunu kontrol et" })); await screen.findByText("Ödemeniz doğrulandı ve borcunuza işlendi.");
  expect(api.post).toHaveBeenLastCalledWith(`/payments/iyzico/checkouts/${checkoutId}/refresh`, {}, expect.anything());
});

it("kurum sağlayıcısı açık değilse kart tahsilatı formu ve istek göndermez", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...debt, online_payment_available: false } } }); open();
  await screen.findByText(/Bu kurumda yeni online ödeme açık değil/); expect(screen.queryByRole("form")).not.toBeInTheDocument();
  await waitFor(() => expect(api.post).not.toHaveBeenCalled());
});

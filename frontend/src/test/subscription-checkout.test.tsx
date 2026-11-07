import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SubscriptionCheckout, subscriptionPaymentUrl } from "../features/saas/SubscriptionCheckout";
import { PaymentReview } from "../features/saas/PaymentReview";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { post: vi.fn() }, apiMessage: () => "Ödeme isteği tamamlanamadı" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const invoice = { id: "invoice", package_name: "Okul", amount: "100.00", currency: "TRY", status: "PENDING", can_checkout: true };

it("ödeme bağlantısı yalnız sağlayıcının HTTPS alan adında açılır", () => {
  expect(subscriptionPaymentUrl("https://sandbox-api.iyzipay.com/checkoutform/test")).toBeTruthy();
  for (const value of ["javascript:alert(1)", "https://iyzipay.com.evil.example/test", "https://evil.example/", "http://sandbox-api.iyzipay.com/test", "https://user@sandbox-api.iyzipay.com/test", "https://sandbox-api.iyzipay.com:8443/test", "//sandbox-api.iyzipay.com/test"]) expect(subscriptionPaymentUrl(value)).toBeNull();
});

it("zaman aşımı aynı kimlikle tekrar edilir ve istemci ödeme tutarını belirlemez", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce({ data: { data: { checkout_url: "https://sandbox-api.iyzipay.com/checkoutform/test", status: "PENDING" } } });
  render(<SubscriptionCheckout invoice={invoice} onClose={vi.fn()} onRefresh={vi.fn()} />);
  for (const [label, value] of [["Kimlik veya vergi numarası", "11111111111"], ["Telefon", "+905000000000"], ["Fatura adresi", "Test adresi"], ["Şehir", "Istanbul"], ["Ülke", "Turkey"]]) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  const form = screen.getByRole("form", { name: "Üyelik ödeme bilgileri" });
  fireEvent.submit(form); await screen.findByRole("alert");
  await waitFor(() => expect(screen.getByRole("button", { name: "Ödeme sayfasını hazırla" })).toBeEnabled());
  fireEvent.submit(form);
  expect(await screen.findByRole("link", { name: "Güvenli ödeme sayfasını aç" })).toHaveAttribute("href", "https://sandbox-api.iyzipay.com/checkoutform/test");
  const calls = vi.mocked(api.post).mock.calls;
  expect(calls[0]).toEqual(calls[1]); expect(calls[0][1]).not.toHaveProperty("amount"); expect(calls[0][1]).not.toHaveProperty("plan_id");
  expect(screen.queryByLabelText(/kart numarası/i)).not.toBeInTheDocument();
});

it("mevcut ödeme yeni tahsilat açmadan devam eder ve güvensiz bağlantıyı reddeder", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { data: { checkout_url: "https://evil.example/pay" } } });
  render(<SubscriptionCheckout invoice={{ ...invoice, can_resume: true }} onClose={vi.fn()} onRefresh={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Mevcut ödeme sayfasını getir" }));
  await screen.findByRole("alert"); expect(api.post).toHaveBeenCalledWith("/subscription/invoices/invoice/resume", undefined);
  expect(screen.queryByRole("link")).not.toBeInTheDocument(); expect(screen.queryByRole("form")).not.toBeInTheDocument();
});

it("Root iade kaydında ödeme göndermez ve zaman aşımı sonrası aynı uzlaştırmayı tekrarlar", async () => {
  const done = vi.fn(); vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce({ data: { data: {} } });
  render(<PaymentReview invoice={{ ...invoice, provider_paid_amount: "100.00", provider_currency: "TRY" }} onDone={done} onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Uzlaştırma işlemi"), { target: { value: "REFUND_RECORDED" } });
  fireEvent.change(screen.getByLabelText("Doğrulanan iade referansı"), { target: { value: "CHECKED-EXTERNAL-REFUND" } });
  fireEvent.change(screen.getByLabelText("Kontrol açıklaması"), { target: { value: "Banka panelinde doğrulandı" } });
  fireEvent.click(screen.getByRole("button", { name: "Uzlaştırmayı kaydet" })); await screen.findByRole("alert");
  await waitFor(() => expect(screen.getByRole("button", { name: "Uzlaştırmayı kaydet" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Uzlaştırmayı kaydet" })); await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(vi.mocked(api.post).mock.calls[1]);
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(["/platform/invoices/invoice/review", expect.objectContaining({ action: "REFUND_RECORDED", refund_reference: "CHECKED-EXTERNAL-REFUND" })]);
});

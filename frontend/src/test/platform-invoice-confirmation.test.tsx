import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PaymentReview } from "../features/saas/PaymentReview";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: (failure: Error) => failure.message }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("uzlaştırılan satır yeniden okunmadan formu kapatmaz ve aynı işlem kimliğini korur", async () => {
  const invoice = { id: "invoice", organization_id: "school", amount: "12.00",
    currency: "TRY", status: "PAID_REVIEW", checkout_status: "PAID_REVIEW" };
  const accepted = { ...invoice, status: "REFUNDED", checkout_status: "REFUNDED" };
  vi.mocked(api.post).mockResolvedValue({ data: { success: true, data: accepted } });
  vi.mocked(api.get).mockResolvedValueOnce({ data: { success: true, data: [invoice] } })
    .mockResolvedValueOnce({ data: { success: true, data: [accepted] } });
  const completed = vi.fn();
  render(<PaymentReview invoice={invoice} onDone={completed} onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Uzlaştırma işlemi"), { target: { value: "REFUND_RECORDED" } });
  fireEvent.change(screen.getByLabelText("Doğrulanan iade referansı"), { target: { value: "TEST-FIXTURE" } });
  fireEvent.change(screen.getByLabelText("Kontrol açıklaması"), { target: { value: "Yalnız izole test açıklaması" } });
  fireEvent.click(screen.getByRole("button", { name: "Uzlaştırmayı kaydet" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Sunucudan okunan üyelik ödeme durumu doğrulanamadı.");
  expect(completed).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Doğrulanan iade referansı")).toHaveValue("TEST-FIXTURE");
  fireEvent.click(screen.getByRole("button", { name: "Uzlaştırmayı kaydet" }));
  await waitFor(() => expect(completed).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual(vi.mocked(api.post).mock.calls[1][1]);
  expect(api.get).toHaveBeenCalledWith("/platform/invoices", { params: { record_id: "invoice", organization_id: "school", limit: 1 } });
});

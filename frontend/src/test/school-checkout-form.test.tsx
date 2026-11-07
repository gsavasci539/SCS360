import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SchoolCheckoutForm } from "../features/payment/SchoolCheckoutForm";
import { checkoutAttemptKey, checkoutScope, readSchoolCheckout } from "../features/payment/schoolCheckoutAttempt";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import { api } from "../lib/api";
import type { AuthUser } from "../types/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: (reason: Error) => reason.message || "İstek tamamlanamadı" }));
const debtId = "00000000-0000-4000-8000-000000000001";
const user: AuthUser = { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "test@example.invalid", is_super_admin: false, roles: [], permissions: ["finance.write", "parent.make_payment"], branch_ids: [] };
const notFound = { response: { status: 404 } };
function fill() {
  fireEvent.change(screen.getByLabelText("Kimlik / pasaport numarası"), { target: { value: "PRIVATE_IDENTITY" } });
  fireEvent.change(screen.getByLabelText("Ödeme telefonu"), { target: { value: "05555555555" } });
  fireEvent.change(screen.getByLabelText("Fatura adresi"), { target: { value: "PRIVATE_ADDRESS" } });
  fireEvent.change(screen.getByLabelText("Şehir"), { target: { value: "Ankara" } });
  fireEvent.change(screen.getByLabelText("Ülke"), { target: { value: "Türkiye" } });
}
beforeEach(() => { useAuthStore.setState({ user, sessionVersion: 1 }); usePlatformWorkspace.setState({ workspace: null }); sessionStorage.clear(); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.resetAllMocks(); sessionStorage.clear(); });

it("persists the request UUID before initialize and sends only the server debt amount", async () => {
  vi.mocked(api.post).mockImplementation(async (_path, body) => {
    const request = body as { request_id: string };
    const saved = readSchoolCheckout(checkoutAttemptKey(checkoutScope(user, null, "staff"), debtId));
    expect(saved.attempt?.request_id).toBe(request.request_id);
    return { data: { data: { conversation_id: request.request_id, debt_id: debtId, amount: "25.00", status: "PENDING", can_resume: true, can_refresh: true,
      checkout_url: "https://sandbox-api.iyzipay.com/checkoutform/test?token=PRIVATE_TOKEN" } } };
  });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: { conversation_id: String(path).split("/").at(-1), debt_id: debtId, amount: "25.00", status: "PENDING", can_resume: true, can_refresh: true } } }));
  render(<SchoolCheckoutForm debtId={debtId} amount="25.00" available />); fill();
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  expect(await screen.findByRole("link", { name: "Güvenli ödeme sayfasını aç" })).toHaveAttribute("href", "https://sandbox-api.iyzipay.com/checkoutform/test?token=PRIVATE_TOKEN");
  expect(api.post).toHaveBeenCalledWith("/payments/iyzico/initialize", expect.objectContaining({ debt_id: debtId, amount: "25.00", request_id: expect.any(String) }), expect.anything());
  expect(JSON.stringify(sessionStorage)).not.toMatch(/PRIVATE|05555555555|Ankara|buyer|checkout_url/);
});

it("after a lost response and reload reads the same checkout without reinitializing or storing billing fields", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("timeout"));
  vi.mocked(api.get).mockRejectedValue(notFound);
  const first = render(<SchoolCheckoutForm purpose="parent" debtId={debtId} amount="25.00" available />); fill();
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  await screen.findByRole("button", { name: "İlk isteği aynı kimlikle tekrar gönder" });
  const body = vi.mocked(api.post).mock.calls[0][1] as { request_id: string }; first.unmount();
  vi.mocked(api.get).mockResolvedValue({ data: { data: { conversation_id: body.request_id, debt_id: debtId, amount: "25.00", status: "INITIALIZING", can_resume: false, can_refresh: true } } });
  render(<SchoolCheckoutForm purpose="parent" debtId={debtId} amount="10.00" available />);
  expect(await screen.findByText(/Ödeme oturumu hazırlanıyor\. Yeni ödeme başlatmadan/)).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledOnce();
  expect(api.get).toHaveBeenLastCalledWith(`/parent/payments/checkouts/${body.request_id}`, expect.anything());
  expect(screen.queryByRole("form")).not.toBeInTheDocument(); expect(JSON.stringify(sessionStorage)).not.toMatch(/PRIVATE|05555555555/);
});

it("a missing server reservation permits billing reentry with the original UUID, never a new one", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("timeout")); vi.mocked(api.get).mockRejectedValue(notFound);
  const first = render(<SchoolCheckoutForm debtId={debtId} amount="25.00" available />); fill();
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  await screen.findByRole("button", { name: "İlk isteği aynı kimlikle tekrar gönder" });
  const originalId = (vi.mocked(api.post).mock.calls[0][1] as { request_id: string }).request_id; first.unmount();
  render(<SchoolCheckoutForm debtId={debtId} amount="25.00" available />);
  await screen.findByRole("form", { name: "Öğrenci ödeme bilgileri" });
  expect(screen.getByLabelText("Kimlik / pasaport numarası")).toHaveValue(""); fill();
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect((vi.mocked(api.post).mock.calls[1][1] as { request_id: string }).request_id).toBe(originalId);
});

it("does not send a provider initialization if durable recovery storage fails", async () => {
  render(<SchoolCheckoutForm debtId={debtId} amount="25.00" available />); fill();
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("denied"); });
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("saklanamadı"); expect(api.post).not.toHaveBeenCalled();
});

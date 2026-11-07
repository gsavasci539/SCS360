import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SchoolCheckoutStatus } from "../features/payment/SchoolCheckoutStatus";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import type { AuthUser } from "../types/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "Sonuç alınamadı" }));
const identifier = "00000000-0000-4000-8000-000000000002";
const user: AuthUser = { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "test@example.invalid", is_super_admin: false, roles: [], permissions: ["finance.read", "finance.write", "parent.make_payment"], branch_ids: [] };
const pending = { conversation_id: identifier, status: "PENDING", can_resume: true, can_refresh: true };
beforeEach(() => { useAuthStore.setState({ user, sessionVersion: 1 }); usePlatformWorkspace.setState({ workspace: null }); });
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("reads stored status without provider calls and explicitly refreshes verified results with POST", async () => {
  const complete = vi.fn(); vi.mocked(api.get).mockResolvedValue({ data: { data: pending } });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { ...pending, status: "COMPLETED", can_refresh: false, can_resume: false } } });
  render(<SchoolCheckoutStatus checkoutId={identifier} onComplete={complete} />);
  await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }); expect(api.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  await waitFor(() => expect(complete).toHaveBeenCalledOnce());
  expect(api.post).toHaveBeenCalledWith(`/payments/iyzico/checkouts/${identifier}/refresh`, {}, expect.objectContaining({ signal: expect.any(AbortSignal) }));
});

it("uses parent-only status resume and refresh paths and does not persist a hosted secret", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: pending } });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { ...pending, checkout_url: "https://sandbox-api.iyzipay.com/checkoutform/test?token=PRIVATE" } } });
  render(<SchoolCheckoutStatus purpose="parent" checkoutId={identifier} />);
  fireEvent.click(await screen.findByRole("button", { name: "Mevcut ödeme sayfasını getir" }));
  expect(await screen.findByRole("link", { name: "Güvenli ödeme sayfasını aç" })).toHaveAttribute("href", "https://sandbox-api.iyzipay.com/checkoutform/test?token=PRIVATE");
  expect(api.get).toHaveBeenCalledWith(`/parent/payments/checkouts/${identifier}`, expect.anything());
  expect(api.post).toHaveBeenCalledWith(`/parent/payments/checkouts/${identifier}/resume`, {}, expect.anything());
  expect(JSON.stringify(sessionStorage)).not.toContain("PRIVATE");
});

it("does not show secret or refresh actions to a read-only finance viewer", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...pending, can_resume: false, can_refresh: false } } });
  render(<SchoolCheckoutStatus checkoutId={identifier} />);
  await screen.findByRole("status"); await waitFor(() => expect(api.get).toHaveBeenCalledOnce());
  expect(screen.queryByRole("button", { name: "Mevcut ödeme sayfasını getir" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Ödeme sonucunu kontrol et" })).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("displays paid review and refunded states without treating them as completed debt posting", async () => {
  const complete = vi.fn(); vi.mocked(api.get).mockResolvedValue({ data: { data: { ...pending, status: "PAID_REVIEW" } } });
  const view = render(<SchoolCheckoutStatus checkoutId={identifier} onComplete={complete} />);
  expect(await screen.findByText(/Ödeme alınmış, kayıt uzlaştırması bekleniyor/)).toBeInTheDocument();
  expect(complete).not.toHaveBeenCalled(); view.unmount();
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...pending, status: "REFUNDED", can_refresh: false, can_resume: false } } });
  render(<SchoolCheckoutStatus checkoutId={identifier} onComplete={complete} />);
  expect(await screen.findByText("Bu ödeme için iade kaydı bulunuyor.")).toBeInTheDocument(); expect(complete).not.toHaveBeenCalled();
});

it("drops late completion after the signed-in actor changes", async () => {
  let resolve!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((done) => { resolve = done; }) as never)
    .mockResolvedValue({ data: { data: { ...pending, can_refresh: false, can_resume: false } } });
  const complete = vi.fn(); render(<SchoolCheckoutStatus checkoutId={identifier} onComplete={complete} />);
  await waitFor(() => expect(api.get).toHaveBeenCalledOnce());
  act(() => { useAuthStore.setState({ user: { ...user, id: "other-actor" }, sessionVersion: 2 }); });
  await act(async () => { resolve({ data: { data: { ...pending, status: "COMPLETED" } } }); });
  expect(complete).not.toHaveBeenCalled(); expect(screen.queryByText("Ödemeniz doğrulandı ve borcunuza işlendi.")).not.toBeInTheDocument();
});

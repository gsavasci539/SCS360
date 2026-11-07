import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { StudentCheckoutStatus } from "../features/payment/StudentCheckoutStatus";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "Sonuç alınamadı" }));
const checkoutId = "00000000-0000-4000-8000-000000000002";
beforeEach(() => { useAuthStore.setState({ user: { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "actor@example.invalid", is_super_admin: false, roles: [], permissions: ["parent.make_payment"], branch_ids: [] }, sessionVersion: 1 }); usePlatformWorkspace.setState({ workspace: null }); });
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("borcun toplam durumuna değil bu ödeme oturumunun sunucu onayına göre tamamlar", async () => {
  const complete = vi.fn(); vi.mocked(api.get).mockResolvedValue({ data: { data: { conversation_id: checkoutId, status: "FRAUD_REVIEW", can_refresh: true, can_resume: false } } });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { conversation_id: checkoutId, status: "COMPLETED", can_refresh: false, can_resume: false } } });
  render(<StudentCheckoutStatus checkoutId={checkoutId} onComplete={complete} />);
  await screen.findByText(/Ödeme incelemede/); expect(complete).not.toHaveBeenCalled();
  expect(vi.mocked(api.get).mock.calls[0][0]).toBe(`/payments/iyzico/checkouts/${checkoutId}`);
  fireEvent.click(screen.getByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  await waitFor(() => expect(complete).toHaveBeenCalledOnce());
});

it("ağ hatasını başarısız tahsilat diye işaretlemez ve manuel kontrol açık kalır", async () => {
  const complete = vi.fn(); vi.mocked(api.get).mockRejectedValue(new Error("timeout"));
  render(<StudentCheckoutStatus checkoutId={checkoutId} onComplete={complete} />); await screen.findByRole("alert");
  expect(screen.getByRole("status")).toHaveTextContent("doğrulanması bekleniyor"); expect(complete).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Kaydı yeniden yükle" })).toBeEnabled(); expect(api.post).not.toHaveBeenCalled();
});

it("veli amacı yalnız veli ödeme sonucu yolunu çağırır", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { conversation_id: checkoutId, status: "PENDING", can_resume: false, can_refresh: true } } });
  render(<StudentCheckoutStatus purpose="parent" checkoutId={checkoutId} onComplete={vi.fn()} />);
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(`/parent/payments/checkouts/${checkoutId}`, expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

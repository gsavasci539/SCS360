import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PaymentReadinessPanel } from "../features/saas/PaymentReadinessPanel";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Ayarlar alınamadı" }));
const pending = { state: "needs_configuration", mode: "sandbox", available: false, enabled: false, configured: false,
  missing_fields: ["SAAS_IYZICO_API_KEY", "SAAS_IYZICO_SECRET_KEY"], invalid_fields: [], warnings: [], organization_id: null };
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("eksik hesap ayarlarını adlarıyla gösterir ve aktif ödeme izlenimi vermez", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { saas: pending, school: { ...pending, missing_fields: ["IYZICO_ORGANIZATION_ID"] }, provider_verified: false } } });
  render(<PaymentReadinessPanel />);
  const membership = await screen.findByRole("article", { name: "SCS360 üyelik ödemeleri" });
  expect(within(membership).getByText("Kurulum bekleniyor")).toBeInTheDocument();
  expect(membership).toHaveTextContent("SAAS_IYZICO_API_KEY");
  expect(screen.queryByText("iyzico Sandbox · test ortamı")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /^(Etkinleştir|Öde|Kartla öde)$/ })).not.toBeInTheDocument();
});

it("gerçek yapılandırılmış sandbox ile kapalı hesabı ayırır ve başarısız durum sorgusunu yeniden dener", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ data: { data: {
    saas: { ...pending, state: "sandbox_configured", configured: true, enabled: true, available: true, missing_fields: [] },
    school: { ...pending, state: "sandbox_configured", configured: true, missing_fields: [] }, provider_verified: false } } });
  render(<PaymentReadinessPanel />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Ayarlar alınamadı");
  fireEvent.click(screen.getByRole("button", { name: "Ödeme ayarlarını yenile" }));
  expect(await screen.findByText("iyzico Sandbox · test ortamı")).toBeInTheDocument();
  expect(screen.getByText("Yapılandırıldı · kapalı")).toBeInTheDocument();
  expect(screen.getByText(/Sağlayıcıyla başarılı ödeme ve sonuç doğrulaması ayrıca test edilmelidir/)).toBeInTheDocument();
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
});

it("bozuk durum yanıtını yakalar ve dizi alanları olmadan kartı çöktürmez", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ data: { data: { saas: { ...pending, missing_fields: null }, school: pending, provider_verified: false } } })
    .mockResolvedValue({ data: { data: { saas: pending, school: pending, provider_verified: false } } });
  render(<PaymentReadinessPanel />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Ayarlar alınamadı");
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Ödeme ayarlarını yenile" }));
  expect(await screen.findByRole("article", { name: "SCS360 üyelik ödemeleri" })).toBeInTheDocument();
});

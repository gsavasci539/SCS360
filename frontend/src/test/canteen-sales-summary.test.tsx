import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CanteenSalesPage } from "../features/operations/CanteenSalesPage";
import { getAnalysis } from "../lib/analysis";
import { api } from "../lib/api";

vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));

beforeEach(() => { vi.mocked(api.get).mockResolvedValue({ data: { data: [] } }); });
afterEach(() => { cleanup(); vi.resetAllMocks(); });

async function open(analysis: Record<string, unknown>) {
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: analysis } } as never);
  render(<MemoryRouter><CanteenSalesPage /></MemoryRouter>);
  await screen.findByText("Toplam Satış");
}

function metric(label: string) { return within(screen.getByText(label).parentElement!); }

it("describes unknown inventory and recorded sales without inventing critical stock or a stable trend", async () => {
  await open({ total_sales: 25, daily_average: 5, inventory_status: "unknown", trend: "recorded", recommendations: [] });
  expect(screen.getByText("Stok verisi yok")).toBeInTheDocument();
  expect(screen.getByText("Kayıtlı satış özeti")).toBeInTheDocument();
  expect(screen.queryByText("Kritik")).not.toBeInTheDocument();
  expect(screen.queryByText("Stabil")).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("shows missing history as insufficient trend data while retaining an actual recorded zero", async () => {
  await open({ total_sales: 0, daily_average: "0.00", inventory_status: "unknown", trend: "insufficient_data" });
  expect(screen.getByText("Trend için veri yetersiz")).toBeInTheDocument();
  expect(metric("Toplam Satış").getByText("0.00 TL")).toBeInTheDocument();
  expect(metric("Günlük Ortalama").getByText("0.00 TL")).toBeInTheDocument();
});

it.each([
  [null, undefined], [Number.NaN, Number.POSITIVE_INFINITY], ["NaN", "Infinity"], [-1, "-2.00"],
])("keeps missing or invalid amounts unknown instead of crashing or displaying zero (%s, %s)", async (total, average) => {
  await open({ total_sales: total, daily_average: average });
  expect(metric("Toplam Satış").getByText("Tutar bilinmiyor")).toBeInTheDocument();
  expect(metric("Günlük Ortalama").getByText("Tutar bilinmiyor")).toBeInTheDocument();
  expect(screen.queryByText("0.00 TL")).not.toBeInTheDocument();
});

it("only displays explicit stock and trend classifications supplied by the API", async () => {
  await open({ total_sales: "123.45", daily_average: "4.12", inventory_status: "critical", trend: "decreasing" });
  expect(screen.getByText("Kritik")).toBeInTheDocument();
  expect(screen.getByText("Düşüş")).toBeInTheDocument();
  expect(metric("Toplam Satış").getByText("123.45 TL")).toBeInTheDocument();
});

it("separates real sales, top-ups and catalogue history and displays the actual inclusive period", async () => {
  await open({ total_sales: "35.00", daily_average: "1.17", wallet_debit_amount: "15.00", direct_sale_amount: "20.00",
    topup_amount: "100.00", catalog_orders: { amount: "22.00", record_count: 2 }, observed_day_count: 30,
    period_start: "2026-01-01", period_end_exclusive: "2026-01-31", as_of: "2026-01-30T21:30:00Z", timezone: "Europe/Istanbul" });
  expect(metric("Toplam Satış").getByText("35.00 TL")).toBeInTheDocument();
  expect(screen.getByText("Cüzdandan harcama").parentElement).toHaveTextContent("15.00 TL");
  expect(screen.getByText("Doğrudan satış").parentElement).toHaveTextContent("20.00 TL");
  expect(screen.getByText("Bakiye yüklemeleri").parentElement).toHaveTextContent("100.00 TL");
  expect(screen.getByText("Eski katalog siparişleri").parentElement).toHaveTextContent("22.00 TL");
  expect(screen.getByText(/Dönem:/)).toHaveTextContent("01.01.2026 – 30.01.2026 · 30 gözlenen gün");
  expect(screen.getByText(/Son durum:/)).toHaveTextContent("31.01.2026 00:30:00");
  expect(screen.getByText(/satış toplamına dahil edilmez/)).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("shows review and unknown period information without inventing a zero", async () => {
  await open({ total_sales: null, daily_average: null, requires_review: true, period_start: "invalid", as_of: "invalid" });
  expect(screen.getByRole("status")).toHaveTextContent("Bazı kayıtlar incelenmeli");
  expect(screen.getByText(/Dönem:/)).toHaveTextContent("Tarih bilinmiyor");
  expect(screen.getByText(/Son durum:/)).toHaveTextContent("Güncelleme zamanı bilinmiyor");
  expect(screen.queryByText("0.00 TL")).not.toBeInTheDocument();
});

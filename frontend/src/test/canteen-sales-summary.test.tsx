import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CanteenSalesPage } from "../features/operations/CanteenSalesPage";
import { CanteenPage } from "../features/operations/CanteenPage";
import { ToastProvider } from "../components/Toast";
import { getAnalysis } from "../lib/analysis";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));

beforeEach(() => { vi.mocked(api.get).mockResolvedValue({ data: { data: [] } }); });
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

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

it("shows the receipt only after exact cart and stored order verification", async () => {
  useAuthStore.setState({ user: { id: "cashier", first_name: "İzole", last_name: "Görevli", email: "pos@test.invalid",
    organization_id: "school", is_super_admin: false, roles: [], permissions: ["canteen.read", "canteen.write"], branch_ids: ["branch"] } });
  let stored = false;
  const product = { id: "product", branch_id: "branch", name: "İzole ürün", category: "Menü", price: 8.25, allergens: [], is_available: true };
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data:
    path === "/canteen/options" ? { students: [{ id: "student", name: "İzole öğrenci", active: true }] }
    : path === "/canteen/products" ? [product]
    : path === "/canteen/student/student/wallet" ? { student_id: "student", branch_id: "branch", student_name: "İzole öğrenci",
      balance: 20, daily_limit: null, daily_spent: 0, dietary_restrictions: [] }
    : path === "/canteen/orders" && stored ? [{ id: "stored-order", student_id: "student", branch_id: "branch", student_name: "İzole öğrenci",
      branch_name: "Kayıtlı şube", product_id: "product", product_name: "İzole ürün", quantity: 1, unit_price: 8.25, total_price: 8.25,
      status: "COMPLETED", payment_method: "WALLET", order_date: "2026-11-21", order_time: "10:00:00" }]
    : [] } }));
  vi.mocked(api.post).mockImplementation(async (_path, body) => ({ data: { data: { authorized: true,
    operation_id: (body as { request_id: string }).request_id, student_id: "student", branch_id: "branch",
    items: [{ order_id: "stored-order", product_id: "product", quantity: 1, total: 8.25 }],
  } } }));
  await open({ total_sales: 0 });
  fireEvent.change(screen.getByPlaceholderText("Öğrenci ara veya kart okutun"), { target: { value: "İzole" } });
  fireEvent.click(screen.getByRole("button", { name: "Öğrenciyi ara" }));
  fireEvent.click(await screen.findByRole("button", { name: /İzole ürün/ }));
  fireEvent.click(screen.getByRole("button", { name: "Cüzdandan satışı kaydet" }));
  expect(await screen.findByText("İstek tamamlanamadı")).toBeInTheDocument();
  expect(screen.queryByText("KANTİN MAKBUZU")).not.toBeInTheDocument();
  stored = true;
  fireEvent.click(screen.getByRole("button", { name: "Aynı siparişi doğrula" }));
  expect(await screen.findByText("KANTİN MAKBUZU")).toBeInTheDocument();
  expect(screen.getByText("Kayıtlı şube")).toBeInTheDocument();
  expect(vi.mocked(api.post).mock.calls[0].slice(0, 2)).toEqual(vi.mocked(api.post).mock.calls[1].slice(0, 2));
});

it("creates a product only in the selected real branch and reopens it from the API", async () => {
  useAuthStore.setState({ user: { id: "owner", first_name: "İzole", last_name: "Yetkili", email: "catalog@test.invalid",
    organization_id: "school", is_super_admin: false, roles: [], permissions: ["canteen.read", "canteen.write"], branch_ids: [] } });
  vi.mocked(getAnalysis).mockResolvedValue({ data: { data: null } } as never);
  let stored: Record<string, unknown> | null = null;
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/canteen/options"
    ? { branches: [{ id: "north", name: "Kuzey" }, { id: "south", name: "Güney" }] }
    : path === "/canteen/products" && stored ? [stored] : [] } }));
  vi.mocked(api.post).mockImplementation(async (_path, body) => {
    const payload = body as Record<string, unknown>;
    stored = { ...payload, id: payload.request_id, price: Number(payload.price), updated_at: "2026-11-21T05:21:00Z" };
    return { data: { data: { id: payload.request_id } } };
  });
  render(<MemoryRouter><ToastProvider><CanteenPage /></ToastProvider></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Ürün Ekle" }));
  const dialog = screen.getByRole("dialog", { name: "Kantin ürünü formu" });
  expect(within(dialog).getByRole("button", { name: "Kaydet" })).toBeDisabled();
  fireEvent.change(within(dialog).getByLabelText("Ürün şubesi"), { target: { value: "south" } });
  fireEvent.change(within(dialog).getByLabelText("Ürün adı"), { target: { value: "İzole katalog ürünü" } });
  fireEvent.change(within(dialog).getByLabelText("Ürün fiyatı"), { target: { value: "14.20" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Kaydet" }));
  expect(await screen.findByText("İzole katalog ürünü")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith("/canteen/products", expect.objectContaining({ branch_id: "south",
    price: "14.20", request_id: expect.any(String) }), expect.objectContaining({ signal: expect.any(AbortSignal) }));
  expect(api.get).toHaveBeenCalledWith("/canteen/products", expect.objectContaining({
    params: { branch_id: "south", record_id: expect.any(String), limit: 1 },
  }));
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

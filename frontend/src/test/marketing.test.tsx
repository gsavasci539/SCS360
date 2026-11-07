import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MarketingPage } from "../features/marketing/MarketingPage";
import { SignupPage } from "../features/marketing/SignupPage";
import { AboutPage } from "../features/marketing/AboutPage";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
const plan = { id: "school-plan", name: "Okul Paketi", price: "1240.50", currency: "TRY", branch_limit: 2, student_limit: 80, user_limit: 12, period_months: 1, is_active: true };
beforeEach(() => { useAuthStore.getState().clearSession(); vi.spyOn(window, "scrollTo").mockImplementation(() => {}); vi.mocked(api.get).mockResolvedValue({ data: { data: [plan] } }); });
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.restoreAllMocks(); vi.resetAllMocks(); });

it("tanıtım gerçek katalog fiyatını ve sınırları gösterir, paket seçimi kayıt ekranına gider", async () => {
  render(<MemoryRouter><MarketingPage /></MemoryRouter>);
  expect(screen.getByRole("heading", { name: /Eğitimde bütün resmi/ })).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: "Paketi seç" })).toHaveAttribute("href", "/kayit?paket=school-plan");
  expect(screen.getByText("80 öğrenci")).toBeInTheDocument(); expect(screen.getByText(/₺1.240,50/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Yıllık" })); expect(screen.getByText(/Bu dönem için satışa açık paket bulunmuyor/)).toBeInTheDocument();
});

it("boş katalogda uydurma fiyat ve satın alma düğmesi üretmez", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: [] } }); render(<MemoryRouter><MarketingPage pricing /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Paketler hazırlanıyor." })).toBeInTheDocument(); expect(screen.queryByRole("link", { name: "Paketi seç" })).not.toBeInTheDocument();
});

it("ana sayfada özgün eğitim illüstrasyonunu boyut ve açıklamasıyla sunar", async () => {
  render(<MemoryRouter><MarketingPage /></MemoryRouter>);
  const artwork = screen.getByRole("img", { name: /eğitim kampüsü illüstrasyonu/ });
  expect(artwork).toHaveAttribute("src", "/images/scs360-education-campus-v1.png");
  expect(artwork).toHaveAttribute("width", "1536"); expect(artwork).toHaveAttribute("height", "1024");
  expect(artwork).toHaveAttribute("fetchpriority", "high");
  expect(screen.getByText("Temsili eğitim kampüsü illüstrasyonu.")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "SCS360 ürün turu" })).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Hakkımızda" }).every((link) => link.getAttribute("href") === "/hakkimizda")).toBe(true);
  await screen.findByRole("link", { name: "Paketi seç" });
});

it("Hakkımızda gerçek ürün amacını anlatır ve ürün turu ile fiyatlandırmaya yönlendirir", async () => {
  render(<MemoryRouter initialEntries={["/hakkimizda"]}><AboutPage /></MemoryRouter>);
  expect(screen.getByRole("heading", { level: 1, name: /Eğitimin etrafında/ })).toBeInTheDocument();
  expect(screen.getByText("Kurum sahibi", { exact: true })).toBeInTheDocument();
  expect(screen.getByText("Veli", { exact: true })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Ürün turunu keşfedin/ })).toHaveAttribute("href", "/#urun");
  expect(screen.getByRole("link", { name: /Paketleri inceleyin/ })).toHaveAttribute("href", "/fiyatlandirma");
  expect(within(screen.getByRole("navigation", { name: "Site menüsü" })).getByRole("link", { name: "Hakkımızda" })).toHaveAttribute("aria-current", "page");
  expect(api.get).not.toHaveBeenCalled();
  await waitFor(() => expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "instant" }));
});

it("temsili ürün turu alanları tıklama ve klavyeyle değişir, ek veri erişimi istemez", async () => {
  render(<MemoryRouter><MarketingPage /></MemoryRouter>);
  const tour = screen.getByRole("region", { name: "SCS360 ürün turu" });
  expect(within(tour).getByText("Temsili arayüz ve örnek içerik.")).toBeInTheDocument();
  const finance = within(tour).getByRole("tab", { name: "Finans" });
  fireEvent.click(finance);
  expect(finance).toHaveAttribute("aria-selected", "true");
  expect(within(tour).getByRole("tabpanel")).toHaveTextContent("Borç ve tahsilat takibi");
  fireEvent.keyDown(finance, { key: "ArrowLeft" });
  expect(within(tour).getByRole("tab", { name: "Eğitim" })).toHaveFocus();
  expect(within(tour).getByRole("tabpanel")).toHaveTextContent("Günlük rapor");
  await screen.findByRole("link", { name: "Paketi seç" });
  expect(vi.mocked(api.get).mock.calls.every(([path]) => path === "/public/plans")).toBe(true);
});

it("katalog hatasını yeniden dener ve yıllık gerçek paketi doğru kayıt bağlantısıyla sunar", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("unavailable")).mockResolvedValue({ data: { data: [{ ...plan, id: "annual-plan", period_months: 12, price: "9999.99" }] } });
  render(<MemoryRouter><MarketingPage pricing /></MemoryRouter>);
  expect(await screen.findByText("İstek tamamlanamadı")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Tekrar dene/ }));
  await screen.findByText(/Bu dönem için satışa açık paket bulunmuyor/);
  fireEvent.click(screen.getByRole("button", { name: "Diğer dönemi göster" }));
  expect(await screen.findByRole("link", { name: "Paketi seç" })).toHaveAttribute("href", "/kayit?paket=annual-plan");
  expect(screen.getByText(/₺9.999,99/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Yıllık" })).toHaveAttribute("aria-pressed", "true");
});

it("başka sayfadan gelen bölüm bağlantısını render sonrası kaydırır ve içeriğe geç odaklanır", async () => {
  const previous = HTMLElement.prototype.scrollIntoView, targets: HTMLElement[] = [];
  const scroll = vi.fn(function (this: HTMLElement) { targets.push(this); });
  HTMLElement.prototype.scrollIntoView = scroll;
  const router = createMemoryRouter([{ path: "/", element: <MarketingPage /> }, { path: "/fiyatlandirma", element: <MarketingPage pricing /> }], { initialEntries: ["/fiyatlandirma"] });
  try {
    render(<RouterProvider router={router} />);
    await screen.findByRole("heading", { name: "İhtiyacınıza göre bir paket." });
    await act(() => router.navigate("/#guven"));
    await waitFor(() => expect(targets.at(-1)?.id).toBe("guven"));
    expect(scroll).toHaveBeenLastCalledWith({ block: "start", behavior: "instant" });
    await act(() => router.navigate("/#public-main"));
    await waitFor(() => expect(screen.getByRole("main")).toHaveFocus());
    expect(targets.at(-1)?.id).toBe("public-main");
    const count = targets.length;
    await act(() => router.navigate("/#%E0%A4%A"));
    expect(targets).toHaveLength(count);
  } finally {
    router.dispose();
    if (previous) HTMLElement.prototype.scrollIntoView = previous;
    else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  }
});

it("bekleyen fiyat kataloğu tamamlanınca alt bölüm yer imini yeni yüksekliğe göre konumlandırır", async () => {
  let complete!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((resolve) => { complete = resolve; }));
  const previous = HTMLElement.prototype.scrollIntoView, targets: HTMLElement[] = [];
  HTMLElement.prototype.scrollIntoView = function () { targets.push(this); };
  try {
    render(<MemoryRouter initialEntries={["/#sorular"]}><MarketingPage /></MemoryRouter>);
    await waitFor(() => expect(targets.at(-1)?.id).toBe("sorular"));
    const before = targets.length;
    await act(async () => complete({ data: { data: [plan] } }));
    await screen.findByRole("link", { name: "Paketi seç" });
    await waitFor(() => expect(targets.length).toBeGreaterThan(before));
    expect(targets.at(-1)?.id).toBe("sorular");
  } finally {
    if (previous) HTMLElement.prototype.scrollIntoView = previous;
    else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  }
});

it("kayıt zaman aşımından sonra aynı istekle tekrar edilir, giriş sonrası ödeme adımına gider", async () => {
  vi.mocked(api.post).mockImplementation(async (path) => path === "/auth/login" ? { data: { data: { access_token: "access", refresh_token: "refresh", user: { id: "owner", organization_id: "school", is_super_admin: false, roles: [], branch_ids: [], permissions: [] } } } } : { data: { data: {} } });
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout"));
  render(<MemoryRouter initialEntries={["/kayit?paket=school-plan"]}><Routes><Route path="/kayit" element={<SignupPage />} /><Route path="/subscription" element={<p>Üyelik ödeme adımı</p>} /></Routes></MemoryRouter>);
  await screen.findByRole("form", { name: "Kurum üyeliği oluştur" });
  for (const [label, value] of [["Kurum adı", "Yeni Okul"], ["Adınız", "Kurum"], ["Soyadınız", "Sahibi"], ["E-posta adresiniz", "owner@example.com"], ["Parola", "AcceptancePass1!"], ["Parola tekrarı", "AcceptancePass1!"]]) fireEvent.change(screen.getByLabelText(label, { exact: true }), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Hesabı oluştur ve ödeme adımına geç" })); await screen.findByText("İstek tamamlanamadı");
  fireEvent.click(screen.getByRole("button", { name: "Hesabı oluştur ve ödeme adımına geç" })); await screen.findByText("Üyelik ödeme adımı");
  const calls = vi.mocked(api.post).mock.calls.filter(([path]) => path === "/public/signup");
  expect(calls).toHaveLength(2); expect(calls[0]).toEqual(calls[1]); expect(calls[0][1]).not.toHaveProperty("price"); expect(calls[0][1]).not.toHaveProperty("confirm_password");
  await waitFor(() => expect(useAuthStore.getState().accessToken).toBe("access"));
});

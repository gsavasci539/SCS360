import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PaymentPage } from "../features/payment/PaymentPage";
import { checkoutAttemptKey, checkoutScope, saveSchoolCheckout } from "../features/payment/schoolCheckoutAttempt";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
const debtId = "00000000-0000-4000-8000-000000000001", checkoutId = "00000000-0000-4000-8000-000000000002";
const metadata = { conversation_id: checkoutId, debt_id: debtId, amount: "25.00", status: "FRAUD_REVIEW", can_resume: false, can_refresh: true };
beforeEach(() => {
  useAuthStore.setState({ user: { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "actor@example.invalid", is_super_admin: false, roles: [], permissions: ["parent.view_children", "parent.view_finances", "parent.make_payment", "finance.write"], branch_ids: [] }, sessionVersion: 1 });
  usePlatformWorkspace.setState({ workspace: null }); sessionStorage.clear();
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).includes("/checkouts/") ? metadata
    : path === "/parent/my-children" || path === "/parent/my-children/options?module=finances" ? [{ student_id: "child", first_name: "Deniz", last_name: "Test" }]
      : String(path).endsWith("/financial-invoices") ? { student_id: "child", total_remaining: "25.00", invoices: [{ debt_id: debtId, remaining_amount: "25.00", amount: "25.00", status: "UNPAID", debt_type: "EDUCATION" }], online_payment_available: true }
        : String(path).endsWith("/insights") ? { recommendations: [] } : {} } }));
});
afterEach(() => { cleanup(); vi.resetAllMocks(); sessionStorage.clear(); });

it("a staff callback query reads its checkout and never trusts URL success or starts a new payment", async () => {
  render(<MemoryRouter initialEntries={[`/payment?checkout=${checkoutId}&success=true`]}><Routes><Route path="/payment" element={<PaymentPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText(/Ödeme incelemede/)).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith(`/payments/iyzico/checkouts/${checkoutId}`, expect.anything());
  expect(api.post).not.toHaveBeenCalled(); expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.queryByText("Ödemeniz doğrulandı ve borcunuza işlendi.")).not.toBeInTheDocument();
});

it("a parent callback uses only the parent-purpose status and refresh routes", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { data: { ...metadata, status: "PAID_REVIEW", can_resume: false } } });
  render(<MemoryRouter initialEntries={[`/parent/finances?checkout=${checkoutId}`]}><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  expect(await screen.findByText(/Ödeme alınmış, kayıt uzlaştırması bekleniyor/)).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith(`/parent/payments/checkouts/${checkoutId}/refresh`, {}, expect.anything());
  expect(vi.mocked(api.get).mock.calls.some(([path]) => String(path).includes("/payments/iyzico/"))).toBe(false);
});

it("the real parent invoice modal initializes with the persisted nonce and hides payment entry when permission is absent", async () => {
  vi.mocked(api.post).mockImplementation(async (_path, body) => ({ data: { data: { ...metadata,
    conversation_id: (body as { request_id: string }).request_id, status: "PENDING", can_resume: true,
    checkout_url: "https://sandbox-api.iyzipay.com/checkoutform/test" } } }));
  const view = render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Öde" }));
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/parent/payments/initialize", expect.objectContaining({ debt_id: debtId, amount: "25.00", request_id: expect.any(String) }), expect.anything()));
  view.unmount(); useAuthStore.setState({ user: { ...useAuthStore.getState().user!, permissions: ["parent.view_finances"] } });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  await screen.findByText("Ödenmedi", { exact: true }); expect(screen.queryByRole("button", { name: "Öde" })).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/parent/my-children/options?module=finances", expect.anything());
});

it("çocuk değiştiğinde ödeme penceresini kapatır ve gecikmiş veya yanlış öğrenci bakiyesini göstermez", async () => {
  const secondDebtId = "00000000-0000-4000-8000-000000000005";
  const firstSnapshot = { student_id: "child", total_remaining: "25.00", online_payment_available: true,
    invoices: [{ debt_id: debtId, remaining_amount: "25.00", status: "UNPAID", description: "İlk çocuğun borcu" }] };
  const secondSnapshot = { student_id: "sibling", total_remaining: "50.00", online_payment_available: true,
    invoices: [{ debt_id: secondDebtId, remaining_amount: "50.00", status: "UNPAID", description: "İkinci çocuğun borcu" }] };
  let firstRequests = 0;
  let finishOldRequest!: (value: unknown) => void;
  let siblingRequests = 0;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/parent/my-children") return { data: { data: [
      { student_id: "child", first_name: "Deniz" }, { student_id: "sibling", first_name: "Ada" },
    ] } };
    if (path === "/parent/child/child/financial-invoices") {
      if (++firstRequests === 3) return new Promise((resolve) => { finishOldRequest = resolve; });
      return { data: { data: firstSnapshot } };
    }
    if (path === "/parent/child/sibling/financial-invoices") {
      return { data: { data: ++siblingRequests === 1 ? firstSnapshot : secondSnapshot } };
    }
    return { data: { data: null } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  const choose = (value: string) => fireEvent.change(screen.getByRole("combobox", { name: "Öğrenci Seçin" }), { target: { value } });
  fireEvent.click(await screen.findByRole("button", { name: "Öde" }));
  expect(screen.getByRole("dialog", { name: "Öğrenci ödemesi" })).toBeInTheDocument();
  choose("sibling");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(await screen.findByText("Ödeme kayıtları seçili öğrenci için doğrulanamadı.")).toBeInTheDocument();
  expect(screen.queryByText("Kalan toplam:")).not.toBeInTheDocument();
  expect(screen.queryByText("Bekleyen ödeme bulunmuyor.")).not.toBeInTheDocument();
  choose("child");
  await screen.findByText("İlk çocuğun borcu");
  fireEvent.click(screen.getByRole("button", { name: "Borçları yenile" }));
  await waitFor(() => expect(firstRequests).toBe(3));
  const lastRequest = vi.mocked(api.get).mock.calls.filter(([path]) => path === "/parent/child/child/financial-invoices").at(-1)?.[1];
  choose("sibling");
  expect(lastRequest?.signal?.aborted).toBe(true);
  expect(await screen.findByText("İkinci çocuğun borcu")).toBeInTheDocument();
  await act(async () => finishOldRequest({ data: { data: firstSnapshot } }));
  expect(screen.queryByText("İlk çocuğun borcu")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Öde" }));
  expect(screen.getByText(/Ada · .*50/)).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("borç yenileme, açık işlem sona erince ödeme düğmesini geri getirir ve oturum değişimini korur", async () => {
  const invoicePath = "/parent/child/child/financial-invoices";
  const snapshot = (description: string, payment_in_progress: boolean) => ({ data: { data: {
    student_id: "child", total_remaining: 25, online_payment_available: true,
    invoices: [{ debt_id: debtId, description, payment_in_progress, remaining_amount: 25, status: "UNPAID" }],
  } } });
  let reads = 0;
  let completeOldRequest!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path !== invoicePath) return { data: { data: path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz" }] : null } };
    if (++reads === 3) return new Promise((resolve) => { completeOldRequest = resolve; });
    return snapshot(reads === 4 ? "Yeni oturumun borcu" : "Öğrenci borcu", reads === 1);
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  expect(await screen.findByText("Bu borç için açık bir ödeme işlemi var.")).toBeInTheDocument();
  const refresh = () => screen.getByRole("button", { name: "Borçları yenile" });
  fireEvent.click(refresh());
  expect(refresh()).toBeDisabled();
  expect(await screen.findByRole("button", { name: "Öde" })).toBeInTheDocument();
  fireEvent.click(refresh());
  const pending = vi.mocked(api.get).mock.calls.filter(([path]) => path === invoicePath).at(-1)?.[1];
  act(() => useAuthStore.setState({ sessionVersion: 2 }));
  expect(await screen.findByText("Yeni oturumun borcu")).toBeInTheDocument();
  expect(pending?.signal?.aborted).toBe(true);
  await act(async () => completeOldRequest(snapshot("Eski oturumun borcu", true)));
  expect(screen.queryByText("Eski oturumun borcu")).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("finans izni yoksa borç isteği yapmaz ve bakiye göstermez", async () => {
  useAuthStore.setState({ user: { ...useAuthStore.getState().user!, permissions: ["parent.view_children"] } });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  expect(await screen.findByText("Ödeme kayıtlarını görüntüleme yetkiniz yok.")).toBeInTheDocument();
  expect(screen.queryByText("Kalan toplam:")).not.toBeInTheDocument();
  expect(screen.queryByText("Bekleyen ödeme bulunmuyor.")).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.endsWith("/financial-invoices"))).toBe(false);
});

it.each([
  { fromServer: false, online: false, debtStatus: "UNPAID", remaining: "25.00" },
  { fromServer: false, online: true, debtStatus: "PAID", remaining: "0.00" },
  { fromServer: true, online: true, debtStatus: "UNPAID", remaining: "25.00" },
])("ödeme sonucu salt okunur açılır (sunucudan: $fromServer, borç durumu: $debtStatus)", async ({ fromServer, online, debtStatus, remaining }) => {
  const storageKey = checkoutAttemptKey(checkoutScope(useAuthStore.getState().user, null, "parent"), debtId);
  if (!fromServer) saveSchoolCheckout(storageKey, { version: 1, debt_id: debtId, request_id: checkoutId, amount: "25.00", status: "PENDING" });
  const invoicePath = "/parent/child/child/financial-invoices";
  const statusPath = `/parent/payments/checkouts/${checkoutId}`;
  let statusCalls = 0;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === statusPath) return { data: { data: ++statusCalls === 1 ? { ...metadata, status: "REVIEW", can_resume: true } :
      { ...metadata, status: "COMPLETED", payment_id: "00000000-0000-4000-8000-000000000010" } } };
    if (path === invoicePath) return { data: { data: { student_id: "child", total_remaining: remaining, online_payment_available: online, invoices: [
      { debt_id: debtId, status: debtStatus, remaining_amount: remaining,
        open_checkout: fromServer ? { debt_id: debtId, request_id: checkoutId, amount: "25.00" } : null },
      { debt_id: "00000000-0000-4000-8000-000000000011", status: "CANCELLED", remaining_amount: "0.00" },
    ] } } };
    return { data: { data: path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz" }] : null } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  expect(screen.queryByRole("button", { name: "Öde" })).not.toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "Kayıtlı ödeme sonucu" })).toBeInTheDocument();
  expect(await screen.findByText(/Ödeme incelemede/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Mevcut ödeme sayfasını getir" })).not.toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Öğrenci ödeme bilgileri" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Kaydı yeniden yükle" }));
  expect(await screen.findByText("Ödemeniz doğrulandı ve borcunuza işlendi.")).toBeInTheDocument();
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.filter(([path]) => path === invoicePath)).toHaveLength(2));
  expect(statusCalls).toBe(2);
  expect(api.post).not.toHaveBeenCalled();
  if (fromServer) expect(window.sessionStorage.getItem(storageKey!)).toBeNull();
});

it.each([true, false])("açık işlem çakışmasında borçları yeniler (kendi işlemi: %s)", async (ownCheckout) => {
  const key = checkoutAttemptKey(checkoutScope(useAuthStore.getState().user, null, "parent"), debtId);
  let conflict = false;
  const invoicesPath = "/parent/child/child/financial-invoices";
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === invoicesPath) return { data: { data: { student_id: "child", total_remaining: 25, online_payment_available: true,
      invoices: [{ debt_id: debtId, remaining_amount: 25, status: "UNPAID", description: "Test borcu",
        payment_in_progress: conflict, open_checkout: conflict && ownCheckout
          ? { request_id: checkoutId, debt_id: debtId, amount: "25.00" } : null }] } } };
    if (path === `/parent/payments/checkouts/${checkoutId}`) return { data: { data: metadata } };
    return { data: { data: path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz" }] : null } };
  });
  vi.mocked(api.post).mockImplementation(async () => {
    conflict = true;
    throw { response: { status: 409, data: { errors: [{ code: "SCHOOL_CHECKOUT_IN_PROGRESS" }] } } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Öde" }));
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  if (ownCheckout) {
    fireEvent.click(await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }));
    expect(await screen.findByText(/Ödeme incelemede/)).toBeInTheDocument();
  } else {
    expect(await screen.findByText("Bu borç için açık bir ödeme işlemi var.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ödeme sonucunu kontrol et" })).not.toBeInTheDocument();
  }
  expect(screen.getByText("Test borcu")).toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Öde" })).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.filter(([path]) => path === invoicesPath)).toHaveLength(2);
  expect(vi.mocked(api.get).mock.calls.filter(([path]) => path.includes("/checkouts/")).map(([path]) => path))
    .toEqual(ownCheckout ? [`/parent/payments/checkouts/${checkoutId}`] : []);
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(window.sessionStorage.getItem(key!)).toBeNull();
});

it("kısmi tahsilatın kalan tutarı yeni işlem kimliğiyle gönderilir", async () => {
  const key = checkoutAttemptKey(checkoutScope(useAuthStore.getState().user, null, "parent"), debtId);
  saveSchoolCheckout(key, { version: 1, request_id: checkoutId, debt_id: debtId, amount: "25.00", status: "PENDING" });
  let invoiceReads = 0;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === `/parent/payments/checkouts/${checkoutId}`) return { data: { data: { ...metadata,
      status: "COMPLETED", payment_id: "00000000-0000-4000-8000-000000000010" } } };
    if (path.endsWith("/financial-invoices")) {
      const remaining = ++invoiceReads === 1 ? 100 : 75;
      return { data: { data: { student_id: "child", total_remaining: remaining, online_payment_available: true,
        invoices: [{ debt_id: debtId, remaining_amount: remaining, status: "PARTIALLY_PAID" }] } } };
    }
    return { data: { data: path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz" }] : null } };
  });
  vi.mocked(api.post).mockImplementation(async (_path, body) => {
    const request = body as { request_id: string; amount: string };
    return { data: { data: { ...metadata, conversation_id: request.request_id, amount: request.amount, status: "PENDING" } } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Öde" }));
  fireEvent.click(await screen.findByRole("button", { name: "Kalan borç için yeni ödeme" }));
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.submit(screen.getByRole("form", { name: "Öğrenci ödeme bilgileri" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  const request = vi.mocked(api.post).mock.calls[0][1] as { request_id: string; amount: string };
  expect(request.amount).toBe("75.00");
  expect(request.request_id).not.toBe(checkoutId);
});

it("aynı tarayıcı sunucudaki açık ödeme ile eşleşen kayıtlı işleme döner", async () => {
  const storageKey = checkoutAttemptKey(checkoutScope(useAuthStore.getState().user, null, "parent"), debtId);
  saveSchoolCheckout(storageKey, { version: 1, debt_id: debtId, request_id: checkoutId, amount: "25.00", status: "PENDING" });
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path.endsWith("/financial-invoices")) return { data: { data: { student_id: "child", total_remaining: 25, online_payment_available: true,
      invoices: [{ debt_id: debtId, remaining_amount: 25, status: "UNPAID",
        open_checkout: { request_id: checkoutId, debt_id: debtId, amount: "25.00" } }] } } };
    if (path === `/parent/payments/checkouts/${checkoutId}`) return { data: { data: { ...metadata, status: "PENDING", can_resume: true } } };
    return { data: { data: path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz" }] : null } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Ödeme işlemine dön" }));
  expect(await screen.findByRole("button", { name: "Mevcut ödeme sayfasını getir" })).toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("kayıtlı sonuç farklı borçla veya tutarla eşleşirse tahsilat göstermez", async () => {
  const storageKey = checkoutAttemptKey(checkoutScope(useAuthStore.getState().user, null, "parent"), debtId);
  saveSchoolCheckout(storageKey, { version: 1, debt_id: debtId, request_id: checkoutId, amount: "25.00", status: "PENDING" });
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path.endsWith("/financial-invoices")) return { data: { data: { student_id: "child", total_remaining: 25, online_payment_available: false,
      invoices: [{ debt_id: debtId, remaining_amount: 25, status: "UNPAID" }] } } };
    if (path === `/parent/payments/checkouts/${checkoutId}`) return { data: { data: { ...metadata,
      amount: "50.00", status: "COMPLETED", payment_id: "00000000-0000-4000-8000-000000000010" } } };
    return { data: { data: path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz" }] : null } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Ödeme sonucunu kontrol et" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("İstek tamamlanamadı");
  expect(screen.queryByText("Ödemeniz doğrulandı ve borcunuza işlendi.")).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

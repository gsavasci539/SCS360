import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PaymentFormPage, PaymentsPage } from "../features/finance/FinancePages";
import { api } from "../lib/api";
import type { AuthUser } from "../types/api";

const mocks = vi.hoisted(() => ({ navigate: vi.fn(), toast: vi.fn() }));
vi.mock("react-router-dom", async () => ({ ...await vi.importActual("react-router-dom"), useNavigate: () => mocks.navigate }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast: mocks.toast }) }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "Sonuç alınamadı" }));
vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn(async () => ({ data: { data: null } })) }));
let permissions = new Set<string>();
let account: AuthUser;
let workspace: { id: string; name: string; operatorId: string } | null = null;
vi.mock("../stores/auth", () => ({ useAuthStore: (selector: (value: { can: (permission: string) => boolean; user: AuthUser }) => unknown) => selector({ can: (permission) => permissions.has(permission), user: account }) }));
vi.mock("../stores/platformWorkspace", () => ({ usePlatformWorkspace: (selector: (value: { workspace: typeof workspace }) => unknown) => selector({ workspace }) }));
const debtId = "00000000-0000-4000-8000-000000000001";
const firstId = "00000000-0000-4000-8000-000000000011", secondId = "00000000-0000-4000-8000-000000000012";
const first = { id: firstId, student_name: "İlk kişi", amount: "100.00", payment_method: "CASH", status: "COMPLETED", payment_date: "2026-11-04" };
const second = { id: secondId, student_name: "İkinci kişi", amount: "50.00", payment_method: "CASH", status: "COMPLETED", payment_date: "2026-11-04" };
let rows: Record<string, unknown>[];
beforeEach(() => {
  sessionStorage.clear(); workspace = null;
  account = { id: "cashier-a", email: "cash@test.invalid", first_name: "Cash", last_name: "Test", organization_id: "school-a", is_super_admin: false,
    permissions: ["finance.write"], branch_ids: [], roles: [] };
  permissions = new Set(["finance.read", "finance.write", "receipt.read"]); rows = [first, second];
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).startsWith("/payments/debt-options") ? {
    items: [{ id: debtId, name: "Deniz · Kalan 100.00 TL" }], selected: null, total: 1, total_pages: 1, page: 1, page_size: 50,
  } : path === "/debts" ? { items: [{ id: debtId, student_name: "Deniz", remaining_amount: "100.00" }], total: 1, total_pages: 1 } :
    { items: rows, total: rows.length, total_pages: 1, page: 1, page_size: 20 } } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { receipt_id: "receipt", receipt_number: "RCP-ACCEPTANCE", remaining_debt: "75.00" } } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); mocks.navigate.mockReset(); mocks.toast.mockReset(); });

async function fillPayment() {
  const choice = await screen.findByRole("combobox", { name: /Borç kaydı/ });
  await waitFor(() => expect(within(choice).getByRole("option", { name: /Deniz/ })).toBeInTheDocument());
  fireEvent.change(choice, { target: { value: debtId } });
  fireEvent.change(screen.getByRole("spinbutton", { name: /Ödeme tutarı/ }), { target: { value: "25.00" } });
  fireEvent.change(screen.getByRole("combobox", { name: /Ödeme yöntemi/ }), { target: { value: "CASH" } });
}

it("sonucu bilinmeyen tahsilat tekrarında aynı istek kimliğini korur", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout"));
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  const submit = screen.getByRole("button", { name: /Tahsilatı tamamla/ });
  fireEvent.click(submit); await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(submit).toBeEnabled()); fireEvent.click(submit);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  const firstBody = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
  const retryBody = vi.mocked(api.post).mock.calls[1][1] as Record<string, unknown>;
  expect(firstBody.request_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/i));
  expect(retryBody.request_id).toBe(firstBody.request_id);
  expect(mocks.navigate).toHaveBeenCalledWith("/finance/receipts/receipt");
});

it("yalnız tahsilat yetkisiyle minimal borç seçer ve yasak makbuz sayfasına yönlenmez", async () => {
  permissions = new Set(["finance.write"]);
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/debts")).toBe(false);
  expect(vi.mocked(api.get).mock.calls.some(([path]) => String(path).startsWith("/payments/debt-options"))).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: /Tahsilatı tamamla/ }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  expect(await screen.findByText(/RCP-ACCEPTANCE/)).toBeInTheDocument();
  expect(mocks.navigate).not.toHaveBeenCalled();
});

it("iptal düğmesi kullanıcının seçtiği satırdaki tahsilatı hedefler", async () => {
  render(<MemoryRouter><PaymentsPage /></MemoryRouter>);
  const row = (await screen.findByText("İkinci kişi")).closest("tr")!;
  fireEvent.click(within(row).getByRole("button", { name: "İptal et" }));
  const dialog = await screen.findByRole("dialog");
  expect(dialog).toHaveTextContent("İkinci kişi");
  fireEvent.change(within(dialog).getByLabelText("İptal nedeni"), { target: { value: "İkinci işlem" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "İptal et" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith(`/payments/${secondId}/cancel`, { cancel_reason: "İkinci işlem" }));
});

it("online tahsilatta nakit iptali yerine sağlayıcı mutabakatı bilgisini gösterir", async () => {
  rows = [{ ...first, requires_provider_refund: true }]; render(<MemoryRouter><PaymentsPage /></MemoryRouter>);
  const row = (await screen.findByText("İlk kişi")).closest("tr")!;
  expect(within(row).queryByRole("button", { name: "İptal et" })).not.toBeInTheDocument();
  expect(within(row).getByText(/Sağlayıcı mutabakatı/)).toBeInTheDocument();
});

it("finans okuma ve yalnız tahsilat yetkisi olan kullanıcı tahsilat açabilir ama iptal edemez", async () => {
  permissions = new Set(["finance.read", "finance.collect_payment"]);
  render(<MemoryRouter><PaymentsPage /></MemoryRouter>);
  expect(await screen.findByRole("link", { name: "Tahsilat al" })).toHaveAttribute("href", "/finance/payments/new");
  await screen.findByText("İlk kişi");
  expect(screen.queryByRole("button", { name: "İptal et" })).not.toBeInTheDocument();
});

it("sonucu belirsiz tahsilatı sayfa yeniden açıldığında aynı gövdeyle sürdürür", async () => {
  permissions = new Set(["finance.write"]);
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout"));
  const mounted = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" }));
  await screen.findByRole("alert");
  const original = vi.mocked(api.post).mock.calls[0][1]; mounted.unmount();
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  const amount = screen.getByRole("spinbutton", { name: /Ödeme tutarı/ });
  expect(amount).toHaveValue(25); expect(amount).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" }));
  await screen.findByText("RCP-ACCEPTANCE");
  expect(vi.mocked(api.post).mock.calls[1][1]).toEqual(original);
});

it("bekleyen tahsilat taslağını başka kullanıcıya veya Root kurumuna taşımaz", async () => {
  permissions = new Set(["finance.write"]); account = { ...account, is_super_admin: true };
  workspace = { id: "school-a", name: "A", operatorId: account.id };
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout"));
  const mounted = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" })); await screen.findByRole("alert"); mounted.unmount();
  workspace = { ...workspace, id: "school-b" };
  const otherSchool = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  expect(screen.getByRole("spinbutton", { name: /Ödeme tutarı/ })).toHaveValue(null); otherSchool.unmount();
  workspace = { ...workspace, id: "school-a", operatorId: "cashier-b" }; account = { ...account, id: "cashier-b" };
  const otherAccount = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  expect(screen.getByRole("spinbutton", { name: /Ödeme tutarı/ })).toHaveValue(null); otherAccount.unmount();
  account = { ...account, id: "cashier-a" }; workspace = { ...workspace, operatorId: account.id };
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  expect(screen.getByRole("spinbutton", { name: /Ödeme tutarı/ })).toHaveValue(25);
});

it("başarılı tahsilatı yeniden açınca yeni ödeme göndermeden makbuzu gösterir", async () => {
  permissions = new Set(["finance.write"]);
  const mounted = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" })); await screen.findByText("RCP-ACCEPTANCE"); mounted.unmount();
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  expect(await screen.findByText("RCP-ACCEPTANCE")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Yeni tahsilat" }));
  expect(screen.getByRole("spinbutton", { name: /Ödeme tutarı/ })).toHaveValue(null);
});

it("işlem kimliği saklanamazsa sunucuya tahsilat göndermez", async () => {
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  const storage = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("unavailable"); });
  try {
    fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" }));
    await screen.findByRole("alert"); expect(api.post).not.toHaveBeenCalled();
  } finally { storage.mockRestore(); }
});

it("sunucu doğrulamada reddettiğinde alanları düzeltmeye izin verir ve yeni işlem kimliği kullanır", async () => {
  vi.mocked(api.post).mockRejectedValueOnce({ isAxiosError: true, response: { status: 422 } });
  render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" })); await screen.findByRole("alert");
  const amount = screen.getByRole("spinbutton", { name: /Ödeme tutarı/ }); expect(amount).toBeEnabled();
  fireEvent.change(amount, { target: { value: "20.00" } });
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  const first = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
  const second = vi.mocked(api.post).mock.calls[1][1] as Record<string, unknown>;
  expect(first.request_id).not.toBe(second.request_id); expect(second.amount).toBe("20.00");
});

it("eski tahsilatın geç yanıtı başka hesabı yönlendirmez ve kendi makbuzunu korur", async () => {
  let finish!: (value: unknown) => void;
  vi.mocked(api.post).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  const mounted = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>); await fillPayment();
  fireEvent.click(screen.getByRole("button", { name: "Tahsilatı tamamla" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1)); mounted.unmount();
  account = { ...account, id: "cashier-b" };
  const other = render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  await act(async () => { finish({ data: { data: { receipt_id: "receipt", receipt_number: "RCP-ACCEPTANCE", remaining_debt: "75.00" } } }); });
  expect(mocks.navigate).not.toHaveBeenCalled(); expect(mocks.toast).not.toHaveBeenCalled();
  expect(screen.getByRole("spinbutton", { name: /Ödeme tutarı/ })).toHaveValue(null); other.unmount();
  account = { ...account, id: "cashier-a" }; render(<MemoryRouter><PaymentFormPage /></MemoryRouter>);
  expect(await screen.findByText("RCP-ACCEPTANCE")).toBeInTheDocument();
});

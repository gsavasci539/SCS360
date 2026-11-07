import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SchoolPaymentReviewPage } from "../features/payment/SchoolPaymentReviewPage";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import { api } from "../lib/api";
import type { AuthUser } from "../types/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: (reason: Error) => reason.message || "İstek tamamlanamadı" }));
const id = "00000000-0000-4000-8000-000000000001", debt = "00000000-0000-4000-8000-000000000002";
const user: AuthUser = { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "actor@example.invalid", is_super_admin: false, roles: [], permissions: ["finance.read", "finance.write"], branch_ids: [] };
const row = { id, debt_id: debt, student_id: null, student_name: "Deniz Öğrenci", amount: "25.00", currency: "USD", paid_amount: "25.00", paid_currency: "USD",
  status: "PAID_REVIEW", review_reason: "BALANCE_CHANGED", provider_payment_id: "provider-reference", provider_transaction_id: null, verified_at: "2026-11-05T06:00:00Z",
  created_at: "2026-11-05T05:00:00Z", remaining_amount: "50.00", revision: "a".repeat(64), can_apply: true, can_refund: true, environment: "LIVE", payment_id: null, receipt_id: null, review_events: [] };
function page(items = [row]) { return { items, total: items.length, page: 1, page_size: 20, total_pages: 1 }; }
function open(selected = true) { return render(<MemoryRouter initialEntries={[`/finance/online-payments${selected ? `?checkout=${id}` : ""}`]}><SchoolPaymentReviewPage /></MemoryRouter>); }
function reason() { fireEvent.change(screen.getByLabelText("Kontrol açıklaması"), { target: { value: "Bankadaki tutar karşılaştırıldı" } }); }
beforeEach(() => {
  useAuthStore.setState({ user, sessionVersion: 1 }); usePlatformWorkspace.setState({ workspace: null }); sessionStorage.clear();
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page() : row } }));
});
afterEach(() => { cleanup(); vi.resetAllMocks(); sessionStorage.clear(); });

it("loads the pending-only server page and never sends actions while opening or paging", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...page(), total_pages: 2, total: 21 } } });
  open(false); expect(await screen.findByText("Deniz Öğrenci")).toBeInTheDocument();
  expect(screen.getByText("Canlı")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Listeyi yenile" }));
  fireEvent.click(await screen.findByRole("button", { name: "Sonraki sayfa" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/payments/iyzico/reviews", expect.objectContaining({ params: { page: 2, page_size: 20 } })));
  expect(api.post).not.toHaveBeenCalled();
});

it("returns a write-only actor to permitted cash entry while retaining the read actor payment list link", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["finance.write"] } }); open(false);
  expect(await screen.findByRole("link", { name: "Yeni tahsilata git" })).toHaveAttribute("href", "/finance/payments/new");
  expect(screen.queryByRole("link", { name: "Tahsilatlara dön" })).not.toBeInTheDocument(); cleanup();
  useAuthStore.setState({ user }); open(false);
  expect(await screen.findByRole("link", { name: "Tahsilatlara dön" })).toHaveAttribute("href", "/finance/payments");
  expect(screen.queryByRole("link", { name: "Yeni tahsilata git" })).not.toBeInTheDocument();
});

it("requires both native write permission and the current server eligibility flags", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["finance.read"] } }); open();
  expect(await screen.findByText(/Görüntüleme yetkisi işlem yapma yetkisi vermez/)).toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument(); cleanup();
  useAuthStore.setState({ user });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page() : { ...row, can_apply: false, can_refund: false } } }));
  open(); await screen.findByText(/uygulanabilir bir mutabakat işlemi bulunmuyor/); expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.queryByText(/Görüntüleme yetkisi işlem yapma yetkisi vermez/)).not.toBeInTheDocument();
});

it.each([
  ["COMPLETED", null, "Ödeme borca işlendi.", null],
  ["REFUNDED", "EXTERNAL_REFUND_RECORDED", "Dışarıda gerçekleşen iade kaydı tamamlandı.", "Dışarıda gerçekleşen iade kaydedildi"],
])("describes the resolved %s record without blaming a writer's permissions", async (status, reviewReason, message, reasonLabel) => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page([])
    : { ...row, status, review_reason: reviewReason, can_apply: false, can_refund: false } } }));
  open(); expect(await screen.findByText(new RegExp(message!))).toBeInTheDocument();
  if (reasonLabel) expect(screen.getByText(reasonLabel)).toBeInTheDocument();
  if (reviewReason) expect(screen.queryByText(reviewReason)).not.toBeInTheDocument();
  expect(screen.queryByText(/Görüntüleme yetkisi işlem yapma yetkisi vermez/)).not.toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument(); expect(api.post).not.toHaveBeenCalled();
});

it("translates a known review reason and keeps an unfamiliar internal code out of the interface", async () => {
  open(); expect(await screen.findByText("Borç bakiyesi değişti")).toBeInTheDocument();
  expect(screen.queryByText("BALANCE_CHANGED")).not.toBeInTheDocument(); cleanup();
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page()
    : { ...row, review_reason: "UNRECOGNIZED_INTERNAL_DETAIL" } } }));
  open(); expect(await screen.findByText("İnceleme nedeni için kayıt kontrol edilmeli")).toBeInTheDocument();
  expect(screen.queryByText("UNRECOGNIZED_INTERNAL_DETAIL")).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("retries an uncertain immutable command with the same UUID and revision without persisting reason", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")).mockImplementation(async (_path, body) => ({ data: { data: { ...row, status: "COMPLETED", can_apply: false, can_refund: false,
    review_events: [{ request_id: (body as { request_id: string }).request_id, action: "APPLY", result_status: "COMPLETED", created_at: row.created_at }] } } }));
  open(); await screen.findByRole("form"); reason(); fireEvent.submit(screen.getByRole("form"));
  fireEvent.click(await screen.findByRole("button", { name: "Aynı mutabakat isteğini tekrar dene" }));
  expect(await screen.findByText("Mutabakat isteğinin sonucu kaydedildi.")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledTimes(2);
  const original = vi.mocked(api.post).mock.calls[0][1]; expect(vi.mocked(api.post).mock.calls[1][1]).toEqual(original);
  expect(original).toEqual(expect.objectContaining({ request_id: expect.stringMatching(/^[0-9a-f-]{36}$/i), expected_revision: row.revision, action: "APPLY" }));
  expect(JSON.stringify(sessionStorage)).not.toContain("Bankadaki");
});

it("reloads stale details and waits for explicit acknowledgement without resubmitting a new revision", async () => {
  let changed = false;
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page() : changed ? { ...row, revision: "b".repeat(64), can_apply: false } : row } }));
  vi.mocked(api.post).mockImplementation(async () => { changed = true; throw { message: "Kayıt değişti", response: { status: 409 } }; });
  open(); await screen.findByRole("form"); reason(); fireEvent.submit(screen.getByRole("form"));
  fireEvent.click(await screen.findByRole("button", { name: "Güncel kaydı inceledim" }));
  await screen.findByRole("form"); expect(api.post).toHaveBeenCalledOnce();
  expect(screen.getByLabelText("Mutabakat işlemi")).toHaveValue("REFUND_RECORDED");
});

it("records only an external refund reference with exact string money actual currency and an aware date", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page() : { ...row, can_apply: false } } }));
  vi.mocked(api.post).mockImplementation(async (_path, body) => ({ data: { data: { ...row, status: "REFUNDED", can_apply: false, can_refund: false,
    review_events: [{ request_id: (body as { request_id: string }).request_id, action: "REFUND_RECORDED", result_status: "REFUNDED", created_at: row.created_at }] } } }));
  open(); await screen.findByRole("form"); reason();
  fireEvent.change(screen.getByLabelText("Dış iade referansı"), { target: { value: "BANK-REFUND-123" } });
  fireEvent.change(screen.getByLabelText("Gerçekleşen iade tarihi"), { target: { value: "2026-11-04T10:00" } });
  fireEvent.submit(screen.getByRole("form")); await screen.findByText(/Dışarıda yapılan iade kaydı doğrulandı/);
  expect(api.post).toHaveBeenCalledWith(`/payments/iyzico/checkouts/${id}/review`, expect.objectContaining({ action: "REFUND_RECORDED", refund_reference: "BANK-REFUND-123", refund_amount: "25.00", refund_currency: "USD", refunded_at: new Date("2026-11-04T10:00").toISOString() }), expect.anything());
  expect(screen.queryByText(/₺/)).not.toBeInTheDocument();
});

it("rejects malformed review metadata and keeps a pure parent out without requests", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...row, revision: "bad", amount: "NaN" } } });
  open(); expect(await screen.findByText("Online ödeme detayı doğrulanamadı.")).toBeInTheDocument(); expect(screen.queryByRole("form")).not.toBeInTheDocument(); cleanup();
  vi.mocked(api.get).mockClear(); useAuthStore.setState({ user: { ...user, permissions: ["parent.view_finances", "parent.make_payment"] } });
  open(); expect(await screen.findByText("Online ödeme incelemesi için finans yetkisi ve kurum çalışma alanı gerekir.")).toBeInTheDocument(); expect(api.get).not.toHaveBeenCalled();
});

it("drops a previous organization response when the root workspace changes", async () => {
  let resolve!: (value: unknown) => void;
  useAuthStore.setState({ user: { ...user, is_super_admin: true } });
  usePlatformWorkspace.setState({ workspace: { id: "school-a", name: "A", operatorId: user.id } });
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((done) => { resolve = done; }) as never)
    .mockResolvedValue({ data: { data: page([{ ...row, student_name: "B Öğrencisi" }]) } });
  open(false); await waitFor(() => expect(api.get).toHaveBeenCalledOnce());
  act(() => { usePlatformWorkspace.setState({ workspace: { id: "school-b", name: "B", operatorId: user.id } }); });
  await screen.findByText("B Öğrencisi");
  await act(async () => { resolve({ data: { data: page() } }); });
  expect(screen.queryByText("Deniz Öğrenci")).not.toBeInTheDocument(); expect(api.post).not.toHaveBeenCalled();
});

it("does not submit a refund amount or currency different from the verified provider proof", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page() : { ...row, can_apply: false } } }));
  open(); await screen.findByRole("form"); reason();
  fireEvent.change(screen.getByLabelText("Dış iade referansı"), { target: { value: "BANK-REFUND" } });
  fireEvent.change(screen.getByLabelText("Gerçekleşen iade tarihi"), { target: { value: "2026-11-04T10:00" } });
  fireEvent.change(screen.getByLabelText("Tam iade tutarı"), { target: { value: "25.01" } });
  fireEvent.submit(screen.getByRole("form")); await screen.findByText(/doğrulanmış sağlayıcı kaydıyla aynı olmalı/);
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Tam iade tutarı"), { target: { value: "25.00" } });
  fireEvent.change(screen.getByLabelText("İade para birimi"), { target: { value: "TRY" } });
  fireEvent.submit(screen.getByRole("form")); expect(api.post).not.toHaveBeenCalled();
});

it("allows correcting a definitive validation failure instead of retrying a locked invalid command", async () => {
  vi.mocked(api.post).mockRejectedValue({ message: "İade bilgilerini kontrol edin", response: { status: 422 } });
  open(); await screen.findByRole("form"); reason(); fireEvent.submit(screen.getByRole("form"));
  await screen.findByText("İade bilgilerini kontrol edin");
  expect(screen.getByLabelText("Kontrol açıklaması")).toBeEnabled();
  expect(screen.queryByRole("button", { name: "Aynı mutabakat isteğini tekrar dene" })).not.toBeInTheDocument();
});

it("reloads capabilities after an access rejection and does not offer an endless forbidden retry", async () => {
  let rejected = false;
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? page() : rejected ? { ...row, can_apply: false, can_refund: false } : row } }));
  vi.mocked(api.post).mockImplementation(async () => { rejected = true; throw { message: "Yetki değişti", response: { status: 403 } }; });
  open(); await screen.findByRole("form"); reason(); fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByText("Bu kayıt için uygulanabilir bir mutabakat işlemi bulunmuyor.")).toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Aynı mutabakat isteğini tekrar dene" })).not.toBeInTheDocument();
  expect(api.post).toHaveBeenCalledOnce();
});

it("closes an in-flight command and reopens the fresh read-only result while removing its stale queue row", async () => {
  let committed = false, requestId = "", resolve!: (value: unknown) => void;
  const completed = () => ({ ...row, status: "COMPLETED", can_apply: false, can_refund: false,
    review_events: [{ request_id: requestId, action: "APPLY", result_status: "COMPLETED", created_at: row.created_at }] });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: String(path).endsWith("/reviews") ? committed ? page([]) : page() : committed ? completed() : row } }));
  vi.mocked(api.post).mockImplementation((_path, body) => { requestId = (body as { request_id: string }).request_id; return new Promise((done) => { resolve = done; }) as never; });
  open(); await screen.findByRole("form"); reason(); fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
  fireEvent.click(screen.getByRole("button", { name: "Pencereyi kapat" })); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  committed = true; await act(async () => { resolve({ data: { data: completed() } }); });
  fireEvent.click(screen.getByRole("button", { name: "İncele" }));
  expect(await screen.findByRole("region", { name: "Mutabakat işlem geçmişi" })).toBeInTheDocument();
  expect(await screen.findByText("Uzlaştırma bekleyen online ödeme bulunmuyor.")).toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Listeyi yenile" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Listeyi yenile" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Listeyi yenile" })).toBeEnabled());
  expect(api.post).toHaveBeenCalledOnce();
});

it("never paints the old workspace command completion or receipt in the new workspace", async () => {
  let resolve!: (value: unknown) => void, requestId = "";
  useAuthStore.setState({ user: { ...user, is_super_admin: true } });
  usePlatformWorkspace.setState({ workspace: { id: "school-a", name: "A", operatorId: user.id } });
  vi.mocked(api.get).mockImplementation(async (path) => {
    const other = usePlatformWorkspace.getState().workspace?.id === "school-b";
    if (!String(path).endsWith("/reviews") && other) throw new Error("Bu kurumda ödeme kaydı bulunmuyor");
    return { data: { data: String(path).endsWith("/reviews") ? page([{ ...row, student_name: other ? "B Öğrencisi" : row.student_name }]) : row } };
  });
  vi.mocked(api.post).mockImplementation((_path, body) => { requestId = (body as { request_id: string }).request_id; return new Promise((done) => { resolve = done; }) as never; });
  open(); await screen.findByRole("form"); reason(); fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
  act(() => { usePlatformWorkspace.setState({ workspace: { id: "school-b", name: "B", operatorId: user.id } }); });
  await screen.findByText("B Öğrencisi"); await screen.findByText("Bu kurumda ödeme kaydı bulunmuyor");
  await act(async () => { resolve({ data: { data: { ...row, status: "COMPLETED", receipt_id: debt, can_apply: false, can_refund: false,
    review_events: [{ request_id: requestId, action: "APPLY", result_status: "COMPLETED", created_at: row.created_at }] } } }); });
  expect(screen.queryByText("Mutabakat isteğinin sonucu kaydedildi.")).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Makbuzu aç" })).not.toBeInTheDocument();
  expect(screen.queryByText("Deniz Öğrenci")).not.toBeInTheDocument(); expect(api.post).toHaveBeenCalledOnce();
});

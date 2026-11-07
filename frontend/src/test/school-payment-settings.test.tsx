import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SchoolPaymentSettings } from "../features/payment/SchoolPaymentSettings";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() }, apiMessage: (error: unknown) => error instanceof Error ? error.message : "İşlem tamamlanamadı" }));
const blank = { can_manage: true, configured: false, enabled: false, environment: null, account_id: null, revision: null,
  has_api_key: false, has_secret_key: false, callback_configured: true, portal_configured: true, encryption_configured: true,
  production_compatible: true, available: false, updated_at: null };
const configured = { ...blank, configured: true, enabled: true, environment: "LIVE", account_id: "merchant-one", revision: "revision-one",
  has_api_key: true, has_secret_key: true, available: true, updated_at: "2026-11-05T01:00:00Z" };
beforeEach(() => {
  useAuthStore.getState().setSession({ access_token: "test", refresh_token: "test-refresh", token_type: "bearer", user: {
    id: "owner", email: "owner@example.invalid", first_name: "Owner", last_name: "Test", organization_id: "school-one",
    is_super_admin: false, roles: [], permissions: [], branch_ids: [],
  } });
  vi.mocked(api.get).mockResolvedValue({ data: { data: blank } });
  vi.mocked(api.put).mockResolvedValue({ data: { data: configured } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const form = () => screen.getByRole("form", { name: "Kurum iyzico hesabı ayarları" });
async function ready() { await screen.findByRole("form", { name: "Kurum iyzico hesabı ayarları" }); }
function keys(apiKey = "private-api-key", secretKey = "private-secret-key") {
  fireEvent.change(screen.getByLabelText(/^API key/), { target: { value: apiKey } });
  fireEvent.change(screen.getByLabelText(/^Secret key/), { target: { value: secretKey } });
}
function failure(status?: number) { return Object.assign(new Error(status ? `Hata ${status}` : "Ağ sonucu belirsiz"), status ? { response: { status } } : {}); }

it("yönetici olmayan kullanıcının minimal yanıtında gizli anahtar formu açılmaz", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { can_manage: false, available: true } } });
  render(<SchoolPaymentSettings />);
  expect(await screen.findByText(/yalnız kurum sahibi/)).toBeInTheDocument();
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/^API key/)).not.toBeInTheDocument();
});

it("yeni canlı hesap ayarını açık anahtarlarla kaydeder, anahtarları temizler ve saklamaz", async () => {
  render(<SchoolPaymentSettings />); await ready();
  expect(screen.getByRole("combobox", { name: "Ödeme ortamı" })).toHaveValue("LIVE");
  expect(screen.getByText("Merchant kurulumu bekleniyor")).toBeInTheDocument();
  keys(); fireEvent.click(screen.getByLabelText("Online öğrenci ödemesini etkinleştir"));
  const local = vi.spyOn(Storage.prototype, "setItem"); local.mockClear();
  try {
    fireEvent.submit(form()); await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.put).mock.calls[0][1]).toMatchObject({ expected_revision: null, environment: "LIVE", enabled: true,
      replace_account: false, api_key: "private-api-key", secret_key: "private-secret-key", request_id: expect.stringMatching(/^[0-9a-f-]{36}$/i) });
    expect(await screen.findByText(/Ödeme ayarları kaydedildi/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^API key/)).toHaveValue(""); expect(screen.getByLabelText(/^Secret key/)).toHaveValue("");
    expect(local).not.toHaveBeenCalled();
  } finally { local.mockRestore(); }
});

it("mevcut hesabın boş anahtarlarını göndermez ve ortam değişiminde açık onay ister", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: configured } });
  render(<SchoolPaymentSettings />); await ready();
  expect(screen.getByLabelText(/^API key/)).toHaveValue("");
  fireEvent.change(screen.getByRole("combobox", { name: "Ödeme ortamı" }), { target: { value: "SANDBOX" } });
  fireEvent.submit(form()); expect(await screen.findByRole("alert")).toHaveTextContent(/açıkça onaylayın/);
  expect(api.put).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("combobox", { name: "Ödeme ortamı" }), { target: { value: "LIVE" } });
  fireEvent.click(screen.getByLabelText("Online öğrenci ödemesini etkinleştir")); fireEvent.submit(form());
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  const saved = vi.mocked(api.put).mock.calls[0][1] as Record<string, unknown>;
  expect(saved).toMatchObject({ expected_revision: "revision-one", enabled: false, replace_account: false });
  expect(saved).not.toHaveProperty("api_key"); expect(saved).not.toHaveProperty("secret_key");
});

it("sonucu bilinmeyen kaydı kilitler ve değişmeyen gövdeyle aynı UUID üzerinden tekrar dener", async () => {
  vi.mocked(api.put).mockRejectedValueOnce(failure());
  render(<SchoolPaymentSettings />); await ready(); keys(); fireEvent.submit(form());
  const retry = await screen.findByRole("button", { name: "Aynı kaydı tekrar dene" });
  expect(screen.getByLabelText(/^API key/)).toBeDisabled();
  fireEvent.click(retry); await waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.put).mock.calls[1][1]).toBe(vi.mocked(api.put).mock.calls[0][1]);
  expect(Object.isFrozen(vi.mocked(api.put).mock.calls[0][1])).toBe(true);
});

it("409 sonrası son revizyonu gösterir, kullanıcı incelemeden eski formu veya yeni UUID'yi göndermez", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ data: { data: configured } }).mockResolvedValue({ data: { data: { ...configured, revision: "revision-two", environment: "SANDBOX" } } });
  vi.mocked(api.put).mockRejectedValueOnce(failure(409));
  render(<SchoolPaymentSettings />); await ready(); keys("replacement-api", "replacement-secret"); fireEvent.submit(form());
  const review = await screen.findByRole("button", { name: "Son durumu inceledim; formu yenile" });
  await waitFor(() => expect(review).toBeEnabled());
  expect(screen.getByRole("combobox", { name: "Ödeme ortamı" })).toHaveValue("LIVE");
  fireEvent.submit(form()); expect(api.put).toHaveBeenCalledTimes(1);
  fireEvent.click(review); expect(screen.getByRole("combobox", { name: "Ödeme ortamı" })).toHaveValue("SANDBOX");
  expect(screen.getByLabelText(/^API key/)).toHaveValue(""); expect(screen.getByLabelText(/^Secret key/)).toHaveValue("");
});

it("hesap değişiminde iki anahtarı ve açık değiştirme onayını birlikte gönderir", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: configured } });
  render(<SchoolPaymentSettings />); await ready();
  fireEvent.change(screen.getByRole("combobox", { name: "Ödeme ortamı" }), { target: { value: "SANDBOX" } });
  fireEvent.click(screen.getByLabelText("Yeni merchant hesabı veya farklı ortam kullanacağım"));
  fireEvent.submit(form()); expect(await screen.findByRole("alert")).toHaveTextContent(/birlikte girilmelidir/);
  expect(api.put).not.toHaveBeenCalled();
  keys("new-account-api", "new-account-secret"); fireEvent.submit(form());
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.put).mock.calls[0][1]).toMatchObject({ expected_revision: "revision-one", environment: "SANDBOX",
    replace_account: true, api_key: "new-account-api", secret_key: "new-account-secret" });
});

it("409 sonrası güncel sunucu kaydı alınamazsa eski revizyona geri dönülmesine izin vermez", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ data: { data: configured } }).mockRejectedValue(new Error("Güncel ayarlar alınamadı"));
  vi.mocked(api.put).mockRejectedValueOnce(failure(409));
  render(<SchoolPaymentSettings />); await ready(); fireEvent.submit(form());
  const review = await screen.findByRole("button", { name: "Son durumu inceledim; formu yenile" });
  await screen.findByText("Güncel ayarlar alınamadı");
  expect(review).toBeDisabled(); expect(screen.getByLabelText(/^API key/)).toBeDisabled();
  expect(api.put).toHaveBeenCalledTimes(1);
});

it("422 doğrulamasından sonra form düzeltilebilir; yeniden yükleme gizli anahtarları taşımaz", async () => {
  vi.mocked(api.put).mockRejectedValueOnce(failure(422));
  const mounted = render(<SchoolPaymentSettings />); await ready(); keys(); fireEvent.submit(form());
  await screen.findByRole("alert"); await waitFor(() => expect(screen.getByLabelText(/^API key/)).toBeEnabled());
  expect(screen.queryByRole("button", { name: "Aynı kaydı tekrar dene" })).not.toBeInTheDocument();
  mounted.unmount(); render(<SchoolPaymentSettings />); await ready();
  expect(screen.getByLabelText(/^API key/)).toHaveValue(""); expect(screen.getByLabelText(/^Secret key/)).toHaveValue("");
});

it("platform yöneticisi kurum seçmeden merchant sorgusu yapmaz", () => {
  const user = useAuthStore.getState().user!; useAuthStore.getState().setUser({ ...user, is_super_admin: true });
  usePlatformWorkspace.getState().select(null);
  render(<SchoolPaymentSettings />);
  expect(screen.getByText("Önce kurum çalışma alanını seçin.")).toBeInTheDocument();
  expect(api.get).not.toHaveBeenCalled();
});

it("platform çalışma alanı değişince önceki kurumun anahtar taslağı temizlenir", async () => {
  const user = useAuthStore.getState().user!; useAuthStore.getState().setUser({ ...user, is_super_admin: true });
  usePlatformWorkspace.getState().select({ id: "school-one", name: "Birinci okul", operatorId: user.id });
  render(<SchoolPaymentSettings />); await ready(); keys("first-school-private", "first-school-secret");
  act(() => usePlatformWorkspace.getState().select({ id: "school-two", name: "İkinci okul", operatorId: user.id }));
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2)); await ready();
  expect(screen.getByLabelText(/^API key/)).toHaveValue(""); expect(screen.getByLabelText(/^Secret key/)).toHaveValue("");
});

it("bozuk yönetim yanıtı formu açmaz ve görünür hata verir", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...configured, revision: [] } } });
  render(<SchoolPaymentSettings />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Ödeme ayarlarının yanıtı geçersiz");
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
});

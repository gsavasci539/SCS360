import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { SettingsPage } from "../features/settings/SettingsPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() }, apiMessage: () => "Servis yanıt vermiyor" }));
const existing = [
  { provider: "SMTP", is_active: false, config: { host: "smtp.example.invalid", port: 465, username: "school", password: "***", options: { tls: true } } },
  { provider: "NETGSM", is_active: true, config: { apiKey: "***", sender: "School" } },
  { provider: "META_WHATSAPP", is_active: false, config: { phone_id: "phone-one", accessToken: "***" } },
];
let records: unknown;
let integrationFailure = false;
function view() { render(<MemoryRouter><ToastProvider><SettingsPage initialSection="integrations" /></ToastProvider></MemoryRouter>); }
beforeEach(() => {
  records = existing; integrationFailure = false;
  useAuthStore.getState().setSession({ access_token: "test", refresh_token: "test", token_type: "bearer", user: {
    id: "writer", email: "writer@test.invalid", first_name: "Settings", last_name: "Writer", organization_id: "school",
    is_super_admin: false, roles: [], permissions: ["settings.read", "settings.write"], branch_ids: [],
  } });
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/settings/integrations" && integrationFailure) throw new Error("offline");
    return { data: { data: path === "/settings/integrations" ? records : { school_name: "Our school" } } };
  });
  vi.mocked(api.put).mockResolvedValue({ data: { success: true } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("yalnız değiştirilen sağlayıcı alanını kaydeder; pasif durumu ve bilinmeyen ayarları göndermez", async () => {
  view();
  const host = await screen.findByLabelText("SMTP sunucusu");
  expect(host).toHaveValue("smtp.example.invalid");
  expect(screen.getByRole("button", { name: "SMTP ayarlarını kaydet" })).toBeDisabled();
  fireEvent.change(host, { target: { value: "new.example.invalid" } });
  fireEvent.click(screen.getByRole("button", { name: "SMTP ayarlarını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  expect(api.put).toHaveBeenCalledWith("/settings/integrations", { provider: "SMTP", config: { host: "new.example.invalid" } });
  expect(await screen.findByText("SMTP ayarları kaydedildi")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "SMTP ayarlarını kaydet" })).toBeDisabled();
  expect(screen.queryByText(/şifrelenerek/)).not.toBeInTheDocument();
});

it("başarısız entegrasyon GET'inde boş ayar yazmaz ve yeniden yüklemeyi sunar", async () => {
  integrationFailure = true; view();
  expect(await screen.findByRole("alert")).toHaveTextContent("Servis yanıt vermiyor");
  expect(screen.queryByLabelText("SMTP sunucusu")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Değişiklikleri kaydet" })).not.toBeInTheDocument();
  expect(api.put).not.toHaveBeenCalled();
  integrationFailure = false;
  fireEvent.click(screen.getByRole("button", { name: "Entegrasyonları yeniden yükle" }));
  expect(await screen.findByLabelText("SMTP sunucusu")).toHaveValue("smtp.example.invalid");
});

it("hatalı yanıt öğelerini form varsayılanlarına çevirmeden güvenle reddeder", async () => {
  records = [null, ...existing]; view();
  expect(await screen.findByRole("alert")).toHaveTextContent("Entegrasyon yanıtı geçerli değil");
  expect(screen.queryByLabelText("SMTP sunucusu")).not.toBeInTheDocument();
  expect(api.put).not.toHaveBeenCalled();
});

it("eski bozuk sağlayıcıyı inceleme için kapatır, diğer sağlayıcı düzenlemesi onu değiştirmez", async () => {
  records = [existing[0], { provider: "META_WHATSAPP", is_active: true, config: null, requires_review: true }];
  view();
  expect(await screen.findByText(/Eski kayıt inceleme gerektiriyor/)).toBeInTheDocument();
  expect(screen.getByLabelText("WhatsApp telefon ID")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("SMTP kullanıcı adı"), { target: { value: "new-user" } });
  fireEvent.click(screen.getByRole("button", { name: "SMTP ayarlarını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  expect(api.put).toHaveBeenCalledWith("/settings/integrations", { provider: "SMTP", config: { username: "new-user" } });
});

it("eski alanın JSON türünü boş metinle değiştirmez ve SMS seçimiyle kayıt oluşturmaz", async () => {
  records = [{ ...existing[0], config: { ...existing[0].config, host: { legacy: true } } }, ...existing.slice(1)];
  view();
  expect(await screen.findByLabelText("SMTP sunucusu")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("SMS sağlayıcısı"), { target: { value: "TWILIO" } });
  expect(api.put).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("SMTP portu"), { target: { value: "2525" } });
  fireEvent.click(screen.getByRole("button", { name: "SMTP ayarlarını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  expect(api.put).toHaveBeenCalledWith("/settings/integrations", { provider: "SMTP", config: { port: "2525" } });
});

it("eksik sağlayıcıyı yalnız girilen alanla oluşturur; genel kaydet entegrasyon yazmaz", async () => {
  records = []; view();
  expect(await screen.findByLabelText("SMTP portu")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("SMTP sunucusu"), { target: { value: "new.example.invalid" } });
  fireEvent.click(screen.getByRole("button", { name: "SMTP ayarlarını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  expect(api.put).toHaveBeenCalledWith("/settings/integrations", { provider: "SMTP", config: { host: "new.example.invalid" } });
  fireEvent.click(screen.getByRole("button", { name: /Genel.*Kurum yapılandırması/ }));
  fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.put).mock.calls[1][0]).toBe("/settings");
});

it("salt okumada entegrasyon yazma düğmeleri açılmaz", async () => {
  useAuthStore.setState((state) => ({ user: state.user ? { ...state.user, permissions: ["settings.read"] } : null }));
  view();
  expect(await screen.findByLabelText("SMTP sunucusu")).toBeDisabled();
  expect(screen.queryByRole("button", { name: /ayarlarını kaydet/ })).not.toBeInTheDocument();
  expect(within(screen.getByRole("heading", { name: "Servis bağlantıları" }).parentElement!).getByText(/Gönderim kurulumu ayrıca/)).toBeInTheDocument();
  expect(api.put).not.toHaveBeenCalled();
});

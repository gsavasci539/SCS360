import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { AxiosRequestConfig } from "axios";
import { ToastProvider } from "../components/Toast";
import { GuidancePage } from "../features/guidance/GuidancePage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: () => "Kayıt kaydedilemedi" }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.com", organization_id: "org", is_super_admin: false, roles: [], permissions: ["guidance.read", "guidance.write"], branch_ids: [] };
const summary = { total_sessions: 500, total_notes: 21, active_cases: 7, total_incidents: 30 };
const studentParameter = (config?: AxiosRequestConfig) =>
  (config?.params as { student_id?: string } | undefined)?.student_id;
beforeEach(() => {
  useAuthStore.setState({ user: manager });
  vi.mocked(api.get).mockImplementation(async (path, config) => ({
    data: { data: path === "/guidance/options" ? {
      students: [{ id: "child", name: "Deniz Test" }], counselors: [{ id: "manager", name: "Test Danışman" }], today: "2026-11-03",
    } : path === "/guidance/summary" ? { ...summary, student_id: studentParameter(config) } : path === "/guidance/incidents" ?
      [{ id: "incident", student_id: "child", student_name: "Deniz Test", description: "Gerçek olay", resolved: false, severity: "MINOR" }] : [] },
  }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } });
  vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = () => render(<MemoryRouter><ToastProvider><GuidancePage /></ToastProvider></MemoryRouter>);

it("salt okuma hesabında gerçek toplam ve ayrıntı bağlantısı görünür, yazma kontrolleri gizlidir", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["guidance.read"] } }); open();
  await screen.findByText(/Erişime açık görüşme: 500/);
  expect(screen.getByRole("link", { name: "Deniz Test" })).toHaveAttribute("href", "/guidance?student=child");
  expect(screen.queryByRole("button", { name: "Çözüldü olarak kaydet", hidden: true })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Rehberlik işlemleri" })).not.toBeInTheDocument();
});

it("öğrenci değiştiğinde eski sayacı gizler ve farklı kapsamdaki yanıtı reddeder", async () => {
  const original = vi.mocked(api.get).getMockImplementation()!;
  let finish = () => {};
  vi.mocked(api.get).mockImplementation((path, config) => {
    if (path !== "/guidance/summary" || studentParameter(config) !== "child") return original(path, config);
    return new Promise((resolve) => {
      finish = () => resolve({ data: { data: { ...summary, student_id: "başka-öğrenci", total_sessions: 3 } } });
    });
  });
  open();
  const panel = within(screen.getByRole("region", { name: "Rehberlik özeti" }));
  expect(panel.getByRole("status")).toHaveTextContent("Rehberlik özeti yükleniyor");
  expect(panel.queryByText(/Erişime açık görüşme:/)).not.toBeInTheDocument();
  await panel.findByText(/Erişime açık görüşme: 500/);
  await screen.findByRole("option", { name: "Deniz Test" });
  fireEvent.change(screen.getByLabelText("Rehberlik öğrencisi"), { target: { value: "child" } });
  expect(panel.getByRole("status")).toBeInTheDocument();
  expect(panel.queryByText(/Erişime açık görüşme:/)).not.toBeInTheDocument();
  finish();
  expect(await panel.findByText("Rehberlik verileri seçili öğrenci kapsamıyla eşleşmiyor.")).toBeInTheDocument();
  expect(panel.queryByText(/Erişime açık görüşme:/)).not.toBeInTheDocument();
});

it("öğrenci ve gerçek danışman seçimiyle not oluşturur; hata taslağı korur", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("failed")); open();
  await screen.findByRole("option", { name: "Deniz Test" });
  fireEvent.change(screen.getByLabelText("Rehberlik öğrencisi"), { target: { value: "child" } });
  await screen.findByRole("option", { name: "Test Danışman" });
  const form = screen.getByRole("form", { name: "Danışman notu oluştur" });
  fireEvent.change(within(form).getByLabelText("Danışman notu"), { target: { value: "Kalıcı gözlem" } });
  fireEvent.change(within(form).getByLabelText("Gizlilik düzeyi"), { target: { value: "CONFIDENTIAL" } });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Notu kaydet" })).toBeEnabled());
  fireEvent.click(within(form).getByRole("button", { name: "Notu kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/guidance/notes", { student_id: "child", counselor_id: "manager", confidentiality_level: "CONFIDENTIAL", note_type: "OBSERVATION", content: "Kalıcı gözlem", tags: [] }));
  expect(await screen.findByText("Kayıt kaydedilemedi")).toBeInTheDocument();
  expect(within(form).getByLabelText("Danışman notu")).toHaveValue("Kalıcı gözlem");
});

it("olay çözüm notunu URL yerine JSON gövdesinde gönderir", async () => {
  open(); const region = await screen.findByRole("region", { name: "Davranış olayları" });
  await within(region).findByText("Olay ayrıntısı"); fireEvent.click(within(region).getByText("Olay ayrıntısı"));
  fireEvent.change(within(region).getByLabelText("Çözüm notu"), { target: { value: "Çözüm kaydı" } });
  fireEvent.click(within(region).getByRole("button", { name: "Çözüldü olarak kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/guidance/incidents/incident/resolve", { resolution_notes: "Çözüm kaydı" }));
});

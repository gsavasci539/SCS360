import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { ConsentsPage } from "../features/consents/ConsentsPage";
import { ParentConsents } from "../features/parent/ParentConsents";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() }, apiMessage: () => "Karar kaydedilemedi" }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.com", organization_id: "org", is_super_admin: false, roles: [], permissions: ["consents.read", "consents.write"], branch_ids: [] };
const doc = { id: "doc", organization_id: "org", title: "Gezi koşulları", content: "Ayrıntılı gezi kapsamı", version: "2.0", content_sha256: "hash", is_active: true, can_decide: true, consent_status: "PENDING", effective_date: "2026-11-03" };
beforeEach(() => {
  useAuthStore.setState({ user: manager });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/consents/options" ? { organizations: [{ id: "org", name: "Kurum" }], students: [{ id: "child", name: "Çocuk Test" }], parents: [{ id: "parent", name: "Veli Test" }] } : path === "/consents/consent-summary" ? { total: 214, approved: 200, rejected: 14 } : path === "/consents/student-consents" ? [] : [doc] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("salt okuma hesabı belge metnini görür, yönetim seçeneklerini istemez", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["consents.read"] } });
  render(<ToastProvider><ConsentsPage /></ToastProvider>);
  await screen.findByText(/Kayıtlı karar: 214/);
  expect(await screen.findByText("Ayrıntılı gezi kapsamı")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Belgeyi oluştur" })).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/consents/options")).toBe(false);
});

it("veli açık okuma kabulü ve ad olmadan karar veremez; güncel sürümü gönderir", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["parent.view_children", "parent.give_consent"] } });
  render(<ParentConsents studentId="child" />);
  const approve = await screen.findByRole("button", { name: "Onaylıyorum", hidden: true });
  expect(approve).toBeDisabled();
  fireEvent.click(screen.getByText("Belgenin tam metnini oku"));
  fireEvent.change(screen.getByLabelText("Adınız ve soyadınız"), { target: { value: " Veli Test " } });
  expect(approve).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(approve);
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/parent/child/child/consents/doc", { consent_status: "APPROVED", acknowledged: true, document_version: "2.0", content_sha256: "hash", signed_name: "Veli Test" }));
});

it("yazma hakkı olmayan veli metni okur ve karar hatası taslağı korur", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["parent.view_children"] } });
  const view = render(<ParentConsents studentId="child" />);
  expect(await screen.findByText("Bu hesap için karar kaydetme yetkisi tanımlı değil.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Onaylıyorum", hidden: true })).not.toBeInTheDocument();
  view.unmount();
  useAuthStore.setState({ user: { ...manager, permissions: ["parent.give_consent"] } });
  vi.mocked(api.post).mockRejectedValue(new Error("failure"));
  render(<ParentConsents studentId="child" />);
  await screen.findByText("Belgenin tam metnini oku"); fireEvent.click(screen.getByText("Belgenin tam metnini oku"));
  fireEvent.change(screen.getByLabelText("Adınız ve soyadınız"), { target: { value: "Veli Test" } });
  fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(screen.getByRole("button", { name: "Onay vermiyorum" }));
  expect(await screen.findByText("Karar kaydedilemedi")).toBeInTheDocument();
  expect(screen.getByLabelText("Adınız ve soyadınız")).toHaveValue("Veli Test");
});

it("yönetici belge oluşturur ve öğrencinin kayıtlı velisini seçer", async () => {
  render(<ToastProvider><ConsentsPage /></ToastProvider>);
  await screen.findByRole("option", { name: "Kurum" });
  fireEvent.change(screen.getByLabelText("Belge başlığı"), { target: { value: "Yeni izin" } });
  fireEvent.change(screen.getByLabelText("Yürürlük tarihi"), { target: { value: "2026-11-03" } });
  fireEvent.change(screen.getByLabelText("Belgenin tam metni"), { target: { value: "Yeni koşullar" } });
  fireEvent.click(screen.getByRole("button", { name: "Belgeyi oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/consents/documents", expect.objectContaining({ title: "Yeni izin", organization_id: "org", content: "Yeni koşullar" })));
  await waitFor(() => expect(screen.getByRole("button", { name: "Yazılı veli kararı kaydet" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Yazılı veli kararı kaydet" }));
  fireEvent.change(screen.getByLabelText("Öğrenci"), { target: { value: "child" } });
  await screen.findByRole("option", { name: "Veli Test" });
  const form = screen.getByRole("region", { name: "Yazılı veli kararı" });
  fireEvent.change(within(form).getByLabelText("Kararı veren veli"), { target: { value: "parent" } });
  fireEvent.click(within(form).getByRole("button", { name: "Veli kararını kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/consents/student-consents", expect.objectContaining({ student_id: "child", parent_id: "parent", consent_method: "PAPER", consent_document_id: "doc" })));
});

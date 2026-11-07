import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { DismissalPage } from "../features/security/DismissalPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, apiMessage: () => "Teslim isteği tamamlanamadı" }));
const user: AuthUser = { id: "desk", email: "desk@test.invalid", first_name: "Pickup", last_name: "Desk", organization_id: "org", is_super_admin: false, roles: [], branch_ids: [], permissions: ["dismissal.read", "dismissal.write"] };
const grant = { id: "grant", student_id: "child", student_name: "Deniz Kabul", authorized_person_name: "Yetkili Yetişkin", authorized_person_id: "TEST-DOC-001", photo_url: "/private/preserved.svg", status: "ACTIVE", effective_status: "ACTIVE", valid_from: "2026-11-03" };
beforeEach(() => {
  useAuthStore.setState({ user });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/dismissal/options" ? { students: [{ id: "child", name: "Deniz Kabul", active: true }], today: "2026-11-03" } : path === "/dismissal/authorizations" ? [grant] : path === "/dismissal/summary" ? { total_pickups: 215, unique_students: 201, valid_authorizations: 300 } : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: {} } }); vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = (entry = "/dismissal") => render(<MemoryRouter initialEntries={[entry]}><ToastProvider><DismissalPage /></ToastProvider></MemoryRouter>);

it("salt okuma kullanıcıda gerçek toplamı ve maskeli kimliği gösterir, yazma düğmelerini gizler", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["dismissal.read"] } }); open();
  await screen.findByText("•••• -001");
  expect(screen.getByLabelText("Teslim özeti")).toHaveTextContent("Seçili gün teslim kaydı: 215");
  expect(screen.queryByRole("region", { name: "Teslim işlemleri" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Teslim yetkisini iptal et", hidden: true })).not.toBeInTheDocument();
  expect(api.get).not.toHaveBeenCalledWith("/students");
});

it("başarısız yetki oluşturma tekrarında aynı UUID ve taslak korunur", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")); open("/dismissal?student=child");
  await screen.findByRole("option", { name: "Deniz Kabul" });
  const form = screen.getByRole("form", { name: "Teslim yetkisi oluştur" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Teslim yetkisini kaydet" })).toBeEnabled());
  fireEvent.change(within(form).getByLabelText("Yetkili yetişkin adı"), { target: { value: "Korunacak yetişkin" } });
  fireEvent.change(within(form).getByLabelText("Yetkili kimlik belgesi numarası"), { target: { value: "TEST-NEW-ID" } });
  fireEvent.click(within(form).getByRole("button", { name: "Teslim yetkisini kaydet" }));
  await screen.findByText("Teslim isteği tamamlanamadı");
  expect(within(form).getByLabelText("Yetkili yetişkin adı")).toHaveValue("Korunacak yetişkin");
  fireEvent.click(within(form).getByRole("button", { name: "Teslim yetkisini kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(vi.mocked(api.post).mock.calls[1]);
});

it("kimlik numarasını otomatik doldurmaz, eşleşmeyen teslimi başarıya çevirmez", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { data: { authorized: false, message: "Kimlik eşleşmedi" } } }); open("/dismissal?student=child");
  const form = screen.getByRole("form", { name: "Öğrenci teslimini kaydet" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Kimliği doğrula ve teslimi kaydet" })).toBeEnabled());
  expect(within(form).getByLabelText("Teslim alanın kimlik belgesi numarası")).toHaveValue("");
  fireEvent.change(within(form).getByLabelText("Teslim alanın kimlik belgesi numarası"), { target: { value: "WRONG-ID" } });
  fireEvent.click(within(form).getByRole("button", { name: "Kimliği doğrula ve teslimi kaydet" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Kimlik eşleşmedi");
  const body = vi.mocked(api.post).mock.calls[0][1];
  expect(body).toEqual(expect.objectContaining({ student_id: "child", pickup_person_id: "WRONG-ID", request_id: expect.any(String) }));
  expect(body).not.toHaveProperty("pickup_person_name"); expect(body).not.toHaveProperty("verified_by");
});

it("yetki düzenlemede fotoğraf ve kimlik bilgisi korunur, kaydetme doğru kayda gider", async () => {
  open(); const table = screen.getByRole("region", { name: "Teslim yetkileri" });
  await within(table).findByText("Yetkiyi aç"); fireEvent.click(within(table).getByText("Yetkiyi aç"));
  fireEvent.click(within(table).getByRole("button", { name: "Yetkiyi düzenle" }));
  const form = screen.getByRole("form", { name: "Teslim yetkisi oluştur" });
  await waitFor(() => expect(within(form).getByRole("button", { name: "Yetki değişikliğini kaydet" })).toBeEnabled());
  expect(within(form).getByLabelText("Yetkili fotoğraf bağlantısı")).toHaveValue("/private/preserved.svg");
  fireEvent.change(within(form).getByLabelText("Yetkili telefonu"), { target: { value: "05000000000" } });
  fireEvent.click(within(form).getByRole("button", { name: "Yetki değişikliğini kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/dismissal/authorizations/grant", expect.objectContaining({ student_id: "child", authorized_person_id: "TEST-DOC-001", photo_url: "/private/preserved.svg", phone: "05000000000" })));
});

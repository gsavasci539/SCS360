import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { UserCreatePage } from "../features/users/UserCreatePage";
import { UserDetailPage } from "../features/users/UserDetailPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() }, apiMessage: () => "Erişim kaydedilemedi" }));
const user: AuthUser = { id: "owner", first_name: "Owner", last_name: "Test", email: "owner@example.com", is_super_admin: false, organization_id: "school", roles: [], permissions: ["users.read", "users.write"], branch_ids: [] };
beforeEach(() => {
  useAuthStore.setState({ user });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/users/staff" ? { id: "staff", organization_id: "school", first_name: "New", last_name: "Staff", email: "staff@example.com", status: "ACTIVE" }
    : path === "/users/options" ? { organizations: [{ id: "school", name: "Okul" }], roles: [{ id: "teacher", name: "Öğretmen" }], branches: [{ id: "branch", name: "Ana Şube" }] } : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "staff" } } }); vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = (create = false) => render(<MemoryRouter initialEntries={[create ? "/users/new" : "/users/staff"]}><Routes><Route path="/users/new" element={<UserCreatePage />} /><Route path="/users/:id" element={<UserDetailPage />} /></Routes></MemoryRouter>);

it("standart rol tamamlama, kaydedilmemiş rol ve şube seçimlerini silmez", async () => {
  useAuthStore.setState({ user: { ...user, roles: [{ id: "owner-role", name: "Sahip", slug: "owner" }], permissions: [...user.permissions, "role.write"] } });
  open(); const role = await screen.findByRole("checkbox", { name: "Öğretmen" });
  fireEvent.click(role); fireEvent.click(screen.getByRole("button", { name: "Eksik standart rolleri ekle" }));
  await screen.findByText("Eksik standart kurum rolleri tamamlandı.");
  expect(api.post).toHaveBeenCalledWith("/users/role-catalog", { organization_id: "school" }); expect(role).toBeChecked();
});

it("okul sahibi kurum UUID'si girmeden hesap oluşturur ve erişim ataması için profile gider", async () => {
  open(true); expect(screen.queryByLabelText("Kurum")).not.toBeInTheDocument();
  for (const [label, value] of [["Ad", "New"], ["Soyad", "Staff"], ["E-posta", "staff@example.com"], ["Başlangıç parolası", "AcceptancePass1!"]]) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Kullanıcıyı oluştur" }));
  await screen.findByRole("heading", { name: "New Staff" });
  expect(vi.mocked(api.post).mock.calls[0][1]).not.toHaveProperty("organization_id");
  expect(await screen.findByRole("form", { name: "Kullanıcı erişimini düzenle" })).toBeInTheDocument();
});

it("rol ve şube seçimleri tek istekte kaydedilir; salt okumada yazma formu sunulmaz", async () => {
  open(); await screen.findByLabelText("Öğretmen"); fireEvent.click(screen.getByLabelText("Öğretmen")); fireEvent.click(screen.getByLabelText("Ana Şube"));
  fireEvent.click(screen.getByRole("button", { name: "Erişimi kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/users/staff/access", { role_ids: ["teacher"], branch_ids: ["branch"] }));
  await screen.findByRole("status"); cleanup(); useAuthStore.setState({ user: { ...user, permissions: ["users.read"] } }); open();
  await screen.findByRole("heading", { name: "New Staff" }); expect(screen.queryByRole("button", { name: "Erişimi kaydet" })).not.toBeInTheDocument();
});

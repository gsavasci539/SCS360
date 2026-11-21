import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AccountDialog } from "../components/AccountDialog";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
  apiMessage: (error: Error) => error.message,
}));

const user: AuthUser = { id: "account", first_name: "İlk", last_name: "Soyad", email: "initial@example.com",
  phone: null, organization_id: "org", is_super_admin: false, roles: [], permissions: [], branch_ids: ["branch"] };
const set = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));

beforeEach(() => { useAuthStore.setState({ user }); });
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("keeps the draft and account unchanged until a matching profile readback arrives", async () => {
  const onSaved = vi.fn();
  vi.mocked(api.put).mockResolvedValue({ data: { success: true, data: { id: user.id, email: "next@example.com" } } });
  vi.mocked(api.get).mockResolvedValueOnce({ data: { success: true, data: user } })
    .mockResolvedValueOnce({ data: { success: true, data: { ...user, first_name: "Yeni", email: "next@example.com" } } });
  render(<AccountDialog user={user} mode="profile" onClose={vi.fn()} onSaved={onSaved} />);
  set("Ad", " Yeni ");
  set("E-posta", "next@example.com");
  set("Mevcut şifre", "current password");
  submit();
  expect(await screen.findByRole("alert")).toHaveTextContent("Kaydedilen profil doğrulanamadı.");
  expect(api.put).toHaveBeenCalledWith("/auth/me", { first_name: "Yeni", last_name: "Soyad", phone: null,
    email: "next@example.com", current_password: "current password" });
  expect(useAuthStore.getState().user).toEqual(user);
  expect(screen.getByLabelText("Ad")).toHaveValue(" Yeni ");
  expect(onSaved).not.toHaveBeenCalled();
  submit();
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith("profile"));
  expect(useAuthStore.getState().user).toMatchObject({ first_name: "Yeni", branch_ids: ["branch"] });
});

it("requires a successful acknowledgement for the current account before signing out", async () => {
  const onSaved = vi.fn();
  vi.mocked(api.post).mockResolvedValueOnce({ data: { success: true, data: { id: "different" } } })
    .mockResolvedValueOnce({ data: { success: true, data: { id: user.id } } });
  render(<AccountDialog user={user} mode="password" onClose={vi.fn()} onSaved={onSaved} />);
  set("Mevcut şifre", "current password");
  set("Yeni şifre", "updated password");
  set("Yeni şifre (tekrar)", "updated password");
  submit();
  expect(await screen.findByRole("alert")).toHaveTextContent("Şifre değişikliği doğrulanamadı.");
  expect(useAuthStore.getState().user).toBe(user);
  submit();
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith("password"));
  expect(useAuthStore.getState().user).toBeNull();
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { RolesPage } from "../features/roles/RolesPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));

const user: AuthUser = { id: "test-delegate", organization_id: "test-organization", first_name: "Test", last_name: "Delegate",
  email: "delegate@test.invalid", is_super_admin: false, roles: [], permissions: ["role.read", "role.write"], branch_ids: [] };
const role = { id: "test-role", name: "Kurum rolü", slug: "institution", description: null, organization_id: user.organization_id, is_system: false };
const attendance = { id: "attendance", code: "attendance.read", name: "Yoklama okuma", module: "attendance", assignable: true };
const finance = { id: "finance", code: "finance.read", name: "Finans okuma", module: "finance", assignable: false };

beforeEach(() => useAuthStore.setState({ user }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("yalnız atanabilir izinleri açar ve kalıcı matrisi ayrı okuma ile doğrular", async () => {
  let saved = [finance];
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { success: true, data:
    path === "/roles" ? [role] : path === "/permissions" ? [attendance, finance] : saved } }));
  vi.mocked(api.put).mockResolvedValue({ data: { success: true, data: { role_id: role.id, permission_ids: ["attendance", "finance"] } } });
  render(<ToastProvider><RolesPage /></ToastProvider>);
  const control = await screen.findByRole("checkbox", { name: attendance.name });
  expect(screen.getByRole("checkbox", { name: finance.name })).toBeDisabled();
  fireEvent.click(control);
  fireEvent.click(screen.getByRole("button", { name: "Matrisi kaydet" }));
  await screen.findByText("Rol izinleri doğrulanamadı");
  expect(control).toBeChecked();
  expect(screen.queryByText("Rol izinleri doğrulandı")).not.toBeInTheDocument();
  saved = [finance, attendance];
  fireEvent.click(screen.getByRole("button", { name: "Matrisi kaydet" }));
  await screen.findByText("Rol izinleri doğrulandı");
  expect(api.put).toHaveBeenCalledWith("/roles/test-role/permissions",
    { permission_ids: ["finance", "attendance"], expected_permission_ids: ["finance"] });
  await waitFor(() => expect(screen.getByRole("button", { name: "Matrisi kaydet" })).toBeDisabled());
});

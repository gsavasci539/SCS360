import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { InventoryPage } from "../features/inventory/InventoryPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.com", organization_id: "org", is_super_admin: false,
  roles: [], permissions: ["inventory.read", "inventory.write"], branch_ids: [] };
const open = () => render(<ToastProvider><InventoryPage /></ToastProvider>);
beforeEach(() => {
  useAuthStore.setState({ user: manager });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/inventory/options" ? {
    branches: [{ id: "branch", name: "Merkez" }], locations: [], items: [{ id: "item", name: "Tablet", code: "PC-1" }], users: [{ id: "teacher", name: "Işıl Öğretmen" }],
  } : path === "/ai/inventory-analysis" ? { total_items: 300, assigned_count: 20, available_count: 280, pending_maintenance: 0 } :
    path === "/inventory/items" ? Array.from({ length: 21 }, (_, index) => ({ id: "item-" + index, item_code: "PC-" + index, item_name: "Tablet " + index, status: "ACTIVE" })) : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "saved" } } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("salt okuma yetkisinde gerçek toplamı gösterir, sayfalar ve yazma seçeneklerini istemez", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["inventory.read"] } });
  open();
  await screen.findByText("300");
  expect(screen.queryByRole("region", { name: "Envanter işlemleri" })).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/inventory/options")).toBe(false);
  fireEvent.click(within(screen.getByLabelText("Demirbaş sayfaları")).getByRole("button", { name: "Sonraki" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/inventory/items", { params: { limit: 21, offset: 20 } }));
});

it("demirbaş ve zimmet formlarını izinli API yollarına kaydeder", async () => {
  open();
  await screen.findByRole("option", { name: "PC-1 · Tablet" });
  fireEvent.change(screen.getByLabelText("Demirbaş kodu"), { target: { value: "NEW-1" } });
  fireEvent.change(screen.getByLabelText("Demirbaş adı"), { target: { value: "Yeni tablet" } });
  fireEvent.click(screen.getByRole("button", { name: "Demirbaşı oluştur" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/inventory/items", { item_code: "NEW-1", item_name: "Yeni tablet", location_id: null, branch_id: "branch" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Demirbaşı oluştur" })).toBeEnabled());
  fireEvent.change(screen.getByLabelText("İşlem demirbaşı"), { target: { value: "item" } });
  fireEvent.change(screen.getByLabelText("Zimmet sorumlusu"), { target: { value: "teacher" } });
  fireEvent.click(screen.getByRole("button", { name: "Zimmeti kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/inventory/assignments", { item_id: "item", assigned_to: "teacher", return_date: null, notes: null }));
});

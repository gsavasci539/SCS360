import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("finans izni olmayan velinin panosu finans isteği yapmaz ve ödeme kartı göstermez", async () => {
  useAuthStore.setState({ user: { id: "parent", organization_id: "school", email: "parent@test.invalid", first_name: "Veli", last_name: "Test",
    is_super_admin: false, roles: [], branch_ids: [], permissions: ["parent.view_children"] } });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data:
    path === "/parent/my-children" ? [{ student_id: "child", first_name: "Deniz", last_name: "Test" }]
      : String(path).endsWith("/insights") ? { title: "Kayıt özeti", metrics: [{ label: "Not ortalaması", value: "Henüz değerlendirme kaydı yok" }] }
      : String(path).endsWith("/timeline") ? { events: [] } : {} } }));
  render(<MemoryRouter><ParentPortalPage view="dashboard" /></MemoryRouter>);
  await screen.findByText("Henüz değerlendirme kaydı yok", { exact: false });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/parent/child/child/insights", expect.anything()));
  expect(vi.mocked(api.get).mock.calls.some(([path]) => String(path).includes("financial-invoices"))).toBe(false);
  expect(screen.queryByText("Kalan Ödeme")).not.toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

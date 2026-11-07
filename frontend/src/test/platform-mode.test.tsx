import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { PlatformModeGuard } from "../routes/PlatformModeGuard";
import { AppShell } from "../components/AppShell";
import { ToastProvider } from "../components/Toast";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import type { AuthUser } from "../types/api";

const user: AuthUser = { id: "root", email: "root@example.com", first_name: "Platform", last_name: "Admin", is_super_admin: true, organization_id: "original", roles: [], branch_ids: [], permissions: [] };
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); });
function open(path = "/dashboard") {
  useAuthStore.setState({ user });
  render(<MemoryRouter initialEntries={[path]}><ToastProvider><Routes><Route element={<PlatformModeGuard />}><Route element={<AppShell />}><Route path="/dashboard" element={<p>Kurum verileri</p>} /><Route path="/platform" element={<p>SaaS yönetim alanı</p>} /></Route></Route></Routes></ToastProvider></MemoryRouter>);
}
it("ana yönetici kurum seçmeden yalnız SaaS alanını görür", () => {
  open(); expect(screen.getByText("SaaS yönetim alanı")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Öğrenci aramasına git" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Chatbot'u aç" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "SaaS Yönetimi" })); expect(screen.getByRole("link", { name: "Kurumlar ve Üyelikler" })).toHaveAttribute("href", "/platform");
});
it("seçilen kurum açılır ve tek düğmeyle platforma dönülür, ana hesap kurumu değişmez", () => {
  usePlatformWorkspace.getState().select({ id: "chosen", name: "Seçilen Okul", operatorId: user.id }); open();
  expect(screen.getByText("Kurum verileri")).toBeInTheDocument(); expect(screen.getByLabelText("Seçilen kurum çalışma alanı")).toHaveTextContent("Seçilen Okul");
  fireEvent.click(screen.getByRole("button", { name: "Platform yönetimine dön" })); expect(screen.getByText("SaaS yönetim alanı")).toBeInTheDocument();
  expect(useAuthStore.getState().user?.organization_id).toBe("original"); expect(usePlatformWorkspace.getState().workspace).toBeNull();
});

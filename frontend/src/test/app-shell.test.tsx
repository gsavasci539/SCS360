import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { AppShell } from "../components/AppShell";
import { ToastProvider } from "../components/Toast";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../components/Chatbot", () => ({ Chatbot: () => null }));
const base: AuthUser = { id: "nav", email: "nav@test.invalid", first_name: "Nav", last_name: "Test", organization_id: "org", is_super_admin: false, roles: [], permissions: [], branch_ids: [] };
function open(slugs: string[], permissions: string[], root = false) {
  useAuthStore.setState({ user: { ...base, is_super_admin: root, roles: slugs.map((slug) => ({ id: slug, name: slug, slug })), permissions } });
  render(<MemoryRouter><ToastProvider><AppShell /></ToastProvider></MemoryRouter>);
  return within(screen.getByRole("navigation", { name: "Ana menü" }));
}
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); });

it("veli ve öğretmen birlikte her iki yetkili çalışma alanını görür", () => {
  const nav = open(["parent", "teacher"], ["parent.view_children", "classes.read", "teacher.view_classes"]);
  fireEvent.click(nav.getByRole("button", { name: "Veli Portalı" }));
  expect(nav.getByRole("link", { name: "Çocuğum" })).toHaveAttribute("href", "/parent/children");
  fireEvent.click(nav.getByRole("button", { name: "Eğitim" }));
  expect(nav.getByRole("link", { name: "Sınıflar & Program" })).toBeVisible();
  fireEvent.click(nav.getByRole("button", { name: "Yönetim" }));
  expect(nav.getByRole("link", { name: "Öğretmen Paneli" })).toBeVisible();
});

it("veli özel sağlık okuma yetkisini de kullanır, yetkisiz modül görünmez", () => {
  const nav = open(["parent"], ["parent.view_children", "health.read"]);
  fireEvent.click(nav.getByRole("button", { name: "Operasyon" }));
  expect(nav.getByRole("link", { name: "Revir ve İlaç Kayıtları" })).toBeVisible();
  expect(nav.queryByRole("link", { name: "Öğrenci Teslim Masası" })).not.toBeInTheDocument();
});

it("kantin ve öğretmen rolleri birbirinin alanlarını gizlemez", () => {
  const nav = open(["canteen_staff", "teacher"], ["canteen.read", "canteen.write", "classes.read", "teacher.view_classes"]);
  fireEvent.click(nav.getByRole("button", { name: "Eğitim" }));
  expect(nav.getByRole("link", { name: "Sınıflar & Program" })).toBeVisible();
});

it("varsayılan kantin görünümü öğrenci seçimi yardımcı iznini genel öğrenci ekranına dönüştürmez", () => {
  const nav = open(["canteen_staff"], ["canteen.read", "canteen.write", "students.read", "surveys.respond"]);
  expect(nav.queryByRole("button", { name: "Eğitim" })).not.toBeInTheDocument();
  fireEvent.click(nav.getByRole("button", { name: "Operasyon" }));
  expect(nav.getByRole("link", { name: "Kantin Satış" })).toBeVisible();
  expect(nav.getAllByRole("link", { name: "Katılabileceğim Anketler" })).toHaveLength(1);
});

it("özel role verilen finans okuması kantin yazması nedeniyle gizlenmez", () => {
  const nav = open(["custom"], ["canteen.read", "canteen.write", "finance.read"]);
  fireEvent.click(nav.getByRole("button", { name: "Finans" }));
  expect(nav.getByRole("link", { name: "Borçlar" })).toBeVisible();
});

it("öğretmen paneli özel okuma yetkisini gerektirir; veli rolü olmayan yöneticiye veli alanı açılmaz", () => {
  const nav = open(["accountant"], ["dashboard.read"]);
  fireEvent.click(nav.getByRole("button", { name: "Yönetim" }));
  expect(nav.queryByRole("link", { name: "Öğretmen Paneli" })).not.toBeInTheDocument();
  expect(nav.queryByRole("button", { name: "Veli Portalı" })).not.toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import App from "../App";
import { ToastProvider } from "../components/Toast";
import { navigation } from "../config/navigation";
import { resources } from "../config/resources";
import { useAuthStore } from "../stores/auth";

describe("Okul360 uygulama iskeleti", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    useAuthStore.setState({ accessToken: null, refreshToken: null, user: null, hydrated: true });
  });

  it("korumalı sayfadan giriş ekranına yönlendirir", async () => {
    render(<MemoryRouter initialEntries={["/dashboard"]}><ToastProvider><App /></ToastProvider></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: /günün akışına/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Giriş yap" })).toBeInTheDocument();
  });

  it("ana menü ve CRUD kaynakları eksiksiz tanımlıdır", () => {
    expect(navigation.map((item) => item.path)).toEqual(expect.arrayContaining(["/dashboard", "/students", "/attendance", "/finance/debts", "/reports", "/settings"]));
    expect(Object.keys(resources)).toEqual(expect.arrayContaining(["organizations", "branches", "users", "students", "parents", "classes", "debts"]));
  });

  it("giriş alanlarına demo kimlik bilgisi yerleştirmez", async () => {
    render(<MemoryRouter initialEntries={["/login"]}><ToastProvider><App /></ToastProvider></MemoryRouter>);
    expect(await screen.findByLabelText("E-posta adresi")).toHaveValue("");
    expect(screen.getByLabelText("Şifre")).toHaveValue("");
    expect(screen.queryByText("Demo hesap")).not.toBeInTheDocument();
  });

  it("doğrudan URL ile yetkisiz modüle erişimi engeller", async () => {
    useAuthStore.setState({
      accessToken: "access",
      refreshToken: "refresh",
      hydrated: true,
      user: {
        id: "1", email: "user@example.com", first_name: "Test", last_name: "Kullanıcı",
        is_super_admin: false, organization_id: "org", roles: [], permissions: ["dashboard.read"], branch_ids: [],
      },
    });
    render(<MemoryRouter initialEntries={["/settings"]}><ToastProvider><App /></ToastProvider></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Bu alan için yetkiniz yok" })).toBeInTheDocument();
  });
});

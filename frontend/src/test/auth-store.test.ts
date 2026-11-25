import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "../stores/auth";
import type { AuthPayload, AuthUser } from "../types/api";

const user: AuthUser = {
  id: "user-1", email: "user@example.com", first_name: "Ayşe", last_name: "Yılmaz", is_super_admin: false,
  organization_id: "org-1", roles: [], permissions: ["student.read"], branch_ids: [],
};
const payload: AuthPayload = { access_token: "access-token", refresh_token: "refresh-token", token_type: "bearer", user };

describe("web ve bearer oturum saklama", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    useAuthStore.getState().clearSession();
  });

  afterEach(() => useAuthStore.getState().clearSession());

  it("eski local ve session storage tokenlarını temizler, oturumu cookie'den başlatır", () => {
    localStorage.setItem("okul360-session", JSON.stringify({ accessToken: "old", refreshToken: "old-refresh", user }));
    sessionStorage.setItem("scs360-session", JSON.stringify({ accessToken: "old", refreshToken: "old-refresh", user }));
    useAuthStore.getState().setCookieSession(user, "csrf");
    expect(useAuthStore.getState().authenticated).toBe(true);
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(localStorage.getItem("okul360-session")).toBeNull();
    expect(sessionStorage.getItem("scs360-session")).toBeNull();
  });

  it("web oturumu için tokenları yalnızca bellekte ve csrf değerini bellekte tutar", () => {
    useAuthStore.getState().setCookieSession(user, "csrf-secret");
    const state = useAuthStore.getState();
    expect(state.authenticated).toBe(true);
    expect(state.authMode).toBe("cookie");
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.csrfToken).toBe("csrf-secret");
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("bearer test sessions also never persist token values in browser storage", () => {
    useAuthStore.getState().setSession(payload, true);
    useAuthStore.getState().setTokens("next-access", "next-refresh");
    expect(useAuthStore.getState().accessToken).toBe("next-access");
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("logout clears the in-memory identity and browser token remnants", () => {
    useAuthStore.getState().setCookieSession(user, "csrf-secret");
    localStorage.setItem("scs360-session", "stale");
    sessionStorage.setItem("okul360-session", "stale");
    useAuthStore.getState().clearSession();
    expect(useAuthStore.getState().authenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().csrfToken).toBeNull();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("rol adı tek başına yazma yetkisi vermez", () => {
    expect(useAuthStore.getState().can("canteen.write")).toBe(false);
  });

  it("kurum sahibine kurum sayfalarını açar, SaaS yönetimini açmaz", () => {
    useAuthStore.getState().setCookieSession({ ...user, roles: [{ id: "owner-role", name: "Kurum Sahibi", slug: "owner" }], permissions: [] }, "csrf");
    expect(useAuthStore.getState().can("health.read_confidential")).toBe(true);
    expect(useAuthStore.getState().can("dashboard.read")).toBe(true);
    expect(useAuthStore.getState().can("super_admin")).toBe(false);
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../stores/auth";
import type { AuthPayload } from "../types/api";

const payload: AuthPayload = {
  access_token: "access-token",
  refresh_token: "refresh-token",
  token_type: "bearer",
  user: {
    id: "user-1",
    email: "user@example.com",
    first_name: "Ayşe",
    last_name: "Yılmaz",
    is_super_admin: false,
    organization_id: "org-1",
    roles: [],
    permissions: ["student.read"],
    branch_ids: [],
  },
};

describe("oturum saklama", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    useAuthStore.getState().clearSession();
  });

  afterEach(() => useAuthStore.getState().clearSession());

  it.each(["local", "session"] as const)("önceki %s oturumunu SCS360 anahtarına taşır", async (kind) => {
    const storage = kind === "local" ? localStorage : sessionStorage;
    storage.setItem("okul360-session", JSON.stringify({
      accessToken: payload.access_token, refreshToken: payload.refresh_token, user: payload.user,
    }));
    vi.resetModules();
    const { useAuthStore: restored } = await import("../stores/auth");
    expect(restored.getState().accessToken).toBe(payload.access_token);
    expect(storage.getItem("scs360-session")).toContain(payload.access_token);
    expect(storage.getItem("okul360-session")).toBeNull();
  });

  it("yeni oturumu eski kalıcı oturumla değiştirmez", async () => {
    localStorage.setItem("okul360-session", JSON.stringify({ accessToken: "old", refreshToken: "old", user: payload.user }));
    sessionStorage.setItem("scs360-session", JSON.stringify({ accessToken: "current", refreshToken: "current", user: payload.user }));
    vi.resetModules();
    const { useAuthStore: restored } = await import("../stores/auth");
    expect(restored.getState().accessToken).toBe("current");
    expect(localStorage.getItem("okul360-session")).toBeNull();
  });

  it("hatırlama kapalıyken yalnızca sekme oturumu kullanır", () => {
    useAuthStore.getState().setSession(payload, false);
    expect(sessionStorage.getItem("scs360-session")).toContain("access-token");
    expect(localStorage.getItem("scs360-session")).toBeNull();
  });

  it("hatırlama açıkken kalıcı oturum kullanır ve token yenilemeyi aynı yerde tutar", () => {
    useAuthStore.getState().setSession(payload, true);
    useAuthStore.getState().setTokens("new-access", "new-refresh");
    expect(localStorage.getItem("scs360-session")).toContain("new-access");
    expect(sessionStorage.getItem("scs360-session")).toBeNull();
  });

  it("çıkışta iki depodaki oturum izlerini de temizler", () => {
    useAuthStore.getState().setSession(payload, true);
    sessionStorage.setItem("scs360-session", "stale");
    useAuthStore.getState().clearSession();
    expect(localStorage.getItem("scs360-session")).toBeNull();
    expect(sessionStorage.getItem("scs360-session")).toBeNull();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("eski tekil guard'ları çoğul rol izinleriyle de kabul eder", () => {
    useAuthStore.getState().setSession({
      ...payload,
      user: { ...payload.user, permissions: ["students.read", "announcements.read"] },
    });

    expect(useAuthStore.getState().can("student.read")).toBe(true);
    expect(useAuthStore.getState().can("announcement.read")).toBe(true);
  });

  it("kurum sahibine kurum sayfalarını açar, SaaS yönetimini açmaz", () => {
    useAuthStore.getState().setSession({
      ...payload,
      user: { ...payload.user, roles: [{ id: "owner-role", name: "Kurum Sahibi", slug: "owner" }], permissions: [] },
    });
    expect(useAuthStore.getState().can("health.read_confidential")).toBe(true);
    expect(useAuthStore.getState().can("dashboard.read")).toBe(true);
    expect(useAuthStore.getState().can("super_admin")).toBe(false);
  });

  it("bozuk kalıcı kullanıcı yapısı uygulamayı çökertmek yerine girişe döner", async () => {
    for (const broken of [{ ...payload.user, roles: null }, { ...payload.user, permissions: "students.read" }, { ...payload.user, branch_ids: null }]) {
      localStorage.setItem("scs360-session", JSON.stringify({ accessToken: "old", refreshToken: "old-refresh", user: broken }));
      vi.resetModules();
      const { useAuthStore: restored } = await import("../stores/auth");
      expect(restored.getState().accessToken).toBeNull();
      expect(restored.getState().can("students.read")).toBe(false);
      expect(localStorage.getItem("scs360-session")).toBeNull();
    }
  });
});

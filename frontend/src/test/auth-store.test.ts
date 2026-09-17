import { afterEach, beforeEach, describe, expect, it } from "vitest";
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

  it("hatırlama kapalıyken yalnızca sekme oturumu kullanır", () => {
    useAuthStore.getState().setSession(payload, false);
    expect(sessionStorage.getItem("okul360-session")).toContain("access-token");
    expect(localStorage.getItem("okul360-session")).toBeNull();
  });

  it("hatırlama açıkken kalıcı oturum kullanır ve token yenilemeyi aynı yerde tutar", () => {
    useAuthStore.getState().setSession(payload, true);
    useAuthStore.getState().setTokens("new-access", "new-refresh");
    expect(localStorage.getItem("okul360-session")).toContain("new-access");
    expect(sessionStorage.getItem("okul360-session")).toBeNull();
  });

  it("çıkışta iki depodaki oturum izlerini de temizler", () => {
    useAuthStore.getState().setSession(payload, true);
    sessionStorage.setItem("okul360-session", "stale");
    useAuthStore.getState().clearSession();
    expect(localStorage.getItem("okul360-session")).toBeNull();
    expect(sessionStorage.getItem("okul360-session")).toBeNull();
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
});

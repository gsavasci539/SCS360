import { create } from "zustand";
import type { AuthPayload, AuthUser } from "../types/api";
import { usePlatformWorkspace, WORKSPACE_OPERATOR } from "./platformWorkspace";

const TOKEN_STORAGE_KEYS = ["scs360-session", "okul360-session"] as const;

// Roles created by the current seed use plural resource names, whereas a few
// established page guards still use singular names.  Accept both spellings so
// a valid backend permission is never rejected by the client-side guard.
const permissionAliases: Record<string, string> = {
  "user.read": "users.read",
  "user.write": "users.write",
  "users.read": "user.read",
  "users.write": "user.write",
  "student.read": "students.read",
  "student.write": "students.write",
  "students.read": "student.read",
  "students.write": "student.write",
  "parent.read": "parents.read",
  "parent.write": "parents.write",
  "parents.read": "parent.read",
  "parents.write": "parent.write",
  "class.read": "classes.read",
  "class.write": "classes.write",
  "classes.read": "class.read",
  "classes.write": "class.write",
  "announcement.read": "announcements.read",
  "announcement.write": "announcements.write",
  "announcements.read": "announcement.read",
  "announcements.write": "announcement.write",
  "parent_notices.read": "students.read",
  "parent_notices.write": "students.write",
  "communication.read": "notification.read",
  "communication.write": "notification.write",
  "notification.read": "communication.read",
  "notification.write": "communication.write",
  "parent.view_daily_report": "parent.view_children",
  "parent.view_finance": "parent.view_finances",
  "parent.view_finances": "parent.view_finance",
  "outbox.read": "notification.read",
  "survey.read": "surveys.read", "surveys.read": "survey.read",
  "survey.write": "surveys.write", "surveys.write": "survey.write",
  "consent.read": "consents.read", "consents.read": "consent.read",
  "consent.write": "consents.write", "consents.write": "consent.write",
};

export function hasPermission(user: AuthUser | null | undefined, permission?: string): boolean {
  if (!permission) return true;
  // Special handling for super_admin permission
  if (permission === "super_admin") {
    return Boolean(user?.is_super_admin);
  }
  // Owners can use every page inside their own institution. The API still
  // enforces tenant scope, and this never grants platform/SaaS administration.
  if (user?.organization_id && user.roles.some((role) => role.slug === "owner")) return true;
  const equivalentPermission = permissionAliases[permission];
  const operator = (user as (AuthUser & { [WORKSPACE_OPERATOR]?: boolean }) | null | undefined)?.[WORKSPACE_OPERATOR];
  return Boolean(
    user?.is_super_admin || operator ||
    user?.permissions.includes(permission) ||
    (equivalentPermission && user?.permissions.includes(equivalentPermission)),
  );
}

interface AuthState {
  sessionVersion: number;
  authMode: "bearer" | "cookie" | null;
  authenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  csrfToken: string | null;
  user: AuthUser | null;
  hydrated: boolean;
  setSession: (payload: AuthPayload, remember?: boolean) => void;
  setCookieSession: (user: AuthUser, csrfToken: string, newSession?: boolean) => void;
  setTokens: (accessToken: string, refreshToken: string, user?: AuthUser) => void;
  setUser: (user: AuthUser) => void;
  clearSession: () => void;
  setHydrated: (value: boolean) => void;
  can: (permission?: string) => boolean;
}

function clearBrowserTokenStorage() {
  if (typeof window === "undefined") return;
  try {
    for (const storage of [window.localStorage, window.sessionStorage]) {
      for (const key of TOKEN_STORAGE_KEYS) storage.removeItem(key);
    }
  } catch { /* Storage may be disabled by the browser; auth never depends on it. */ }
}

clearBrowserTokenStorage();

export const useAuthStore = create<AuthState>()((set, get) => ({
  sessionVersion: 0,
  authMode: null,
  authenticated: false,
  accessToken: null,
  refreshToken: null,
  csrfToken: null,
  user: null,
  hydrated: false,
  setSession: (payload, _remember = false) => {
    usePlatformWorkspace.getState().select(null);
    clearBrowserTokenStorage();
    set({ authMode: "bearer", authenticated: true, accessToken: payload.access_token, refreshToken: payload.refresh_token,
      csrfToken: null, user: payload.user, hydrated: true, sessionVersion: get().sessionVersion + 1 });
  },
  setCookieSession: (user, csrfToken, newSession = true) => {
    const workspace = usePlatformWorkspace.getState().workspace;
    if (workspace && (!user.is_super_admin || user.id !== workspace.operatorId)) usePlatformWorkspace.getState().select(null);
    clearBrowserTokenStorage();
    set({ authMode: "cookie", authenticated: true, accessToken: null, refreshToken: null, csrfToken, user, hydrated: true,
      sessionVersion: get().sessionVersion + (newSession ? 1 : 0) });
  },
  setTokens: (accessToken, refreshToken, updatedUser) => {
    const user = updatedUser ?? get().user;
    const workspace = usePlatformWorkspace.getState().workspace;
    if (workspace && (!user?.is_super_admin || user.id !== workspace.operatorId)) usePlatformWorkspace.getState().select(null);
    clearBrowserTokenStorage();
    set({ authMode: "bearer", authenticated: Boolean(accessToken), accessToken, refreshToken, user });
  },
  setUser: (user) => {
    const workspace = usePlatformWorkspace.getState().workspace;
    if (workspace && (!user.is_super_admin || user.id !== workspace.operatorId)) usePlatformWorkspace.getState().select(null);
    set({ user });
  },
  clearSession: () => {
    usePlatformWorkspace.getState().select(null);
    clearBrowserTokenStorage();
    set({ authMode: null, authenticated: false, accessToken: null, refreshToken: null, csrfToken: null, user: null,
      hydrated: true, sessionVersion: get().sessionVersion + 1 });
  },
  setHydrated: (hydrated) => set({ hydrated }),
  can: (permission) => hasPermission(get().user, permission),
}));

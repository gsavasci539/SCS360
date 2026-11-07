import { create } from "zustand";
import type { AuthPayload, AuthUser } from "../types/api";
import { isOrganizationAccess } from "../lib/subscription";
import { usePlatformWorkspace, WORKSPACE_OPERATOR } from "./platformWorkspace";

const STORAGE_KEY = "scs360-session";
// Read the previous release's key once so a brand change does not sign users out.
const LEGACY_STORAGE_KEY = "okul360-session";

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
  const equivalentPermission = permissionAliases[permission];
  const operator = (user as (AuthUser & { [WORKSPACE_OPERATOR]?: boolean }) | null | undefined)?.[WORKSPACE_OPERATOR];
  return Boolean(
    user?.is_super_admin || operator ||
    user?.permissions.includes(permission) ||
    (equivalentPermission && user?.permissions.includes(equivalentPermission)),
  );
}

interface PersistedSession {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
}

interface AuthState {
  sessionVersion: number;
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  hydrated: boolean;
  setSession: (payload: AuthPayload, remember?: boolean) => void;
  setTokens: (accessToken: string, refreshToken: string, user?: AuthUser) => void;
  setUser: (user: AuthUser) => void;
  clearSession: () => void;
  setHydrated: (value: boolean) => void;
  can: (permission?: string) => boolean;
}

function storageAvailable(storage: Storage): boolean {
  try {
    const key = `${STORAGE_KEY}-check`;
    storage.setItem(key, key);
    storage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

function validStoredUser(value: unknown): value is AuthUser {
  if (!value || typeof value !== "object") return false;
  const user = value as Record<string, unknown>;
  const strings = (items: unknown) => Array.isArray(items) && items.every((item) => typeof item === "string");
  return ["id", "email", "first_name", "last_name"].every((key) => typeof user[key] === "string") &&
    (user.organization_access === undefined || isOrganizationAccess(user.organization_access)) &&
    typeof user.is_super_admin === "boolean" && (user.organization_id === null || typeof user.organization_id === "string") &&
    strings(user.permissions) && strings(user.branch_ids) && Array.isArray(user.roles) && user.roles.every((role) =>
      role && typeof role === "object" && ["id", "name", "slug"].every((key) => typeof (role as Record<string, unknown>)[key] === "string"));
}

function parseSession(raw: string | null): PersistedSession | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    const container = parsed as Record<string, unknown>;
    const value = ("state" in container ? container.state : container) as Partial<PersistedSession> | undefined;
    if (
      typeof value?.accessToken !== "string" ||
      !value.accessToken ||
      typeof value.refreshToken !== "string" ||
      !value.refreshToken ||
      !validStoredUser(value.user)
    ) return null;
    return value as PersistedSession;
  } catch {
    return null;
  }
}

function getStorage(kind: "local" | "session"): Storage | null {
  if (typeof window === "undefined") return null;
  const storage = kind === "local" ? window.localStorage : window.sessionStorage;
  return storageAvailable(storage) ? storage : null;
}

function readInitialSession(): PersistedSession | null {
  const local = getStorage("local");
  const session = getStorage("session");
  if (!parseSession(local?.getItem(STORAGE_KEY) ?? null) && !parseSession(session?.getItem(STORAGE_KEY) ?? null)) {
    for (const storage of [local, session]) {
      const previous = parseSession(storage?.getItem(LEGACY_STORAGE_KEY) ?? null);
      if (storage && previous) {
        storage.setItem(STORAGE_KEY, JSON.stringify(previous));
        break;
      }
    }
  }
  local?.removeItem(LEGACY_STORAGE_KEY);
  session?.removeItem(LEGACY_STORAGE_KEY);
  const localValue = parseSession(local?.getItem(STORAGE_KEY) ?? null);
  if (localValue) {
    session?.removeItem(STORAGE_KEY);
    return localValue;
  }
  local?.removeItem(STORAGE_KEY);
  const sessionValue = parseSession(session?.getItem(STORAGE_KEY) ?? null);
  if (!sessionValue) session?.removeItem(STORAGE_KEY);
  return sessionValue;
}

function persistSession(value: PersistedSession, remember: boolean) {
  const local = getStorage("local");
  const session = getStorage("session");
  local?.removeItem(STORAGE_KEY);
  session?.removeItem(STORAGE_KEY);
  (remember ? local : session)?.setItem(STORAGE_KEY, JSON.stringify(value));
}

function clearPersistedSession() {
  getStorage("local")?.removeItem(STORAGE_KEY);
  getStorage("session")?.removeItem(STORAGE_KEY);
  getStorage("local")?.removeItem(LEGACY_STORAGE_KEY);
  getStorage("session")?.removeItem(LEGACY_STORAGE_KEY);
}

const initialSession = readInitialSession();

export const useAuthStore = create<AuthState>()((set, get) => ({
  sessionVersion: 0,
  accessToken: initialSession?.accessToken ?? null,
  refreshToken: initialSession?.refreshToken ?? null,
  user: initialSession?.user ?? null,
  hydrated: true,
  setSession: (payload, remember = false) => {
    usePlatformWorkspace.getState().select(null);
    const session = {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      user: payload.user,
    };
    persistSession(session, remember);
    set({ ...session, sessionVersion: get().sessionVersion + 1 });
  },
  setTokens: (accessToken, refreshToken, updatedUser) => {
    const user = updatedUser ?? get().user;
    const workspace = usePlatformWorkspace.getState().workspace;
    if (workspace && (!user?.is_super_admin || user.id !== workspace.operatorId)) usePlatformWorkspace.getState().select(null);
    const remember = Boolean(getStorage("local")?.getItem(STORAGE_KEY));
    if (user) persistSession({ accessToken, refreshToken, user }, remember);
    set({ accessToken, refreshToken, user });
  },
  setUser: (user) => {
    const workspace = usePlatformWorkspace.getState().workspace;
    if (workspace && (!user.is_super_admin || user.id !== workspace.operatorId)) usePlatformWorkspace.getState().select(null);
    const { accessToken, refreshToken } = get();
    const remember = Boolean(getStorage("local")?.getItem(STORAGE_KEY));
    if (accessToken && refreshToken) persistSession({ accessToken, refreshToken, user }, remember);
    set({ user });
  },
  clearSession: () => {
    usePlatformWorkspace.getState().select(null);
    clearPersistedSession();
    set({ accessToken: null, refreshToken: null, user: null, sessionVersion: get().sessionVersion + 1 });
  },
  setHydrated: (hydrated) => set({ hydrated }),
  can: (permission) => hasPermission(get().user, permission),
}));

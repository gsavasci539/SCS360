import { create } from "zustand";
import type { AuthPayload, AuthUser } from "../types/api";

const STORAGE_KEY = "okul360-session";

// Roles created by the current seed use plural resource names, whereas a few
// established page guards still use singular names.  Accept both spellings so
// a valid backend permission is never rejected by the client-side guard.
const permissionAliases: Record<string, string> = {
  "user.read": "users.read",
  "user.write": "users.write",
  "student.read": "students.read",
  "student.write": "students.write",
  "parent.read": "parents.read",
  "parent.write": "parents.write",
  "class.read": "classes.read",
  "class.write": "classes.write",
  "announcement.read": "announcements.read",
  "announcement.write": "announcements.write",
};

interface PersistedSession {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  hydrated: boolean;
  setSession: (payload: AuthPayload, remember?: boolean) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
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

function parseSession(raw: string | null): PersistedSession | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    const container = parsed as Record<string, unknown>;
    const value = ("state" in container ? container.state : container) as Partial<PersistedSession> | undefined;
    if (
      typeof value?.accessToken !== "string" ||
      typeof value.refreshToken !== "string" ||
      !value.user ||
      typeof value.user !== "object"
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
  const localValue = parseSession(local?.getItem(STORAGE_KEY) ?? null);
  if (localValue) {
    session?.removeItem(STORAGE_KEY);
    return localValue;
  }
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
}

const initialSession = readInitialSession();

export const useAuthStore = create<AuthState>()((set, get) => ({
  accessToken: initialSession?.accessToken ?? null,
  refreshToken: initialSession?.refreshToken ?? null,
  user: initialSession?.user ?? null,
  hydrated: true,
  setSession: (payload, remember = false) => {
    const session = {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      user: payload.user,
    };
    persistSession(session, remember);
    set(session);
  },
  setTokens: (accessToken, refreshToken) => {
    const user = get().user;
    const remember = Boolean(getStorage("local")?.getItem(STORAGE_KEY));
    if (user) persistSession({ accessToken, refreshToken, user }, remember);
    set({ accessToken, refreshToken });
  },
  setUser: (user) => {
    const { accessToken, refreshToken } = get();
    const remember = Boolean(getStorage("local")?.getItem(STORAGE_KEY));
    if (accessToken && refreshToken) persistSession({ accessToken, refreshToken, user }, remember);
    set({ user });
  },
  clearSession: () => {
    clearPersistedSession();
    set({ accessToken: null, refreshToken: null, user: null });
  },
  setHydrated: (hydrated) => set({ hydrated }),
  can: (permission) => {
    if (!permission) return true;
    const user = get().user;
    return Boolean(
      user?.is_super_admin ||
      user?.permissions.includes(permission) ||
      user?.permissions.includes(permissionAliases[permission]),
    );
  },
}));

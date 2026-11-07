import axios, { AxiosError, CanceledError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../stores/auth";
import type { ApiResponse, AuthUser } from "../types/api";
import { subscriptionAccessFromError } from "./subscription";
import { isWorkspaceRequest, usePlatformWorkspace } from "../stores/platformWorkspace";

// Same-origin API traffic avoids CORS and is proxied to the backend container
// on port 5006 by Vite (development) or Nginx (production).
const configuredUrl = String(import.meta.env.VITE_API_BASE_URL || "/api");
export const API_BASE_URL = configuredUrl.replace(/\/$/, "");

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 60000 });

type SessionRequest = InternalAxiosRequestConfig & { _retry?: boolean; _scsSession?: number; _scsWorkspace?: string | null; _scsOperator?: string };
function currentRequest(config: SessionRequest) {
  const account = useAuthStore.getState();
  return config._scsSession === account.sessionVersion && (!config._scsWorkspace || !isWorkspaceRequest(config.url || "") || Boolean(account.user?.is_super_admin && account.user.id === config._scsOperator));
}

api.interceptors.request.use((config) => {
  const scoped = config as SessionRequest;
  scoped._scsSession ??= useAuthStore.getState().sessionVersion;
  if (!currentRequest(scoped)) throw new CanceledError("Oturum veya kurum yetkisi değişti", config);
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const account = useAuthStore.getState().user, workspace = usePlatformWorkspace.getState().workspace;
  if (scoped._scsWorkspace === undefined) { scoped._scsWorkspace = account?.is_super_admin && workspace?.operatorId === account.id ? workspace.id : null; scoped._scsOperator = account?.id; }
  if (account?.is_super_admin && scoped._scsOperator === account.id && scoped._scsWorkspace && isWorkspaceRequest(config.url || "")) config.headers.set("X-SCS360-Organization-Id", scoped._scsWorkspace);
  else config.headers.delete("X-SCS360-Organization-Id");
  if (config.data instanceof FormData) config.headers.delete("Content-Type");
  return config;
});

let refreshing: { version: number; promise: Promise<string> } | null = null;

async function refreshAccessToken() {
  const { refreshToken, sessionVersion, user: operator } = useAuthStore.getState();
  if (!refreshToken) throw new Error("Oturum bulunamadı");
  const response = await axios.post<ApiResponse<{ access_token: string; refresh_token: string; user?: AuthUser }>>(
    `${API_BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { timeout: 20000 },
  );
  const { access_token, refresh_token, user } = response.data.data;
  const current = useAuthStore.getState();
  if (current.sessionVersion !== sessionVersion || current.refreshToken !== refreshToken || (user && user.id !== operator?.id)) throw new CanceledError("Oturum değişti");
  useAuthStore.getState().setTokens(access_token, refresh_token, user);
  return access_token;
}

api.interceptors.response.use(
  (response) => {
    if (!currentRequest(response.config as SessionRequest)) throw new CanceledError("Oturum veya kurum yetkisi değişti", response.config);
    return response;
  },
  async (error: AxiosError) => {
    const original = error.config as SessionRequest | undefined;
    if (original && !currentRequest(original)) return Promise.reject(new CanceledError("Oturum veya kurum yetkisi değişti", original));
    if (error.response?.status === 402) {
      const access = subscriptionAccessFromError(error.response.data);
      const account = useAuthStore.getState().user;
      if (access && account && !account.is_super_admin) useAuthStore.getState().setUser({ ...account, organization_access: access });
    }
    
    // Handle 401 from server
    if (error.response?.status === 401 && original && !original._retry && !original.url?.includes("/auth/")) {
      original._retry = true;
      try {
        if (!refreshing || refreshing.version !== original._scsSession) {
          const flight = { version: useAuthStore.getState().sessionVersion, promise: refreshAccessToken() };
          refreshing = flight;
          void flight.promise.finally(() => { if (refreshing === flight) refreshing = null; }).catch(() => {});
        }
        original.headers.Authorization = `Bearer ${await refreshing.promise}`;
        return api(original);
      } catch (reason) {
        if (axios.isCancel(reason) || !currentRequest(original)) return Promise.reject(reason);
        useAuthStore.getState().clearSession();
        if (!window.location.pathname.startsWith("/login")) {
          const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
          window.location.assign(`/login?next=${encodeURIComponent(next)}`);
        }
      }
    }
    return Promise.reject(error);
  },
);

export function apiMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 429) return "Çok fazla deneme yapıldı. Bir süre bekleyip tekrar deneyin.";
    const data = error.response?.data as { message?: string; detail?: string | Array<{ msg?: string }> } | undefined;
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).filter(Boolean).join(", ");
    return data?.message || (error.code === "ECONNABORTED" ? "Sunucu yanıt vermedi. Lütfen tekrar deneyin." : "Sunucuya ulaşılamadı.");
  }
  return error instanceof Error ? error.message : "Beklenmeyen bir hata oluştu.";
}

export const unwrap = <T,>(response: { data: ApiResponse<T> }) => response.data.data;

import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../stores/auth";
import type { ApiResponse } from "../types/api";

// Same-origin API traffic avoids CORS and is proxied to the backend container
// on port 5006 by Vite (development) or Nginx (production).
const configuredUrl = String(import.meta.env.VITE_API_BASE_URL || "/api");
export const API_BASE_URL = configuredUrl.replace(/\/$/, "");

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 20000 });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (config.data instanceof FormData) config.headers.delete("Content-Type");
  return config;
});

let refreshing: Promise<string> | null = null;

async function refreshAccessToken() {
  const refreshToken = useAuthStore.getState().refreshToken;
  if (!refreshToken) throw new Error("Oturum bulunamadı");
  const response = await axios.post<ApiResponse<{ access_token: string; refresh_token: string }>>(
    `${API_BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { timeout: 20000 },
  );
  useAuthStore.getState().setTokens(response.data.data.access_token, response.data.data.refresh_token);
  return response.data.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retry && !original.url?.includes("/auth/")) {
      original._retry = true;
      try {
        refreshing ??= refreshAccessToken().finally(() => { refreshing = null; });
        original.headers.Authorization = `Bearer ${await refreshing}`;
        return api(original);
      } catch {
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
    const data = error.response?.data as { message?: string; detail?: string | Array<{ msg?: string }> } | undefined;
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).filter(Boolean).join(", ");
    return data?.message || (error.code === "ECONNABORTED" ? "Sunucu yanıt vermedi. Lütfen tekrar deneyin." : "Sunucuya ulaşılamadı.");
  }
  return error instanceof Error ? error.message : "Beklenmeyen bir hata oluştu.";
}

export const unwrap = <T,>(response: { data: ApiResponse<T> }) => response.data.data;

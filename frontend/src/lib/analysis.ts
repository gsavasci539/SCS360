import type { AxiosRequestConfig } from "axios";
import { api } from "./api";
import { useAuthStore } from "../stores/auth";
import policy from "../config/analysisPermissions.json";

export function canAnalyze(path: string, can: (permission: string) => boolean = useAuthStore.getState().can) {
  const pathname = path.split("?")[0];
  const rule = Object.entries(policy).find(([template]) => new RegExp("^" + template.replace(/\{[^}]+\}/g, "[^/]+") + "$").test(pathname));
  return Boolean(rule && rule[1].every((group) => group.some((permission) => can(permission))));
}

// Optional panels have no data when their domains are unavailable. No HTTP
// request or synthetic HTTP status is produced for those panels.
export async function getAnalysis<T = any>(path: string, config?: AxiosRequestConfig): Promise<{ data: T }> {
  if (!canAnalyze(path)) return { data: { success: false, message: "", data: null } as T };
  return api.get<T>(path, config);
}

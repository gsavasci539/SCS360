import { isAxiosError } from "axios";

export function reportClientError(context: string, reason?: unknown) {
  if (!import.meta.env.DEV) return;
  // Axios errors carry request headers and complete response bodies. Never
  // write those objects (or their bearer tokens) into browser diagnostics.
  console.error(context, isAxiosError(reason) ? {
    message: reason.message,
    status: reason.response?.status,
    requestId: reason.response?.headers?.["x-request-id"],
  } : { message: reason instanceof Error ? reason.message : "İşlem tamamlanamadı" });
}

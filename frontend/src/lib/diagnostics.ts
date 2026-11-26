import { isAxiosError } from "axios";

function redactTckn(value: string) {
  return value.replace(/(^|\D)(?:\d[\s.-]?){10}\d(?=\D|$)/g, "$1[gizlendi]");
}

export function reportClientError(context: string, reason?: unknown) {
  if (!import.meta.env.DEV) return;
  // Axios errors carry request headers and complete response bodies. Never
  // write those objects (or their bearer tokens) into browser diagnostics.
  console.error(redactTckn(context), isAxiosError(reason) ? {
    message: redactTckn(reason.message),
    status: reason.response?.status,
    requestId: reason.response?.headers?.["x-request-id"],
  } : { message: redactTckn(reason instanceof Error ? reason.message : "İşlem tamamlanamadı") });
}

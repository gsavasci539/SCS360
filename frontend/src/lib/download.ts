import type { AxiosRequestConfig } from "axios";
import { api } from "./api";
import { fileSha256 } from "./fileIntegrity";

/** Download protected API files through the authenticated client. */
export async function downloadFile(path: string, filename: string, options: {
  params?: AxiosRequestConfig["params"];
  signal?: AbortSignal;
  expectedSha256?: string;
} = {}) {
  const { expectedSha256, ...request } = options;
  if (request.signal?.aborted) return;
  const response = await api.get<Blob>(path, { ...request, responseType: "blob" });
  if (request.signal?.aborted) return;
  if (expectedSha256 !== undefined && await fileSha256(response.data, request.signal) !== expectedSha256) {
    throw new Error("İndirilen dosya, kayıttaki SHA-256 özetiyle eşleşmiyor.");
  }
  if (request.signal?.aborted) return;
  const url = URL.createObjectURL(response.data);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename.replace(/[\\/]/g, "_");
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    // Allow the browser to consume the object URL before releasing it.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

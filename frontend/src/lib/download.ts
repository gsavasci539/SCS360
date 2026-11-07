import { api } from "./api";

/** Download protected API files through the authenticated client. */
export async function downloadFile(path: string, filename: string) {
  const response = await api.get(path, { responseType: "blob" });
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

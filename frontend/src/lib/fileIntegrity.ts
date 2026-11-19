/** Compute a file fingerprint with the browser's native Web Crypto implementation. */
export async function fileSha256(file: Blob, signal?: AbortSignal): Promise<string> {
  signal?.throwIfAborted();
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error("Dosya doğrulaması için HTTPS veya localhost bağlantısı gerekli.");
  const bytes = await file.arrayBuffer();
  signal?.throwIfAborted();
  const digest = new Uint8Array(await subtle.digest("SHA-256", bytes));
  signal?.throwIfAborted();
  return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

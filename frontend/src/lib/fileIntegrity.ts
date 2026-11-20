/** Compute a file fingerprint with the browser's native Web Crypto implementation. */
export async function fileSha256(file: Blob, signal?: AbortSignal): Promise<string> {
  signal?.throwIfAborted();
  if (!globalThis.crypto?.subtle) throw new Error("Dosya doğrulaması için HTTPS veya localhost bağlantısı gerekli.");
  return sha256Bytes(await file.arrayBuffer(), signal);
}

export async function sha256Bytes(bytes: BufferSource, signal?: AbortSignal): Promise<string> {
  signal?.throwIfAborted();
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error("İçerik doğrulaması için HTTPS veya localhost bağlantısı gerekli.");
  const digest = new Uint8Array(await subtle.digest("SHA-256", bytes));
  signal?.throwIfAborted();
  return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

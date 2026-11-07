export function hostedPaymentUrl(value: unknown): string | null {
  if (typeof value !== "string" || value.length > 4096) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password && parsed.hostname.endsWith(".iyzipay.com") && (!parsed.port || parsed.port === "443") ? parsed.href : null;
  } catch { return null; }
}

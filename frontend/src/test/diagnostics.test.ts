import { AxiosError, AxiosHeaders } from "axios";
import { afterEach, expect, it, vi } from "vitest";
import { reportClientError } from "../lib/diagnostics";

afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks(); });

it("geliştirme hatasında erişim anahtarını ve öğrenci verisini konsola yazmaz", () => {
  vi.stubEnv("DEV", true);
  const spy = vi.spyOn(console, "error").mockImplementation(() => {});
  const error = new AxiosError("Request failed with status code 403");
  error.config = { headers: new AxiosHeaders({ Authorization: "Bearer hidden-token" }) };
  error.response = { status: 403, statusText: "Forbidden", config: error.config,
    headers: { "x-request-id": "test-request-123" }, data: { child: "Gizli Öğrenci" } };
  reportClientError("Sınıf alınamadı", error);
  const output = JSON.stringify(spy.mock.calls);
  expect(output).toContain("403");
  expect(output).toContain("test-request-123");
  expect(output).not.toMatch(/hidden-token|Gizli Öğrenci|Authorization/);
});

it("üretim ortamında ham hata nesnesini konsola yazmaz", () => {
  vi.stubEnv("DEV", false);
  const spy = vi.spyOn(console, "error").mockImplementation(() => {});
  reportClientError("Hata", new Error("Private data"));
  expect(spy).not.toHaveBeenCalled();
});

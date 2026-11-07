import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MaterialsPage } from "../features/academic/MaterialsPage";
import { ToastProvider } from "../components/Toast";
import { api } from "../lib/api";
import { downloadFile } from "../lib/download";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
vi.mock("../lib/download", () => ({ downloadFile: vi.fn() }));
const material = { id: "material-1", title: "Türkçe çalışma", material_type: "PDF", file_name: "çalışma.pdf",
  teacher_id: "teacher", created_by: "teacher", class_name: "A sınıfı", created_at: "2026-11-03T10:00:00Z" };
const user: AuthUser = { id: "teacher", email: "teacher@test.invalid", first_name: "Teacher", last_name: "Test",
  is_super_admin: false, organization_id: "org", roles: [{ id: "teacher-role", name: "Öğretmen", slug: "teacher" }], permissions: ["material.read", "material.write", "classes.read"], branch_ids: [] };

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ user, hydrated: true, accessToken: "test", refreshToken: "test" });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/classes" ? { items: [{ id: "class-1", name: "A sınıfı" }] } : [material] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "new" } } });
  vi.mocked(downloadFile).mockResolvedValue(undefined);
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.restoreAllMocks(); });
const open = () => render(<ToastProvider><MaterialsPage /></ToastProvider>);

it("materyalin gerçek sınıfını ve tarihini gösterir, indirme düğmesi korumalı API'yi kullanır", async () => {
  open();
  fireEvent.click(await screen.findByRole("button", { name: "Türkçe çalışma indir" }));
  await waitFor(() => expect(downloadFile).toHaveBeenCalledWith("/materials/material-1/file", "çalışma.pdf"));
  expect(screen.getAllByText("A sınıfı").length).toBeGreaterThan(0);
  expect(screen.queryByText("undefined")).not.toBeInTheDocument();
});

it("başlık, sınıf ve dosyayı yükler ve listeyi yeniler", async () => {
  open();
  await screen.findByRole("option", { name: "A sınıfı" });
  fireEvent.change(screen.getByLabelText("Materyal başlığı"), { target: { value: "Yeni kaynak" } });
  fireEvent.change(screen.getByLabelText("Materyal görünürlüğü"), { target: { value: "CLASS_ONLY" } });
  fireEvent.change(screen.getByLabelText("Materyal sınıfı"), { target: { value: "class-1" } });
  const file = new File(["%PDF-1.4"], "kaynak.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByLabelText("Materyal dosyası"), { target: { files: [file] } });
  fireEvent.submit(screen.getByRole("button", { name: "Yükle" }).closest("form")!);
  await screen.findByText("Materyal yüklendi");
  const [, form, config] = vi.mocked(api.post).mock.calls[0];
  expect((form as FormData).get("file")).toBe(file);
  expect(config?.params).toEqual({ title: "Yeni kaynak", material_type: "PDF", visibility: "CLASS_ONLY", class_id: "class-1" });
  expect(api.get).toHaveBeenCalledTimes(3);
});

it("yalnız okuma yetkisinde yükleme ve silme sunmaz ve gereksiz sınıf isteği atmaz", async () => {
  useAuthStore.setState({ user: { ...user, permissions: ["material.read"] } });
  open();
  await screen.findByRole("button", { name: "Türkçe çalışma indir" });
  expect(screen.queryByRole("button", { name: "Yükle" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Türkçe çalışma kaldır" })).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledTimes(1);
});

it("başarısız indirmeyi görünür hata olarak sunar ve tekrar denemeye izin verir", async () => {
  vi.mocked(downloadFile).mockRejectedValueOnce(new Error("failed"));
  open();
  const button = await screen.findByRole("button", { name: "Türkçe çalışma indir" });
  fireEvent.click(button);
  expect(await screen.findByRole("alert")).toHaveTextContent("Materyal indirilemedi");
  expect(button).toBeEnabled();
});

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { ParentNoticesPage } from "../features/communications/ParentNoticesPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn(), delete: vi.fn() }, apiMessage: () => "İşlem başarısız" }));
const clinical = { id: "clinical", student_id: "child", student_name: "Klinik öğrenci", source: "medicine_request", status: "PENDING" };
beforeEach(() => {
  useAuthStore.setState({ user: { id: "reader", email: "reader@test.invalid", first_name: "Reader", last_name: "User", organization_id: "org", is_super_admin: false, roles: [], branch_ids: [], permissions: ["students.read", "students.write", "health.read"] } });
  vi.mocked(api.delete).mockResolvedValue({ data: { data: {} } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const open = (entry: string) => render(<MemoryRouter initialEntries={[entry]}><ToastProvider><Routes><Route path="/parent-notices" element={<ParentNoticesPage />} /><Route path="/parent-notices/:id" element={<ParentNoticesPage />} /></Routes></ToastProvider></MemoryRouter>);

it("öğrenci yazma yetkisi klinik talepte karar düğmesi açmaz", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: clinical } }); open("/parent-notices/clinical");
  await screen.findByText("Klinik öğrenci");
  expect(screen.queryByRole("button", { name: "Onayla" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reddet" })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Revir kaydını aç" })).toHaveAttribute("href", "/health?student=child");
});

it("klinik kaydı listeden silmez, normal veli talebinin kaldırma işlemini korur", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [clinical, { id: "notice", student_name: "Normal öğrenci", status: "PENDING" }], page: 1, page_size: 20, total: 2, total_pages: 1 } } }); open("/parent-notices");
  const clinicalCell = await screen.findByText("Klinik öğrenci");
  expect(within(clinicalCell.closest("tr")!).queryByRole("button", { name: "Kaldır" })).not.toBeInTheDocument();
  const normal = screen.getByText("Normal öğrenci").closest("tr")!;
  fireEvent.click(within(normal).getByRole("button", { name: "Kaldır" }));
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/parent-notices/notice"));
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ResourceFormPage } from "../features/resources/ResourcePages";
import { OrganizationsPage } from "../features/organizations/OrganizationsPage";
import { ToastProvider } from "../components/Toast";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
function session() {
  useAuthStore.setState({ user: { id: "owner", organization_id: "school", first_name: "Okul", last_name: "Sahibi", email: "owner@test.invalid",
    is_super_admin: false, roles: [], branch_ids: [], permissions: ["org.read", "org.write"] } });
}
it("okul sahibi kurum bilgilerini düzenler; yeni hesap, kurum import ve hesap kaldırma düğmeleri gösterilmez", async () => {
  session(); vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [{ id: "school", name: "Kurum" }], total: 1, page: 1, total_pages: 1 } } });
  render(<MemoryRouter><ToastProvider><OrganizationsPage /></ToastProvider></MemoryRouter>);
  expect(await screen.findByRole("link", { name: "Düzenle" })).toHaveAttribute("href", "/organizations/school/edit");
  expect(screen.queryByRole("link", { name: "Kurum ekle" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Excel İçe Aktar" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Kaldır" })).not.toBeInTheDocument();
});
it("eski yeni-kurum URL'si yetkisiz kayıt formu açmaz", () => {
  session(); render(<MemoryRouter><ToastProvider><ResourceFormPage resourceKey="organizations" /></ToastProvider></MemoryRouter>);
  expect(screen.getByText("Yeni kurum hesaplarını ana yönetici SaaS yönetiminden açar.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Kaydet" })).not.toBeInTheDocument();
});

it("kurum iletişim alanı temizlenince eski değeri geri kaydetmez ve null gönderir", async () => {
  session(); vi.mocked(api.get).mockResolvedValue({ data: { data: { id: "school", name: "Kurum", phone: "05320000000" } } });
  vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
  const view = render(<MemoryRouter initialEntries={["/organizations/school/edit"]}><ToastProvider><Routes>
    <Route path="/organizations/:id/edit" element={<ResourceFormPage resourceKey="organizations" />} /><Route path="/organizations" element={<p>Liste</p>} />
  </Routes></ToastProvider></MemoryRouter>);
  const phone = await screen.findByLabelText("Telefon"); expect(phone).toHaveValue("05320000000");
  fireEvent.change(phone, { target: { value: "" } }); fireEvent.submit(view.container.querySelector("form")!);
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/organizations/school", expect.objectContaining({ phone: null })));
});

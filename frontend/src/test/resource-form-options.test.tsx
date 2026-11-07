import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ResourceFormPage } from "../features/resources/ResourcePages";
import { ToastProvider } from "../components/Toast";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const record = { id: "student", organization_id: "school", branch_id: "branch", class_id: "class", first_name: "Test", last_name: "Student", enrollment_date: "2026-01-02", status: "ACTIVE" };
function setup(edit: boolean, writeOnly = false) {
  useAuthStore.getState().setSession({ access_token: "token", refresh_token: "refresh", token_type: "bearer", user: { id: "root", is_super_admin: !writeOnly, organization_id: writeOnly ? "school" : "original-org", first_name: "Root", last_name: "Test", email: "root@example.com", roles: [], permissions: writeOnly ? ["students.write"] : [], branch_ids: [] } });
  usePlatformWorkspace.getState().select({ id: "school", name: "Seçili okul", operatorId: "root" });
  let finish!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === (edit ? "/students/branch-options" : "/students/organization-options")) return await new Promise((resolve) => { finish = resolve; });
    if (String(path).endsWith("/form")) return { data: { data: record } };
    const items = String(path).includes("branch-options") ? [{ id: "branch", name: "Şube" }, { id: "branch2", name: "İkinci şube" }] : String(path).includes("class-options") ? [{ id: "class", name: "Sınıf" }] : [{ id: "school", name: "Seçili okul" }];
    return { data: { data: { items, total_pages: 1 } } };
  });
  vi.mocked(api.post).mockResolvedValue({ data: { data: record } });
  const view = render(<MemoryRouter initialEntries={[edit ? "/students/student/edit" : "/students/new"]}><ToastProvider><Routes><Route path="/students/new" element={<ResourceFormPage resourceKey="students" />} /><Route path="/students/:id/edit" element={<ResourceFormPage resourceKey="students" />} /><Route path="/students" element={<p>Liste</p>} /></Routes></ToastProvider></MemoryRouter>);
  return { ...view, ready: async () => { await waitFor(() => expect(finish).toBeDefined()); finish({ data: { data: { items: edit ? [{ id: "branch", name: "Şube" }, { id: "branch2", name: "İkinci şube" }] : [{ id: "school", name: "Seçili okul" }], total_pages: 1 } } }); } };
}

it("geç gelen seçenekler Root'un seçtiği kurumu kaybetmez ve kurum UUID'sini şube/sınıfa yazmaz", async () => {
  const view = setup(false); await view.ready();
  const organization = await screen.findByRole("combobox", { name: /^Kurum/ }); await waitFor(() => expect(organization).toBeEnabled()); expect(organization).toHaveValue("school");
  expect(screen.getByRole("combobox", { name: /^Şube/ })).toHaveValue(""); expect(screen.getByRole("combobox", { name: "Sınıf" })).toHaveValue("");
  await waitFor(() => expect(screen.getByRole("combobox", { name: /^Şube/ })).toBeEnabled());
  fireEvent.change(screen.getByRole("combobox", { name: /^Şube/ }), { target: { value: "branch" } });
  for (const [label, value] of [["Ad *", "Test"], ["Soyad *", "Student"], ["Kayıt tarihi *", "2026-01-02"]]) fireEvent.change(screen.getByLabelText(new RegExp("^" + label.replace(" *", "\\s*\\*?") + "$")), { target: { value } });
  fireEvent.submit(view.container.querySelector("form")!);
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/students", expect.objectContaining({ organization_id: "school", branch_id: "branch" })));
  expect(vi.mocked(api.post).mock.calls[0][1]).not.toHaveProperty("class_id");
});

it("kayıt seçeneklerden önce gelirse mevcut şube ve sınıfını korur", async () => {
  const view = setup(true); await view.ready();
  await screen.findByRole("combobox", { name: /^Şube/ });
  expect(screen.queryByRole("combobox", { name: /^Kurum/ })).not.toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: /^Şube/ })).toHaveValue("branch"); expect(screen.getByRole("combobox", { name: "Sınıf" })).toHaveValue("class");
});


it("şube değiştirilince eski şubenin sınıfını yeni şubeye göndermez", async () => {
  const view = setup(true); await view.ready();
  const branch = await screen.findByRole("combobox", { name: /^Şube/ }); await waitFor(() => expect(branch).toBeEnabled());
  expect(screen.getByRole("combobox", { name: "Sınıf" })).toHaveValue("class");
  fireEvent.change(branch, { target: { value: "branch2" } });
  await waitFor(() => expect(screen.getByRole("combobox", { name: "Sınıf" })).toHaveValue(""));
  vi.mocked(api.put).mockResolvedValue({ data: { data: record } });
  fireEvent.submit(view.container.querySelector("form")!);
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/students/student", expect.objectContaining({ branch_id: "branch2", class_id: null })));
});

it("yalnız öğrenci yazma yetkisiyle kayıt sonrası yasak genel listeye yönlenmez", async () => {
  const view = setup(false, true); await view.ready();
  const branch = await screen.findByRole("combobox", { name: /^Şube/ }); await waitFor(() => expect(branch).toBeEnabled());
  fireEvent.change(branch, { target: { value: "branch" } });
  for (const [label, value] of [["Ad", "Test"], ["Soyad", "Student"], ["Kayıt tarihi", "2026-01-02"]]) {
    fireEvent.change(screen.getByLabelText(new RegExp("^" + label + "\\s*\\*?$")), { target: { value } });
  }
  fireEvent.submit(view.container.querySelector("form")!);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Öğrenci düzenle" })).toBeInTheDocument());
  expect(screen.queryByText("Liste")).not.toBeInTheDocument();
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/students/student/form", expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

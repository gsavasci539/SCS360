import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { AnnouncementFormPage, AnnouncementsPage } from "../features/communications/CommunicationPages";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: () => "İşlem başarısız" }));
vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn().mockResolvedValue({ data: { data: null } }) }));
const editor: AuthUser = { id: "tester", first_name: "Test", last_name: "Editor", email: "editor@example.invalid", organization_id: "org",
  roles: [], permissions: ["announcement.read", "announcement.write"], branch_ids: [], is_super_admin: false };
const student = "00000000-0000-4000-8000-000000000010";
const draft = { id: "draft-record", title: "İzole duyuru", content: "Taslak için doğrulanan metin.", audience: "SINGLE_STUDENT",
  channels: ["EMAIL"], branch_id: "record-branch", student_id: student, class_id: null, status: "DRAFT" };

beforeEach(() => useAuthStore.setState({ user: editor }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.clearAllMocks(); });

it("tek öğrenci taslağını kanallar dizisiyle kaydeder ve sunucudan doğrular", async () => {
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: draft.id } } });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/announcements/targets" ?
    { items: [{ id: student, name: "İzole öğrenci" }], more: false } : draft } }));
  render(<MemoryRouter initialEntries={["/announcements/new"]}><ToastProvider><Routes>
    <Route path="/announcements/new" element={<AnnouncementFormPage />} />
    <Route path="/announcements" element={<p>Kayıt listesi</p>} />
  </Routes></ToastProvider></MemoryRouter>);
  fireEvent.change(screen.getByLabelText(/Duyuru başlığı/), { target: { value: draft.title } });
  fireEvent.change(screen.getByLabelText(/İçerik/), { target: { value: draft.content } });
  fireEvent.change(screen.getByLabelText(/Hedef kitle/), { target: { value: "SINGLE_STUDENT" } });
  await screen.findByRole("option", { name: "İzole öğrenci" });
  fireEvent.change(screen.getByRole("combobox", { name: /Öğrenci/ }), { target: { value: student } });
  fireEvent.click(screen.getByRole("button", { name: "Taslak olarak kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/announcements", { title: draft.title, content: draft.content,
    audience: "SINGLE_STUDENT", channels: ["EMAIL"], branch_id: null, class_id: null, student_id: student },
  expect.objectContaining({ signal: expect.any(AbortSignal) })));
  expect(api.get).toHaveBeenCalledWith(`/announcements/${draft.id}`, expect.objectContaining({ signal: expect.any(AbortSignal) }));
  expect(await screen.findByText("Kayıt listesi")).toBeInTheDocument();
  expect(screen.getByText("Duyuru taslağı kaydedildi")).toBeInTheDocument();
});

it("yalnız seçilen taslağı sıraya alır ve farklı kimlikteki kuyruk yanıtını reddeder", async () => {
  const other = { ...draft, id: "published", title: "Yayımlanan kayıt", status: "SENT" };
  vi.mocked(api.get).mockResolvedValue({ data: { data: [other, draft] } });
  vi.mocked(api.post).mockResolvedValueOnce({ data: { data: { announcement_id: other.id, jobs_created: 1, already_queued: false } } })
    .mockResolvedValueOnce({ data: { data: { announcement_id: draft.id, jobs_created: 1, already_queued: false } } });
  render(<MemoryRouter><ToastProvider><AnnouncementsPage /></ToastProvider></MemoryRouter>);
  const button = await screen.findByRole("button", { name: `${draft.title} duyurusunu kuyruğa al` });
  expect(screen.queryByRole("button", { name: `${other.title} duyurusunu kuyruğa al` })).not.toBeInTheDocument();
  fireEvent.click(button);
  expect(await screen.findByText("Kuyruk doğrulanamadı")).toBeInTheDocument();
  expect(screen.queryByText("Duyuru kuyruğa alındı")).not.toBeInTheDocument();
  fireEvent.click(button);
  await waitFor(() => expect(api.post).toHaveBeenLastCalledWith(`/announcements/${draft.id}/send`, undefined,
    expect.objectContaining({ signal: expect.any(AbortSignal) })));
  expect(await screen.findByText("Duyuru kuyruğa alındı")).toBeInTheDocument();
});

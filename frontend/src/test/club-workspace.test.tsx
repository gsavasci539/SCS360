import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { ClubWorkspace } from "../features/clubs/ClubWorkspace";
import { ClubsPage } from "../features/clubs/ClubsPage";
import { ParentCertificates } from "../features/parent/ParentCertificates";
import { api } from "../lib/api";
import { downloadFile } from "../lib/download";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
vi.mock("../lib/download", () => ({ downloadFile: vi.fn() }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.invalid", organization_id: "org",
  is_super_admin: false, roles: [], branch_ids: [], permissions: ["clubs.read", "clubs.write"] };
const award = { id: "cert-1", title: "Sanat belgesi", student_name: "Deniz Test", certificate_type: "PARTICIPATION", issue_date: "2026-11-03" };
const clubs = [{ id: "club-1", branch_id: "branch-1", club_name: "Sanat" }];
const changed = vi.fn(async () => {});

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ user: manager, accessToken: "test", hydrated: true });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/clubs/options" ? {
    branches: [{ id: "branch-1", name: "Merkez" }], students: [{ id: "student-1", name: "Deniz Test" }], teachers: [], student_count: 1,
  } : path === "/clubs" ? clubs : String(path).includes("certificates") ? [award] : [] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "new-record" } } });
  vi.mocked(downloadFile).mockResolvedValue(undefined);
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.restoreAllMocks(); });
const open = () => render(<ToastProvider><ClubWorkspace onChange={changed} /></ToastProvider>);

it("kulüp yazma yetkisini bağımsız seçenek API'siyle kullanır ve gerçek üyelik oluşturur", async () => {
  open();
  await screen.findByRole("option", { name: "Deniz Test" }, { timeout: 5000 });
  await screen.findByRole("option", { name: "Sanat" });
  fireEvent.change(screen.getByLabelText("İşlem kulübü"), { target: { value: "club-1" } });
  fireEvent.change(screen.getByLabelText("İşlem öğrencisi"), { target: { value: "student-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Üyeliği kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/clubs/memberships", { club_id: "club-1", student_id: "student-1" }));
  await waitFor(() => expect(changed).toHaveBeenCalled());
  expect(vi.mocked(api.get).mock.calls.every(([path]) => path === "/clubs" || String(path).startsWith("/clubs/"))).toBe(true);
});

it("belgeyi gerçek API'den indirir, salt okuma rolüne yazma formu göstermez", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["clubs.read"] } });
  open();
  fireEvent.click(await screen.findByRole("button", { name: "Sanat belgesi indir" }));
  await waitFor(() => expect(downloadFile).toHaveBeenCalledWith("/clubs/certificates/cert-1/pdf", "Sanat belgesi.pdf"));
  expect(screen.queryByRole("form", { name: "Kulüp oluştur" })).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/clubs/options")).toBe(false);
});

it("yirmiden fazla üyeyi sayfalar ve sonraki kayıtları ister", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["clubs.read"] } });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/clubs/memberships" ? Array.from({ length: 21 }, (_, index) => ({
    id: "member-" + index, student_name: "Öğrenci " + index, club_name: "Sanat", joined_date: "2026-11-03",
  })) : [] } }));
  open();
  const pager = await screen.findByLabelText("Üyelik sayfaları");
  fireEvent.click(within(pager).getByRole("button", { name: "Sonraki" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/clubs/memberships", { params: { status: "ACTIVE", limit: 21, offset: 20 } }));
});

it("veli belgesini çocuğa bağlı adresten indirir", async () => {
  render(<ParentCertificates studentId="child-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "Belgeyi indir" }));
  await waitFor(() => expect(downloadFile).toHaveBeenCalledWith("/parent/child/child-1/certificates/cert-1/pdf", "Sanat belgesi.pdf"));
});

it("kulüp ve etkinlik tablosunu sayfalar, özette gerçek toplamı gösterir", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["clubs.read"] } });
  vi.mocked(api.get).mockImplementation(async (path, config) => ({ data: { data: path === "/ai/clubs-analysis" ? {
    total_clubs: 145, total_members: 90, upcoming_events: 40, recommendations: [],
  } : path === "/clubs" ? Array.from({ length: 21 }, (_, index) => ({ id: "c" + index, club_name: "Kulüp " + (Number((config?.params as { offset?: number } | undefined)?.offset || 0) + index),
    advisor_name: "Işıl Öğretmen", max_members: 30, current_members: 2, is_active: true })) : [] } }));
  render(<ToastProvider><ClubsPage /></ToastProvider>);
  await screen.findByText("145");
  const pager = screen.getByLabelText("Kulüp sayfaları");
  expect(screen.queryByRole("cell", { name: "Kulüp 20" })).not.toBeInTheDocument();
  fireEvent.click(within(pager).getByRole("button", { name: "Sonraki" }));
  await screen.findByRole("cell", { name: "Kulüp 20" });
  expect(api.get).toHaveBeenCalledWith("/clubs", { params: { limit: 21, offset: 20 } });
  expect(screen.queryByText("undefined")).not.toBeInTheDocument();
});

it("veli belge listesinin sonraki sayfasını çocuğun kapsamıyla getirir", async () => {
  vi.mocked(api.get).mockImplementation(async () => ({ data: { data: Array.from({ length: 21 }, (_, index) => ({ ...award, id: "a" + index })) } }));
  render(<ParentCertificates studentId="child-1" />);
  const pager = await screen.findByLabelText("Çocuğun belge sayfaları");
  expect(screen.getAllByRole("button", { name: "Belgeyi indir" })).toHaveLength(20);
  fireEvent.click(within(pager).getByRole("button", { name: "Sonraki" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/parent/child/child-1/certificates", expect.objectContaining({ params: { limit: 21, offset: 20 } })));
});

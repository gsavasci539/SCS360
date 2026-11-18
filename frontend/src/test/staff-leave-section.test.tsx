import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { StaffLeaveSection } from "../features/staff/StaffLeaveSection";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  apiMessage: (error: Error) => error.message,
}));

const route = "/staff/leave-requests";
const previousAuth = useAuthStore.getState();
const previousWorkspace = usePlatformWorkspace.getState();
const user: AuthUser = {
  id: "staff-member", email: "staff@example.invalid", first_name: "Test", last_name: "Staff",
  organization_id: "school", is_super_admin: false, roles: [], permissions: [], branch_ids: [],
};
const pending = {
  id: "existing-leave", staff_id: "staff-member", staff_name: "Test Staff", leave_type: "Yıllık İzin",
  start_date: "2027-01-01", end_date: "2027-01-03", reason: "Planlanmış izin", days_count: 3,
  status: "PENDING", admin_comment: null,
};
const response = (data: unknown) => ({ data: { success: true, data } });

afterEach(() => {
  cleanup();
  useAuthStore.setState(previousAuth);
  usePlatformWorkspace.setState(previousWorkspace);
  vi.resetAllMocks();
});

it("lets a reader submit their own request and verify a lost response without another POST", async () => {
  useAuthStore.setState({ user, can: (permission) => permission === "user.read" });
  let saved: object | null = null;
  vi.mocked(api.get).mockImplementation(async () => response(saved ? [saved] : []));
  vi.mocked(api.post).mockImplementation(async (_url, body) => {
    const submitted = body as Record<string, unknown>;
    saved = { ...submitted, id: submitted.request_id, status: "PENDING", staff_name: "Kayıtlı personel" };
    throw new Error("Lost response");
  });
  render(<StaffLeaveSection />);
  await screen.findByText("Kayıtlı izin talebi yok.");
  fireEvent.click(screen.getByRole("button", { name: "İzin talebi oluştur" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByRole("button", { name: "Talebi gönder" })).toBeDisabled();
  fireEvent.change(dialog.getByLabelText(/Başlangıç/), { target: { value: "2027-01-01" } });
  fireEvent.change(dialog.getByLabelText(/Bitiş/), { target: { value: "2027-01-03" } });
  fireEvent.change(dialog.getByLabelText(/İzin gerekçesi/), { target: { value: "Planlanmış izin" } });
  expect(dialog.getByText("3 gün")).toBeInTheDocument();
  fireEvent.click(dialog.getByRole("button", { name: "Talebi gönder" }));
  fireEvent.click(await dialog.findByRole("button", { name: "Sonucu kontrol et" }));
  expect(await screen.findByText("Kayıtlı personel")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Onayla" })).not.toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith(route, expect.objectContaining({
    staff_id: user.id, start_date: "2027-01-01", end_date: "2027-01-03", days_count: 3,
    reason: "Planlanmış izin", request_id: expect.any(String),
  }), expect.any(Object));
  expect(api.post).toHaveBeenCalledTimes(1);
});

it("waits for explicit review confirmation and preserves the note when the list is stale", async () => {
  useAuthStore.setState({ user, can: () => true });
  const reviewNote = "Çizelge dolu.\nYeni tarih gerekiyor.";
  const decided = { ...pending, status: "REJECTED", admin_comment: reviewNote };
  vi.mocked(api.get)
    .mockResolvedValueOnce(response([pending]))
    .mockResolvedValueOnce(response([pending]))
    .mockResolvedValueOnce(response([decided]));
  vi.mocked(api.put).mockResolvedValue(response(decided));
  render(<StaffLeaveSection />);
  fireEvent.click(await screen.findByRole("button", { name: "Reddet" }));
  expect(api.put).not.toHaveBeenCalled();
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByText("Planlanmış izin")).toBeInTheDocument();
  fireEvent.change(dialog.getByLabelText(/Değerlendirme notu/), { target: { value: reviewNote } });
  fireEvent.click(dialog.getByRole("button", { name: "Değerlendirmeyi kaydet" }));
  const retry = await dialog.findByRole("button", { name: "Sonucu kontrol et" });
  expect(dialog.getByLabelText(/Değerlendirme notu/)).toHaveValue(reviewNote);
  fireEvent.click(retry);
  expect(await screen.findByText("Reddedildi")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(api.put).toHaveBeenCalledWith(route + "/existing-leave/review",
    { status: "REJECTED", admin_comment: reviewNote }, expect.any(Object));
  expect(api.put).toHaveBeenCalledTimes(1);
});

it("allows review in a selected root workspace but excludes self service for the platform account", async () => {
  useAuthStore.setState({ user: { ...user, is_super_admin: true, organization_id: null }, can: () => true });
  usePlatformWorkspace.setState({ workspace: { id: "school", name: "School", operatorId: user.id } });
  vi.mocked(api.get).mockResolvedValue(response([pending]));
  render(<StaffLeaveSection />);
  expect(await screen.findByRole("button", { name: "Onayla" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "İzin talebi oluştur" })).not.toBeInTheDocument();
});

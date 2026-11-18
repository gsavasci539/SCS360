import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DutyRosterSection } from "../features/staff/DutyRosterSection";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  apiMessage: (error: Error) => error.message,
}));

const route = "/staff/duty-rosters";
const previousAuth = useAuthStore.getState();

afterEach(() => {
  cleanup();
  useAuthStore.setState(previousAuth);
  vi.resetAllMocks();
});

it("uses scoped options and reads back a lost confirmation without posting again", async () => {
  useAuthStore.setState({ can: () => true });
  let saved: object | null = null;
  vi.mocked(api.get).mockImplementation(async (url, options) => ({
    data: { data: url === route
      ? (saved ? [saved] : [])
      : { page: 1, total_pages: 1, items: (options?.params as { branch_id?: string } | undefined)?.branch_id
        ? [{ id: "teacher", name: "Kayıtlı öğretmen" }]
        : [{ id: "branch", name: "Kayıtlı şube" }] } },
  }));
  vi.mocked(api.post).mockImplementation(async (_url, body) => {
    const attempt = body as Record<string, string>;
    saved = { ...attempt, id: attempt.request_id, status: "ACTIVE", teacher_name: "Sunucudaki öğretmen" };
    throw new Error("Lost response");
  });
  render(<DutyRosterSection />);
  await screen.findByText("Kayıtlı nöbet yok.");
  fireEvent.click(screen.getByRole("button", { name: "Nöbet oluştur" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByRole("button", { name: "Kaydet" })).toBeDisabled();
  await dialog.findByRole("option", { name: "Kayıtlı şube" });
  fireEvent.change(dialog.getByLabelText(/Şube/), { target: { value: "branch" } });
  await dialog.findByRole("option", { name: "Kayıtlı öğretmen" });
  fireEvent.change(dialog.getByLabelText(/Öğretmen/), { target: { value: "teacher" } });
  fireEvent.change(dialog.getByLabelText(/Gün/), { target: { value: "MONDAY" } });
  fireEvent.change(dialog.getByLabelText(/Nöbet yeri/), { target: { value: "GARDEN" } });
  fireEvent.change(dialog.getByLabelText(/Başlangıç/), { target: { value: "08:00" } });
  fireEvent.change(dialog.getByLabelText(/Bitiş/), { target: { value: "15:30" } });
  fireEvent.click(dialog.getByRole("button", { name: "Kaydet" }));
  fireEvent.click(await dialog.findByRole("button", { name: "Sonucu kontrol et" }));
  expect(await screen.findByText("Sunucudaki öğretmen")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith(route + "/options", expect.objectContaining({
    params: { branch_id: "branch", page: 1, page_size: 100 },
  }));
  expect(api.post).toHaveBeenCalledTimes(1);
});

it("shows the roster without create actions for a reader", async () => {
  useAuthStore.setState({ can: () => false });
  vi.mocked(api.get).mockResolvedValue({ data: { data: [] } });
  render(<DutyRosterSection />);
  expect(await screen.findByText("Kayıtlı nöbet yok.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Nöbet oluştur" })).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledTimes(1);
});

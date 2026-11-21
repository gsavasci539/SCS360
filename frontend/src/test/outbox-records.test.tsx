import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { OutboxDetailPage } from "../features/communications/OutboxDetailPage";
import { OutboxPage } from "../features/communications/OutboxPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); useAuthStore.getState().clearSession(); });

it("giden kutusu kanal ve durum filtrelerini sayfa isteğine ekler", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [], page: 1, page_size: 20, total_pages: 0, total: 0 } } });
  render(<MemoryRouter><ToastProvider><OutboxPage /></ToastProvider></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Kanal"), { target: { value: "EMAIL" } });
  fireEvent.change(screen.getByLabelText("Durum"), { target: { value: "FAILED" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/outbox",
    expect.objectContaining({ params: expect.objectContaining({ channel: "EMAIL", status: "FAILED", page: 1 }) })));
});

it("kuyruk isteğinden sonra aynı işin sunucudaki durumunu gösterir", async () => {
  useAuthStore.setState({ user: { id: "writer", first_name: "Test", last_name: "User", email: "writer@test.invalid",
    is_super_admin: false, organization_id: "org", roles: [], branch_ids: [], permissions: ["notification.write"] } });
  const message = { id: "msg", job_id: "job", branch_id: "branch", channel: "EMAIL", status: "FAILED",
    sent_at: null, subject: "İzole kayıt", recipient: "isolated@test.invalid" };
  vi.mocked(api.get).mockResolvedValueOnce({ data: { data: message } })
    .mockResolvedValueOnce({ data: { data: { ...message, status: "PENDING" } } });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { ...message, status: "PENDING" } } });
  render(<MemoryRouter initialEntries={["/outbox/msg"]}><ToastProvider><Routes>
    <Route path="/outbox/:id" element={<OutboxDetailPage />} />
  </Routes></ToastProvider></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Yeniden kuyruğa al" }));
  expect(await screen.findByText("Kuyruk isteği doğrulandı")).toBeInTheDocument();
  expect(api.get).toHaveBeenLastCalledWith("/outbox/msg", { params: { branch_id: "branch" } });
  expect(screen.queryByText("Sağlayıcı kabul etti")).not.toBeInTheDocument();
});

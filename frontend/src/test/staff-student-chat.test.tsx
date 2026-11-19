import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { StaffStudentChat } from "../features/parent/StaffStudentChat";
import { api } from "../lib/api";
import { downloadFile } from "../lib/download";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  unwrap: (response: { data: { data: unknown } }) => response.data.data,
  apiMessage: (error: Error) => error.message,
}));
vi.mock("../lib/download", () => ({ downloadFile: vi.fn() }));

const user: AuthUser = {
  id: "staff", first_name: "Test", last_name: "Personel", email: "staff@test.invalid",
  organization_id: "school", roles: [], branch_ids: [], permissions: ["messaging.read", "students.read", "messaging.send"],
  is_super_admin: false,
};
const contacts = { student_id: "student", student_name: "Örnek Öğrenci", parent_id: "guardian",
  parent_name: "Birinci Veli", branch_id: "north", class_name: "Sınıf A" };
const branches = [{ id: "north", name: "Kuzey Şube" }, { id: "south", name: "Güney Şube" }];
const response = (data: unknown) => ({ data: { data } });
const page = (items: unknown[], number = 1, total = 1) => response({ items, page: number, total_pages: total });

afterEach(() => {
  cleanup();
  useAuthStore.getState().clearSession();
  vi.resetAllMocks();
});

it("pages through real contacts and keeps student, guardian and branch on send, receipt and attachment", async () => {
  useAuthStore.getState().setUser(user);
  const endpoint = "/admin/chat/student";
  let receiptId = "";
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path.endsWith("chat-branches")) return response(branches);
    const params = config?.params as { page?: number } | undefined;
    if (path.endsWith("chat-contacts")) return params?.page === 1
      ? page([contacts], 1, 2) : page([{ ...contacts, parent_id: "guardian-two", parent_name: "İkinci Veli" }], 2, 2);
    if (path.includes("/sent/")) return response({
      id: receiptId, content: "", is_current_user: true, is_read: false, sent_at: "2026-11-19T09:00:00Z",
      attachment_name: "ders.pdf", attachment_sha256: "a".repeat(64),
    });
    return response([]);
  });
  vi.mocked(api.post).mockImplementation(async (_, form) => {
    receiptId = String((form as FormData).get("request_id"));
    return response(null);
  });
  render(<StaffStudentChat area="/admin" />);
  fireEvent.click(await screen.findByRole("button", { name: "Sonraki" }));
  fireEvent.click(await screen.findByRole("button", { name: /İkinci Veli/ }));
  await screen.findByText("Henüz mesaj yok.");
  const config = expect.objectContaining({ params: { parent_id: "guardian-two", branch_id: "north" } });
  expect(api.get).toHaveBeenCalledWith(endpoint, config);
  const file = new File(["%PDF-1.4"], "ders.pdf");
  fireEvent.change(screen.getByLabelText("Sohbet dosyası"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Gönder" }));
  fireEvent.click(await screen.findByRole("button", { name: "ders.pdf" }));
  expect(api.post).toHaveBeenCalledWith(`${endpoint}/send-file`, expect.any(FormData), config);
  expect(api.get).toHaveBeenCalledWith(`${endpoint}/sent/${receiptId}`, config);
  expect(downloadFile).toHaveBeenCalledWith(`${endpoint}/attachments/${receiptId}`, "ders.pdf", config);
  fireEvent.click(screen.getByRole("button", { name: "Sohbeti kapat" }));
  expect(await screen.findByRole("button", { name: /İkinci Veli/ })).toBeVisible();
});

it("aborts the old branch list and opens a read-only teacher conversation in the selected branch", async () => {
  useAuthStore.getState().setUser({ ...user, permissions: ["messaging.read", "students.read"] });
  let firstSignal: AbortSignal | undefined;
  let finishFirst!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/teacher/chat-branches") return response(branches);
    const params = config?.params as { branch_id?: string } | undefined;
    if (path === "/teacher/chat-contacts" && !params?.branch_id) {
      firstSignal = config?.signal as AbortSignal;
      return new Promise((resolve) => { finishFirst = resolve; });
    }
    if (path === "/teacher/chat-contacts") return page([{ ...contacts, branch_id: "south" }]);
    return response([]);
  });
  render(<StaffStudentChat area="/teacher" />);
  await screen.findByRole("option", { name: "Güney Şube" });
  fireEvent.change(screen.getByLabelText("Şube"), { target: { value: "south" } });
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "  Sınıf A  " } });
  fireEvent.click(screen.getByRole("button", { name: "Ara" }));
  expect(firstSignal?.aborted).toBe(true);
  await act(async () => finishFirst(page([{ ...contacts, student_name: "Eski kapsam" }])));
  expect(screen.queryByText("Eski kapsam")).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: /Birinci Veli/ }));
  expect(await screen.findByText("Bu hesapla gönderim yapılamaz.")).toBeVisible();
  expect(screen.queryByLabelText("Sohbet mesajı")).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/teacher/chat-contacts", expect.objectContaining({
    params: { branch_id: "south", search: "Sınıf A", page: 1 },
  }));
  expect(api.get).toHaveBeenCalledWith("/teacher/chat/student", expect.objectContaining({
    params: { branch_id: "south", parent_id: "guardian" },
  }));
});

it("clears the selected conversation and aborts the request when Root changes institution", async () => {
  useAuthStore.getState().setUser({ ...user, is_super_admin: true, organization_id: null });
  let openSignal: AbortSignal | undefined;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path.endsWith("chat-branches")) return response(branches);
    if (path.endsWith("chat-contacts")) return page([contacts]);
    openSignal = config?.signal as AbortSignal;
    return new Promise(() => {});
  });
  render(<StaffStudentChat area="/admin" />);
  expect(screen.getByText("Sohbetleri açmak için bir kurum seçin.")).toBeVisible();
  expect(api.get).not.toHaveBeenCalled();
  act(() => usePlatformWorkspace.getState().select({ id: "school-1", name: "Kurum 1", operatorId: user.id }));
  fireEvent.click(await screen.findByRole("button", { name: /Birinci Veli/ }));
  await waitFor(() => expect(openSignal).toBeDefined());
  act(() => usePlatformWorkspace.getState().select({ id: "school-2", name: "Kurum 2", operatorId: user.id }));
  expect(openSignal?.aborted).toBe(true);
  expect(screen.queryByRole("button", { name: "Sohbeti kapat" })).not.toBeInTheDocument();
});

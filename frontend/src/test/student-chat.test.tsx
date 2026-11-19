import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ChatInterface } from "../features/parent/ChatInterface";
import { api } from "../lib/api";
import { downloadFile } from "../lib/download";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  unwrap: (response: { data: { data: unknown } }) => response.data.data,
  apiMessage: () => "Sunucuya ulaşılamadı.",
}));
vi.mock("../lib/download", () => ({ downloadFile: vi.fn() }));

const response = (data: unknown) => ({ data: { data } });
const statement = (id: string) => ({
  id, is_current_user: true, is_read: false, sent_at: "2026-11-19T09:00:00Z",
  attachment_name: "rapor.pdf", attachment_sha256: "a".repeat(64), content: "Belge",
});

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("recovers a lost attachment response without sending the same file twice", async () => {
  const endpoint = "/parent/child/student/chat/teacher";
  let requestId = "";
  vi.mocked(api.get).mockImplementation(async (path) =>
    response(path === endpoint ? [] : statement(requestId)));
  vi.mocked(api.post).mockImplementation(async (_path, body: FormData) => {
    requestId = String(body.get("request_id"));
    throw new Error("Lost response");
  });
  render(<ChatInterface studentId="student" teacherId="teacher" teacherName="Öğretmen" onBack={vi.fn()} />);
  await screen.findByText("Henüz mesaj yok.");
  const file = new File(["%PDF-1.4"], "rapor.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByLabelText("Sohbet dosyası"), { target: { files: [file] } });
  fireEvent.change(screen.getByLabelText("Sohbet mesajı"), { target: { value: "Belge" } });
  fireEvent.click(screen.getByRole("button", { name: "Gönder" }));
  await screen.findByRole("alert");
  const [[path, body]] = vi.mocked(api.post).mock.calls;
  expect(path).toBe(`${endpoint}/send-file`);
  expect((body as FormData).get("file")).toBe(file);
  expect((body as FormData).get("message")).toBe("Belge");
  fireEvent.click(screen.getByRole("button", { name: "Gönderimi kontrol et" }));
  fireEvent.click(await screen.findByRole("button", { name: "rapor.pdf" }));
  expect(api.get).toHaveBeenCalledWith(`${endpoint}/sent/${requestId}`, expect.anything());
  expect(downloadFile).toHaveBeenCalledWith(`${endpoint}/attachments/${requestId}`, "rapor.pdf", expect.anything());
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("Sohbet mesajı")).toHaveValue("");
});

it("keeps the selected parent on admin history and protected attachment requests", async () => {
  vi.mocked(api.get).mockResolvedValue(response([statement("saved")]));
  render(<ChatInterface apiBase="/admin" studentId="student" parentId="parent"
    teacherName="Veli" onBack={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "rapor.pdf" }));
  const config = expect.objectContaining({ params: { parent_id: "parent" } });
  expect(api.get).toHaveBeenCalledWith("/admin/chat/student", config);
  expect(downloadFile).toHaveBeenCalledWith("/admin/chat/student/attachments/saved", "rapor.pdf", config);
});

it("keeps a rejected file editable when the server rejects it before saving", async () => {
  vi.mocked(api.get).mockResolvedValue(response([]));
  vi.mocked(api.post).mockRejectedValue({ response: { status: 422 } });
  render(<ChatInterface studentId="student" teacherId="teacher" teacherName="Öğretmen" onBack={vi.fn()} />);
  await screen.findByText("Henüz mesaj yok.");
  const file = new File(["invalid bytes"], "invalid.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByLabelText("Sohbet dosyası"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Gönder" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Eki kaldır" })).toBeEnabled();
  expect(screen.queryByRole("button", { name: "Gönderimi kontrol et" })).not.toBeInTheDocument();
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
});

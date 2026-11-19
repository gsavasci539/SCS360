import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ChatInterface } from "../features/parent/ChatInterface";
import { api } from "../lib/api";
import { downloadFile } from "../lib/download";
import { fileSha256 } from "../lib/fileIntegrity";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  unwrap: (response: { data: { data: unknown } }) => response.data.data,
  apiMessage: (error: unknown) => error instanceof Error ? error.message : "Sunucuya ulaşılamadı.",
}));
vi.mock("../lib/download", () => ({ downloadFile: vi.fn() }));
vi.mock("../lib/fileIntegrity", () => ({ fileSha256: vi.fn(async () => "a".repeat(64)) }));

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
  vi.mocked(api.post).mockImplementation(async (_path, body) => {
    requestId = String((body as FormData).get("request_id"));
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
  expect(downloadFile).toHaveBeenCalledWith(`${endpoint}/attachments/${requestId}`, "rapor.pdf",
    expect.objectContaining({ expectedSha256: "a".repeat(64) }));
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(fileSha256).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("Sohbet mesajı")).toHaveValue("");
});

it("keeps the selected parent on admin history and protected attachment requests", async () => {
  vi.mocked(api.get).mockResolvedValue(response([statement("saved")]));
  render(<ChatInterface apiBase="/admin" studentId="student" parentId="parent"
    teacherName="Veli" onBack={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "rapor.pdf" }));
  const config = expect.objectContaining({ params: { parent_id: "parent" } });
  expect(api.get).toHaveBeenCalledWith("/admin/chat/student", config);
  expect(downloadFile).toHaveBeenCalledWith("/admin/chat/student/attachments/saved", "rapor.pdf",
    expect.objectContaining({ params: { parent_id: "parent" }, expectedSha256: "a".repeat(64) }));
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

it("keeps the attachment draft when a saved message has a different fingerprint", async () => {
  const endpoint = "/parent/child/student/chat/teacher";
  let requestId = "";
  vi.mocked(api.get).mockImplementation(async (path) => response(path === endpoint ? []
    : { ...statement(requestId), content: "", attachment_sha256: "b".repeat(64) }));
  vi.mocked(api.post).mockImplementation(async (_, body) => {
    requestId = String((body as FormData).get("request_id"));
    return response(null);
  });
  render(<ChatInterface studentId="student" teacherId="teacher" teacherName="Öğretmen" onBack={vi.fn()} />);
  await screen.findByText("Henüz mesaj yok.");
  const file = new File(["%PDF-1.4"], "rapor.pdf");
  fireEvent.change(screen.getByLabelText("Sohbet dosyası"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Gönder" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Sunucudaki mesaj bilgileri gönderimle eşleşmiyor.");
  expect(screen.getByRole("button", { name: "Gönderimi kontrol et" })).toBeEnabled();
  expect(screen.queryByRole("button", { name: "rapor.pdf" })).not.toBeInTheDocument();
  expect(api.post).toHaveBeenCalledTimes(1);
});

it("does not start a send if the conversation changes during fingerprinting", async () => {
  let finish!: (value: string) => void;
  vi.mocked(fileSha256).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  vi.mocked(api.get).mockResolvedValue(response([]));
  const props = { studentId: "student", teacherName: "Öğretmen", onBack: vi.fn() };
  const view = render(<ChatInterface {...props} teacherId="teacher" />);
  const file = new File(["%PDF-1.4"], "rapor.pdf");
  fireEvent.change(screen.getByLabelText("Sohbet dosyası"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Gönder" }));
  view.rerender(<ChatInterface {...props} teacherId="other" />);
  await act(async () => finish("a".repeat(64)));
  expect(api.post).not.toHaveBeenCalled();
  expect(screen.queryByText("rapor.pdf")).not.toBeInTheDocument();
});

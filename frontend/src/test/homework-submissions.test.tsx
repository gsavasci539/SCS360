import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { HomeworkSubmissions } from "../features/academic/HomeworkSubmissions";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: (reason: Error) => reason.message }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("geciken eski teslim yanıtı velinin yeni yazdığı metni silemez", async () => {
  let first!: (value: unknown) => void;
  let second!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((resolve) => { first = resolve; }))
    .mockImplementationOnce(() => new Promise((resolve) => { second = resolve; }))
    .mockResolvedValue({ data: { data: [{ id: "submission", student_id: "child", status: "SUBMITTED", submission_text: "Kalıcı dosyalı teslim",
      attachment_file_name: "odev.pdf", attachment_url: "/homework/submissions/submission/attachment" }] } });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "submission", status: "SUBMITTED" } } });
  render(<StrictMode><HomeworkSubmissions homeworkId="homework" studentId="child" /></StrictMode>);
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  await act(async () => second({ data: { data: [] } }));
  const input = await screen.findByRole("textbox", { name: "Teslim metni" });
  fireEvent.change(input, { target: { value: "Kalıcı dosyalı teslim" } });
  await act(async () => first({ data: { data: [] } }));
  expect(input).toHaveValue("Kalıcı dosyalı teslim");
  fireEvent.change(screen.getByLabelText("Ödev dosyası"), { target: { files: [new File(["%PDF-1.4"], "odev.pdf", { type: "application/pdf" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Ödevi teslim et" }));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [path, form] = vi.mocked(api.post).mock.calls[0];
  expect(path).toBe("/homework/homework/submit-file");
  expect((form as FormData).get("submission_text")).toBe("Kalıcı dosyalı teslim");
  expect(await screen.findByRole("status")).toHaveTextContent("Ödev teslimi kaydedildi.");
  expect(api.get).toHaveBeenLastCalledWith("/homework/submissions", expect.objectContaining({
    params: { homework_id: "homework", student_id: "child", record_id: "submission", limit: 1 },
  }));
});

it("puan sunucudan doğru geri bildirimle okunana kadar teslimi güncellemez", async () => {
  const row = { id: "submission", student_id: "child", student_name: "İzole öğrenci", status: "SUBMITTED" };
  const stored = { ...row, status: "GRADED", score: 87.25 };
  vi.mocked(api.get)
    .mockResolvedValueOnce({ data: { data: [row] } })
    .mockResolvedValueOnce({ data: { data: [{ ...stored, teacher_feedback: "Önceki geri bildirim" }] } })
    .mockResolvedValueOnce({ data: { data: [{ ...stored, teacher_feedback: "İzole değerlendirme" }] } });
  vi.mocked(api.put).mockResolvedValue({ data: { data: { id: "submission", status: "GRADED" } } });
  render(<HomeworkSubmissions homeworkId="homework" canGrade />);
  fireEvent.change(await screen.findByRole("spinbutton", { name: "Puan" }), { target: { value: "87.25" } });
  fireEvent.change(screen.getByRole("textbox", { name: "Geri bildirim" }), { target: { value: "İzole değerlendirme" } });
  fireEvent.click(screen.getByRole("button", { name: "Notu kaydet" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Puan ve geri bildirim sunucudan doğrulanamadı");
  expect(screen.getByText("Teslim alındı")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Notu kaydet" }));
  expect(await screen.findByText("Puan: 87.25 / 100")).toBeInTheDocument();
});

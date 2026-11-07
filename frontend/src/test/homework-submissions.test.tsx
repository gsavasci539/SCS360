import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { HomeworkSubmissions } from "../features/academic/HomeworkSubmissions";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("geciken eski teslim yanıtı velinin yeni yazdığı metni silemez", async () => {
  let first!: (value: unknown) => void;
  let second!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((resolve) => { first = resolve; }))
    .mockImplementationOnce(() => new Promise((resolve) => { second = resolve; }))
    .mockResolvedValue({ data: { data: [{ id: "submission", student_id: "child", status: "SUBMITTED", submission_text: "Kalıcı dosyalı teslim" }] } });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "submission" } } });
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
});

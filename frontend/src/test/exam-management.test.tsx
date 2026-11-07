import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ExamsPage } from "../features/academic/ExamsPage";
import { api } from "../lib/api";
import { getAnalysis } from "../lib/analysis";
import { ParentReportCards } from "../features/parent/ParentReportCards";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, apiMessage: () => "Sınav verileri alınamadı" }));
vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn() }));
let permissions = new Set<string>();
vi.mock("../lib/workspaceUser", () => ({ useWorkspaceUser: () => ({ permissions: [...permissions], roles: [] }) }));
vi.mock("../stores/auth", () => ({ hasPermission: (_user: unknown, permission: string) => permissions.has(permission) }));
const exam = { id: "exam", class_id: "class", title: "Gerçek sınav", class_name: "A Sınıfı", exam_date: "2026-10-20",
  exam_type: "QUIZ", status: "SCHEDULED", max_score: 80, duration_minutes: 60, weight: 1, start_time: "10:15:00" };
beforeEach(() => {
  permissions = new Set(["exam.read", "exam.write"]);
  vi.mocked(getAnalysis).mockResolvedValue({ data: { data: null } });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/exams" ? {
    items: [exam], total: 1, total_pages: 1, page: 1, page_size: 25,
  } : String(path).endsWith("/roster") ? { items: [{ id: "child", name: "Gerçek Öğrenci", score: 0, result_id: "result" }],
    total: 1, total_pages: 1, page: 1, page_size: 50 } : { items: [], total: 0, total_pages: 0 } } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { created: 0, updated: 1 } } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("sınavdan gerçek sıfır notunu yükler ve boş değere dönüştürmeden günceller", async () => {
  render(<ExamsPage />);
  await screen.findByRole("cell", { name: "Gerçek sınav" });
  expect(screen.getByRole("button", { name: "Yeni sınav" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Notlar ve karne" }));
  const grade = await screen.findByRole("spinbutton", { name: "Gerçek Öğrenci notu" });
  expect(grade).toHaveValue(0);
  fireEvent.change(grade, { target: { value: "40" } });
  fireEvent.click(screen.getByRole("button", { name: "Notları kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/exams/bulk-grade-entry", {
    exam_id: "exam", grades: [{ student_id: "child", score: 40, grade_scale: null, notes: null }],
  }));
  expect(await screen.findByRole("status")).toHaveTextContent("Notlar kaydedildi");
});

it("salt okuma yetkisinde yazma düğmelerini ve kontrollerini sunmaz", async () => {
  permissions = new Set(["exam.read"]); render(<ExamsPage />);
  const table = await screen.findByRole("table");
  expect(within(table).getByRole("cell", { name: "Gerçek sınav" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Yeni sınav" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Sınavı iptal et" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Notlar ve karne" }));
  await screen.findByText("Gerçek Öğrenci");
  expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Notları kaydet" })).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("sınav okuması başarısız olduğunda boş başarı yerine yeniden deneme sağlar", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("timeout")); render(<ExamsPage />);
  expect(await screen.findByText("Sınav verileri alınamadı")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByRole("cell", { name: "Gerçek sınav" })).toBeInTheDocument();
});

it("veli karne ekranı gerçek sıfır ortalamayı ve boş devam bilgisini gösterir", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [{ id: "card", academic_year: "2026-2027", semester: "FALL", gpa: 0, attendance_rate: null }], total: 1, total_pages: 1 } } });
  render(<ParentReportCards studentId="child" />);
  expect(await screen.findByText("0.00 / 4")).toBeInTheDocument();
  expect(screen.getByText("Veri yok veya erişim kapalı")).toBeInTheDocument();
  expect(screen.queryByText("%95")).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

it("çocuk değiştiğinde geciken eski karne cevabını göstermez", async () => {
  let finish: (value: unknown) => void = () => {};
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  const rendered = render(<ParentReportCards key="old" studentId="old-child" />);
  vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [{ id: "new-card", teacher_comments: "Yeni yorum" }], total: 1, total_pages: 1 } } });
  rendered.rerender(<ParentReportCards key="new" studentId="new-child" />);
  expect(await screen.findByText("Öğretmen: Yeni yorum")).toBeInTheDocument();
  finish({ data: { data: { items: [{ id: "old-card", teacher_comments: "Eski gizli yorum" }], total: 1, total_pages: 1 } } });
  await waitFor(() => expect(screen.queryByText(/Eski gizli yorum/)).not.toBeInTheDocument());
});

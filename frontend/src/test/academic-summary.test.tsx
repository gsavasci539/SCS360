import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AIAnalyticsPage } from "../features/ai/AIAnalyticsPage";
import { canAnalyze, getAnalysis } from "../lib/analysis";

vi.mock("../lib/analysis", () => ({ canAnalyze: vi.fn(), getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ apiMessage: () => "Akademik veriler alınamadı" }));
const summary = { analysis_kind: "RECORDED_GRADES", ai_model: null, total_analyzed: 1, total_students: 2,
  students_without_grades: 1, risk_threshold: 70, total_risk_students: 1, prediction_available: false,
  risk_students: [{ student_id: "child", student_name: "Gerçek Öğrenci", current_average: 25,
    grade_count: 2, trend: "veri yetersiz", confidence: null, predicted_grade: null, risk_level: "yüksek" }], recommendations: [] };
beforeEach(() => {
  vi.mocked(canAnalyze).mockImplementation((path) => path.split("?")[0] === "/ai/ai-academic-predictions");
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: summary } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("gerçek kayıt özeti ve eksik değerlendirmeyi gösterir; tahmin veya güven yüzdesi uydurmaz", async () => {
  render(<AIAnalyticsPage />);
  expect(await screen.findByRole("heading", { name: "Kayıtlı not analizi" })).toBeInTheDocument();
  expect(screen.getByText("Gerçek Öğrenci")).toBeInTheDocument();
  expect(screen.getByText(/1 öğrenci için seçili dönemde değerlendirme kaydı yok/)).toBeInTheDocument();
  expect(screen.queryByText(/Güven Eşiği/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Tahmin:/)).not.toBeInTheDocument();
  expect(getAnalysis).toHaveBeenCalledTimes(1);
  expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-academic-predictions?days=30", expect.objectContaining({ signal: expect.any(AbortSignal) }));
  fireEvent.change(screen.getByRole("combobox", { name: "Analiz dönemi" }), { target: { value: "7" } });
  await waitFor(() => expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-academic-predictions?days=7", expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

it("başarısız analiz boş başarı gibi görünmez ve yeniden denenebilir", async () => {
  vi.mocked(getAnalysis).mockRejectedValueOnce(new Error("timeout")); render(<AIAnalyticsPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Akademik veriler alınamadı");
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByText("Gerçek Öğrenci")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("izinli analiz yoksa istekte bulunmadan açık bir boş durum gösterir", async () => {
  vi.mocked(canAnalyze).mockReturnValue(false); render(<AIAnalyticsPage />);
  expect(await screen.findByText("Yetkiniz kapsamında analiz bulunmuyor")).toBeInTheDocument();
  expect(getAnalysis).not.toHaveBeenCalled();
});

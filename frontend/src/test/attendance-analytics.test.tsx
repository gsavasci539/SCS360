import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { AIAnalyticsPage } from "../features/ai/AIAnalyticsPage";
import { AttendancePage } from "../features/attendance/AttendancePage";
import { canAnalyze, getAnalysis } from "../lib/analysis";
import { api } from "../lib/api";

vi.mock("../lib/analysis", () => ({ canAnalyze: vi.fn(), getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Yoklama özeti alınamadı" }));
vi.mock("../stores/auth", () => ({ useAuthStore: (select: (state: { can: () => boolean }) => unknown) => select({ can: () => false }) }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));
vi.mock("recharts", () => ({ ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => <div>{children}</div>, Bar: () => null,
  CartesianGrid: () => null, Tooltip: () => null, XAxis: () => null, YAxis: () => null }));

const recorded = { current_rate: 0, predicted_rate: 98, ai_model: null, prediction_available: false,
  total_records: 2, total_analyzed: 1, students_without_records: 1, total_risk_students: 1,
  monitoring_threshold: 80, period_start: "2026-11-01", period_end: "2026-11-11",
  requires_review: false, risk_results_limited: false,
  risk_alerts: [{ student_id: "pupil", student_name: "Seçili öğrenci", current_rate: 0, predicted_rate: 98, record_count: 2, trend: "veri yetersiz" }],
  patterns: [{ student_id: "pupil", student_name: "Seçili öğrenci", patterns: [{ day: "Pazartesi", rate: 100, record_count: 2 }] }],
  recommendations: ["Bir öğrencinin kayıtlı devam oranı izleme eşiğinin altında."] };

beforeEach(() => {
  vi.mocked(canAnalyze).mockImplementation((path) => ["/ai/ai-attendance-predictions", "/ai/attendance-analysis"].includes(path.split("?")[0]));
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: recorded } });
  vi.mocked(api.get).mockResolvedValue({ data: { data: [] } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("analiz ekranında gerçek sıfırı, öğrenciye ait örüntüyü ve dönem seçimini gösterir", async () => {
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  const panel = await screen.findByRole("region", { name: "Kayıtlı devam özeti" });
  expect(within(panel).getByRole("table", { name: "Kayıtlı devam izleme listesi" })).toHaveTextContent("Seçili öğrenci");
  expect(within(panel).getByText("Pazartesi: %100 devamsızlık · 2 kayıt")).toBeInTheDocument();
  expect(within(panel).getAllByText("%0").length).toBeGreaterThan(0);
  expect(screen.queryByText(/Tahmin:|Tahmini Oran|Pattern Recognition|%98/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "90" } });
  await waitFor(() => expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-attendance-predictions?days=90", expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

it("boş yoklamada oran veya olumlu model sonucu uydurmaz", async () => {
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { ...recorded, current_rate: null,
    total_records: 0, total_analyzed: 0, students_without_records: 2, total_risk_students: 0,
    risk_alerts: [], patterns: [], recommendations: ["Seçili dönemde yoklama kaydı yok; devam oranı hesaplanamıyor."] } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  const panel = await screen.findByRole("region", { name: "Kayıtlı devam özeti" });
  expect(within(panel).getByText("—")).toBeInTheDocument();
  expect(within(panel).getByText("Seçili dönemde yoklama kaydı yok; devam oranı hesaplanamıyor.")).toBeInTheDocument();
  expect(within(panel).queryByText("%0")).not.toBeInTheDocument();
});

it("analiz arızasını yeniden deneyebilir", async () => {
  vi.mocked(getAnalysis).mockRejectedValueOnce(new Error("503"));
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Yoklama özeti alınamadı");
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByRole("region", { name: "Kayıtlı devam özeti" })).toBeInTheDocument();
});

it("yoklama ekranı da aynı gerçek özeti gösterir ve tahmin alanı içermez", async () => {
  render(<AttendancePage />);
  expect(await screen.findByRole("region", { name: "Kayıtlı devam özeti" })).toBeInTheDocument();
  expect(screen.queryByText(/Tahmini Oran|AI Devamsızlık Analizi|%98/)).not.toBeInTheDocument();
});

it("yoklama ekranındaki özet hatası görünürdür ve yeniden denenir", async () => {
  vi.mocked(getAnalysis).mockRejectedValueOnce(new Error("503"));
  render(<AttendancePage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Yoklama özeti alınamadı");
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByRole("region", { name: "Kayıtlı devam özeti" })).toBeInTheDocument();
});

it("analiz yetkisi yoksa isteği ve paneli açmaz", async () => {
  vi.mocked(canAnalyze).mockReturnValue(false);
  render(<AttendancePage />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(getAnalysis).not.toHaveBeenCalled();
  expect(screen.queryByRole("region", { name: "Kayıtlı devam özeti" })).not.toBeInTheDocument();
});

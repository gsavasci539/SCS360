import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { AIAnalyticsPage } from "../features/ai/AIAnalyticsPage";
import { canAnalyze, getAnalysis } from "../lib/analysis";

vi.mock("../lib/analysis", () => ({ canAnalyze: vi.fn(), getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ apiMessage: () => "Analiz alınamadı" }));
vi.mock("recharts", () => ({ ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => <div>{children}</div>, Bar: () => null, CartesianGrid: () => null,
  Tooltip: () => null, XAxis: () => null, YAxis: () => null }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("genel bakışta eksik oranı sıfır veya memnuniyet olarak göstermez ve dönem API'ye gider", async () => {
  vi.mocked(canAnalyze).mockImplementation((path) => path.split("?")[0] === "/ai/insights-report");
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: {
    period_start: "2026-11-01", period_end: "2026-11-11", requires_review: false, priority_actions: [],
    insights: { academic_performance: { average_grade: null, at_risk_students: 0 },
      attendance: { overall_rate: null, trend: "veri yetersiz" }, financial: { collection_rate: null }, parent_satisfaction: { score: null, sentiment: null } },
  } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  await screen.findByRole("region", { name: "Kayıtlı genel değerlendirme" });
  expect(screen.getAllByText("—")).toHaveLength(3);
  expect(screen.getByText("Ölçülmedi")).toBeInTheDocument();
  expect(screen.queryByText(/Time Series|Pattern Recognition|Akademik AI Skoru|Tüm göstergeler normal/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "90" } });
  await waitFor(() => expect(getAnalysis).toHaveBeenCalledWith("/ai/insights-report?days=90", expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

it("operasyonda kayıtlı sayıları gösterir, personel verimliliği ve AI skoru uydurmaz", async () => {
  vi.mocked(canAnalyze).mockImplementation((path) => path === "/ai/ai-operational-optimization");
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: {
    counts: { class_count: 2, active_students: 2, assigned_active_students: 2, unassigned_active_students: 0,
      known_capacity: 40, classes_without_capacity: 0, staff_count: 1 },
    optimization_scores: { classroom_utilization: 5, staff_efficiency: null, overall_score: null },
    over_capacity_classes: [], resource_allocation: { recommended_actions: [] },
  } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  await screen.findByRole("region", { name: "Kayıtlı operasyon özeti" });
  expect(screen.getByText("%5")).toBeInTheDocument();
  expect(screen.getByText("40 tanımlı kontenjan")).toBeInTheDocument();
  expect(screen.queryByText(/AI Genel Skor|Personel Verimliliği|Resource Optimization/)).not.toBeInTheDocument();
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { AIAnalyticsPage } from "../features/ai/AIAnalyticsPage";
import { canAnalyze, getAnalysis } from "../lib/analysis";

vi.mock("../lib/analysis", () => ({ canAnalyze: vi.fn(), getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ apiMessage: () => "Finans kayıtları alınamadı" }));
vi.mock("recharts", () => ({ ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => <div>{children}</div>, Bar: () => null,
  CartesianGrid: () => null, Tooltip: () => null, XAxis: () => null, YAxis: () => null }));
const recorded = { id: "financial", analysis_type: "recorded_finance", ai_model: null, forecast_available: false,
  collection_rate: 25, collected_total: "25.00", outstanding_debt: "75.00", total_expected: "75.00", overdue_amount: "0.00", payment_count: 3,
  as_of: "2026-11-04", period_start: "2026-11-04", period_end_exclusive: "2027-05-01", months: 6,
  historical_monthly: [{ month: "2026-10", collected_amount: "10.00", payment_count: 1 }, { month: "2026-11", collected_amount: "15.00", payment_count: 2 }],
  monthly_forecast: [{ month: "2026-11", scheduled_amount: "75.00", debt_count: 1 }, { month: "2026-12", scheduled_amount: "0.00", debt_count: 0 }],
  risk_assessment: { level: "unknown" }, predictions: [], risk_parents: [], recommendations: [] };
beforeEach(() => {
  vi.mocked(canAnalyze).mockImplementation((path) => path.split("?")[0] === "/ai/ai-financial-predictions");
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: recorded } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("shows actual payment history and due calendar with a real period selector", async () => {
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Kayıtlı finans analizi" })).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Kayıtlı tahsilat geçmişi" })).toHaveTextContent("₺10");
  expect(screen.getByRole("table", { name: "Kayıtlı vade takvimi" })).toHaveTextContent("₺75");
  expect(screen.getByRole("region", { name: "Aylık kayıtlı tahsilat grafiği" })).toBeInTheDocument();
  expect(screen.queryByText(/Time series|Risk Skoru|Riskli Veliler|AI Nakit Akışı/)).not.toBeInTheDocument();
  expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-financial-predictions?months=6", expect.objectContaining({ signal: expect.any(AbortSignal) }));
  fireEvent.change(screen.getByRole("combobox", { name: "Finans vade dönemi" }), { target: { value: "3" } });
  await waitFor(() => expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-financial-predictions?months=3", expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

it("shows missing financial history and unknown amounts without inventing zero income or a model", async () => {
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { ...recorded,
    collection_rate: null, collected_total: null, outstanding_debt: null, total_expected: null, overdue_amount: null,
    historical_monthly: [], monthly_forecast: [], payment_count: 0, requires_review: true } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByText("Henüz tamamlanmış tahsilat kaydı bulunmuyor.")).toBeInTheDocument();
  expect(screen.getByText("Açık borç").nextElementSibling).toHaveTextContent("—");
  expect(screen.queryByRole("region", { name: "Aylık kayıtlı tahsilat grafiği" })).not.toBeInTheDocument();
  expect(screen.queryByText(/₺0|50.000|Time Series|Yüksek/)).not.toBeInTheDocument();
});

it("financial analysis failures can be retried instead of showing a successful empty report", async () => {
  vi.mocked(getAnalysis).mockRejectedValueOnce(new Error("unavailable"));
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Finans kayıtları alınamadı");
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByRole("heading", { name: "Kayıtlı finans analizi" })).toBeInTheDocument();
});

it("does not describe unreadable completed payment records as an empty ledger", async () => {
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { ...recorded,
    historical_monthly: [], payment_count: 1, invalid_payment_count: 1, collected_total: null, requires_review: true } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByText("Tahsilat kayıtları incelenmeli; aylık dağılım gösterilemiyor.")).toBeInTheDocument();
  expect(screen.queryByText("Henüz tamamlanmış tahsilat kaydı bulunmuyor.")).not.toBeInTheDocument();
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AIAnalyticsPage } from "../features/ai/AIAnalyticsPage";
import { canAnalyze, getAnalysis } from "../lib/analysis";

vi.mock("../lib/analysis", () => ({ canAnalyze: vi.fn(), getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ apiMessage: () => "Veli kayıtları alınamadı" }));
const recorded = { analysis_type: "recorded_parent_engagement", ai_model: null, sentiment_available: false,
  as_of: "2026-11-04", period_start: "2026-10-06", period_end_exclusive: "2026-11-05", analysis_period_days: 30,
  registration_metrics: { total_records: 3, records_with_contact: 2, records_without_contact: 1, account_linked_records: 1,
    notification_allowed_records: 1, notification_declined_records: 2, notification_unknown_records: 0,
    contact_availability_rate: 66.7, notification_consent_rate: 33.3 },
  communication_metrics: { record_count: 5, sent_count: 1, pending_count: 1, failed_count: 1, cancelled_count: 1,
    unknown_count: 1, completed_attempt_count: 2, send_success_rate: 50 }, requires_review: true,
  sentiment_analysis: { overall_sentiment: "unknown", sentiment_score: null, confidence: null } };
beforeEach(() => {
  vi.mocked(canAnalyze).mockImplementation((path) => path.split("?")[0] === "/ai/ai-parent-sentiment");
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: recorded } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("shows factual parent contact records and recipient statuses without mood or confidence claims", async () => {
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Veli iletişim özeti" })).toBeInTheDocument();
  expect(screen.getByText("Veli iletişim kaydı").nextElementSibling).toHaveTextContent("3");
  expect(screen.getByText("İletişim bilgisi olan kayıt").nextElementSibling).toHaveTextContent("2");
  expect(screen.getByRole("table", { name: "Veli gönderim kayıtları" })).toHaveTextContent("Gönderildi");
  expect(screen.queryByText(/AI Duygu Analizi|Etkileşim Skoru|Güven Oranı|pozitif|negatif/)).not.toBeInTheDocument();
  expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-parent-sentiment?days=30", expect.objectContaining({ signal: expect.any(AbortSignal) }));
  fireEvent.change(screen.getByRole("combobox", { name: "Veli iletişim dönemi" }), { target: { value: "7" } });
  await waitFor(() => expect(getAnalysis).toHaveBeenCalledWith("/ai/ai-parent-sentiment?days=7", expect.objectContaining({ signal: expect.any(AbortSignal) })));
});

it("distinguishes a known empty record count from an unavailable delivery rate", async () => {
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { ...recorded,
    registration_metrics: { ...recorded.registration_metrics, total_records: 0, records_with_contact: 0, records_without_contact: 0,
      account_linked_records: 0, notification_allowed_records: 0, notification_declined_records: 0,
      contact_availability_rate: null, notification_consent_rate: null },
    communication_metrics: { ...recorded.communication_metrics, record_count: 0, sent_count: 0, pending_count: 0,
      failed_count: 0, cancelled_count: 0, unknown_count: 0, completed_attempt_count: 0, send_success_rate: null }, requires_review: false } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByText("Bu dönemde veli kaydına bağlı gönderim kaydı bulunmuyor.")).toBeInTheDocument();
  expect(screen.getByText("Veli iletişim kaydı").nextElementSibling).toHaveTextContent("0");
  expect(screen.getByText("Sonuçlanan gönderimlerde gönderildi oranı").nextElementSibling).toHaveTextContent("—");
});

it("retains an actual zero send success rate and never exposes contact payloads", async () => {
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { ...recorded,
    communication_metrics: { ...recorded.communication_metrics, sent_count: 0, failed_count: 2, send_success_rate: 0 },
    private_contact: "private-parent@example.invalid" } } });
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Veli iletişim özeti" })).toBeInTheDocument();
  expect(screen.getByText("Sonuçlanan gönderimlerde gönderildi oranı").nextElementSibling).toHaveTextContent("%0");
  expect(screen.queryByText(/private-parent/)).not.toBeInTheDocument();
});

it("does not hide query errors behind an empty parent report", async () => {
  vi.mocked(getAnalysis).mockRejectedValueOnce(new Error("unavailable"));
  render(<MemoryRouter><AIAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Veli kayıtları alınamadı");
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByRole("heading", { name: "Veli iletişim özeti" })).toBeInTheDocument();
});

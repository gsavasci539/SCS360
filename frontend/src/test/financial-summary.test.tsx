import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { PaymentForecastCard } from "../features/finance/PaymentForecastCard";
import { PaymentDetailPage, ReceiptDetailPage, ReceiptsPage } from "../features/finance/FinancePages";

const unknown = { id: "summary", total_expected: null, outstanding_debt: null, overdue_amount: null, collected_total: null,
  collection_rate: null, risk_assessment: "unknown", requires_review: true };
vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn(async () => ({ data: { data: {
  total_expected: null, outstanding_debt: null, overdue_amount: null, collected_total: null,
  collection_rate: null, risk_assessment: "unknown", requires_review: true } } })) }));
vi.mock("../lib/api", () => ({ apiMessage: () => "Error", api: { get: vi.fn(async (path: string) => ({ data: { data:
  path === "/receipts" ? [] : { id: "record", receipt_number: "RCP-TEST", amount: "25", remaining_debt: "75", status: "ACTIVE", payment_date: "2026-11-04" } } })) } }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));
afterEach(cleanup);

it("shows unknown totals explicitly and never classifies missing data as high risk", () => {
  render(<PaymentForecastCard summary={unknown} />);
  expect(screen.getByRole("heading", { name: "Tahsilat özeti" })).toBeInTheDocument();
  expect(screen.getByText("Açık borç").nextElementSibling).toHaveTextContent("—");
  expect(screen.getByText("Tahsilat oranı").nextElementSibling).toHaveTextContent("—");
  expect(screen.getByRole("status")).toHaveTextContent("incelenmeli");
  expect(screen.queryByText("Yüksek")).not.toBeInTheDocument();
  expect(screen.queryByText(/₺0/)).not.toBeInTheDocument();
});

it("retains a real zero balance and collection rate", () => {
  render(<PaymentForecastCard summary={{ id: "summary", total_expected: "0.00", outstanding_debt: "0", overdue_amount: 0, collected_total: "0", collection_rate: 0 }} />);
  expect(screen.getByText("Açık borç").nextElementSibling).toHaveTextContent("₺0");
  expect(screen.getByText("Tahsilat oranı").nextElementSibling).toHaveTextContent("%0");
});

it("shows the recorded as-of date and exclusive contract range without inventing a default period", () => {
  const { rerender } = render(<PaymentForecastCard summary={{ ...unknown, as_of: "2026-12-31", period_start: "2026-12-31", period_end_exclusive: "2027-03-01", months: 3 }} />);
  expect(screen.getByText(/^Kayıt tarihi:/)).toHaveTextContent("31 Ara 2026");
  expect(screen.getByText(/^Vade dönemi/)).toHaveTextContent("3 takvim ayı");
  expect(screen.getByText(/^Vade dönemi/)).toHaveTextContent("01 Mar 2027 tarihinden önceki vadeler");
  rerender(<PaymentForecastCard summary={{ ...unknown, as_of: "2026-02-31", period_start: "2027-03-01", period_end_exclusive: "2026-12-31", months: 99 }} />);
  expect(screen.queryByText(/^Kayıt tarihi:/)).not.toBeInTheDocument();
  expect(screen.queryByText(/^Vade dönemi/)).not.toBeInTheDocument();
});

it.each([ReceiptsPage, ReceiptDetailPage, PaymentDetailPage])("receipt and payment views share the unknown-safe recorded summary", async (View) => {
  render(<MemoryRouter><View /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Tahsilat özeti" })).toBeInTheDocument();
  expect(screen.queryByText("Yüksek")).not.toBeInTheDocument();
  expect(screen.getByText("Dönem vadeli bakiye").nextElementSibling).toHaveTextContent("—");
});

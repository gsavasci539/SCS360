import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));

const child = "00000000-0000-4000-8000-000000000001";
const sibling = "00000000-0000-4000-8000-000000000002";
const debt = "00000000-0000-4000-8000-000000000003";
const receipt = "00000000-0000-4000-8000-000000000004";
const receiptPath = `/parent/child/${child}/debts/${debt}/receipts`;
const validPage = { student_id: child, debt_id: debt, total: 1, items: [{
  id: receipt, receipt_number: "TEST-MAKBUZ", issued_at: "2026-11-20T12:00:00+03:00",
  status: "ACTIVE", amount: "25.10", remaining_debt: "100.25",
}] };

function portalData(path: string) {
  if (path === "/parent/my-children/options?module=finances") return [
    { student_id: child, first_name: "Deniz" }, { student_id: sibling, first_name: "Ada" },
  ];
  if (path === `/parent/child/${child}/financial-invoices`) return {
    student_id: child, total_remaining: "100.25", online_payment_available: false,
    invoices: [{ debt_id: debt, remaining_amount: "100.25", paid_amount: "25.10", status: "PARTIALLY_PAID", description: "Kasım ödemesi" }],
  };
  if (path === `/parent/child/${sibling}/financial-invoices`) return { student_id: sibling, invoices: [] };
  return null;
}

beforeEach(() => {
  useAuthStore.getState().setUser({ id: "parent", organization_id: "school", first_name: "Veli", last_name: "Test",
    email: "parent@test.invalid", roles: [], branch_ids: [], is_super_admin: false, permissions: ["parent.view_finances"] });
});

afterEach(() => {
  cleanup();
  useAuthStore.getState().clearSession();
  vi.resetAllMocks();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("kısmi tahsilatın makbuzunu çocuk ve borç kapsamından okur ve sunucu PDF'sini indirir", async () => {
  const pdf = new Blob(["%PDF-1.7"], { type: "application/pdf" });
  const createObjectURL = vi.fn(() => "blob:receipt-test");
  vi.stubGlobal("URL", class extends URL {
    static createObjectURL = createObjectURL;
    static revokeObjectURL = vi.fn();
  });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === `${receiptPath}/${receipt}/pdf`) return { data: pdf };
    return { data: { data: path === receiptPath ? validPage : portalData(path) } };
  });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Makbuz incele" }));
  expect(await screen.findByText("TEST-MAKBUZ")).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith(receiptPath, expect.objectContaining({ params: { page: 1, page_size: 20 } }));
  fireEvent.click(screen.getByRole("button", { name: "PDF indir" }));
  await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
  expect(createObjectURL).toHaveBeenCalledWith(pdf);
  expect(api.get).toHaveBeenCalledWith(`${receiptPath}/${receipt}/pdf`, expect.objectContaining({ responseType: "blob" }));
});

it("çocuk değiştiğinde makbuz listesini kapatır ve geciken yanıtı iptal eder", async () => {
  let completeRequest!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path) => path === receiptPath
    ? new Promise((resolve) => { completeRequest = resolve; })
    : { data: { data: portalData(path) } });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Makbuz incele" }));
  expect(await screen.findByRole("dialog", { name: "Tahsilat makbuzları" })).toBeInTheDocument();
  const options = vi.mocked(api.get).mock.calls.find(([path]) => path === receiptPath)?.[1];
  fireEvent.change(screen.getByRole("combobox", { name: "Öğrenci Seçin" }), { target: { value: sibling } });
  expect(options?.signal?.aborted).toBe(true);
  await act(async () => completeRequest({ data: { data: validPage } }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByText("TEST-MAKBUZ")).not.toBeInTheDocument();
});

it("çocuk değiştiğinde başlamış PDF indirme isteği dosya kaydetmez", async () => {
  let completeDownload!: (value: unknown) => void;
  const pdfPath = `${receiptPath}/${receipt}/pdf`;
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  vi.mocked(api.get).mockImplementation(async (path) => path === pdfPath
    ? new Promise((resolve) => { completeDownload = resolve; })
    : { data: { data: path === receiptPath ? validPage : portalData(path) } });
  render(<MemoryRouter><ParentPortalPage view="finances" /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Makbuz incele" }));
  fireEvent.click(await screen.findByRole("button", { name: "PDF indir" }));
  const options = vi.mocked(api.get).mock.calls.find(([path]) => path === pdfPath)?.[1];
  fireEvent.change(screen.getByRole("combobox", { name: "Öğrenci Seçin" }), { target: { value: sibling } });
  expect(options?.signal?.aborted).toBe(true);
  await act(async () => completeDownload({ data: new Blob(["%PDF-1.7"], { type: "application/pdf" }) }));
  expect(click).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

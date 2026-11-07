import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ReceiptPrintPage } from "../features/finance/ReceiptPrintPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("iptal durumunu API'den alır ve iki makbuz kopyasını açıkça işaretler", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { id: "receipt-1", receipt_number: "RCP-TEST", status: "CANCELLED",
    student_name: "Çağrı Şahin", branch_name: "Merkez", organization_name: "Örnek Kurum", amount: "10.01" } } });
  render(<MemoryRouter initialEntries={["/receipts/receipt-1/print"]}><Routes><Route path="/receipts/:id/print" element={<ReceiptPrintPage />} /></Routes></MemoryRouter>);
  expect(await screen.findAllByRole("heading", { name: "İPTAL EDİLMİŞ MAKBUZ" })).toHaveLength(2);
  expect(screen.queryByRole("heading", { name: "TAHSİLAT MAKBUZU" })).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/receipts/receipt-1");
});

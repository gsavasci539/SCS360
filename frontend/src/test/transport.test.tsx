import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BusPage } from "../features/transport/BusPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Servis verileri alınamadı" }));
beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/bus/routes" ? [
    { id: "route", route_name: "Kuzey rotası", vehicle_plate: "34 SCS 360", status: "ACTIVE", capacity: 24, driver_name: null },
  ] : path === "/bus/attendance?limit=50" ? [
    { id: "attendance", route_id: "route", student_name: "Deniz Kabul", date: "2026-11-03", status: "PRESENT" },
  ] : { recommendations: ["Sabit öneri"] } } }));
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("API sözleşmesindeki plaka, rota durumu ve katılım tarihini gösterir", async () => {
  render(<BusPage />);
  await screen.findByText("34 SCS 360");
  const tables = screen.getAllByRole("table");
  expect(within(tables[0]).getByText("Aktif")).toBeInTheDocument();
  expect(within(tables[1]).getByText("Kuzey rotası")).toBeInTheDocument();
  expect(within(tables[1]).getByText("03 Kas 2026")).toBeInTheDocument();
  expect(screen.queryByText("undefined")).not.toBeInTheDocument();
  expect(screen.queryByText("null")).not.toBeInTheDocument();
});

it("kayıtlı rota özeti analiz sağlayıcısına bağımlı değildir", async () => {
  render(<BusPage />);
  const summary = await screen.findByLabelText("Listelenen servis rotalarının özeti");
  expect(summary).toHaveTextContent("Aktif rota: 1");
  expect(summary).toHaveTextContent("Kapasite: 24");
  expect(screen.queryByText("Sabit öneri")).not.toBeInTheDocument();
});

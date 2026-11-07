import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BusRouteManager } from "../features/transport/BusRouteManager";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: () => "İşlem tamamlanamadı" }));
beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/bus/options" ? { branches: [{ id: "school-branch", name: "Seçilen okul şubesi" }], drivers: [], students: [], today: "2026-11-04" } : [] } }));
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("rota oluşturma zaman aşımında aynı kimlik ve seçilen kurum şubesiyle tekrarlanır", async () => {
  const close = vi.fn(); vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce({ data: { data: { id: "route" } } });
  render(<BusRouteManager routeId={null} canWrite onClose={close} onRefresh={vi.fn()} />);
  const branch = await screen.findByRole("option", { name: "Seçilen okul şubesi" }); expect(branch).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.change(screen.getByRole("combobox", { name: "Rota şubesi" }), { target: { value: "school-branch" } });
  fireEvent.change(screen.getByLabelText("Rota adı"), { target: { value: "Kuzey" } });
  const form = screen.getByRole("form", { name: "Servis rotasını kaydet" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.submit(form); await screen.findByRole("alert"); await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.submit(form); await waitFor(() => expect(close).toHaveBeenCalledOnce());
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(vi.mocked(api.post).mock.calls[1]);
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual(expect.objectContaining({ branch_id: "school-branch", route_name: "Kuzey", capacity: 40 }));
});

it("yalnız okuma rolü rota veya durak yazma formu alamaz", async () => {
  render(<BusRouteManager routeId="route" canWrite={false} onClose={vi.fn()} onRefresh={vi.fn()} />);
  await screen.findByRole("heading", { name: "Duraklar" });
  expect(screen.queryByRole("form")).not.toBeInTheDocument(); expect(api.post).not.toHaveBeenCalled(); expect(api.put).not.toHaveBeenCalled();
});

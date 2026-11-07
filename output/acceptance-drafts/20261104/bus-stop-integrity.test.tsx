import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BusRouteManager } from "../features/transport/BusRouteManager";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, apiMessage: () => "İşlem tamamlanamadı" }));
let viewer = { id: "bus-actor-a", organization_id: "school-a" };
vi.mock("../lib/workspaceUser", () => ({ useWorkspaceUser: () => viewer }));
const stop = { id: "stop-a", route_id: "route", stop_name: "First stop", stop_order: 1, latitude: 0, longitude: 0, estimated_arrival: "08:20", version: "a".repeat(64) };
beforeEach(() => {
  sessionStorage.clear(); viewer = { id: "bus-actor-a", organization_id: "school-a" };
  vi.mocked(api.get).mockImplementation(async (path, config) => ({ data: { data: path === "/bus/routes/route" ? {
    id: "route", branch_id: "branch", route_name: "Own route", updated_at: "2026-11-04T12:00:00Z", driver_id: "current-driver",
  } : path === "/bus/options" ? {
    branches: [{ id: "branch", name: "Own branch" }], drivers: [{ id: "current-driver", name: "Current Driver" }], students: [{ id: "student", name: "Own Student" }],
    today: "2026-11-04", driver_page: config?.params?.driver_page || 1, driver_total_pages: 2,
  } : path === "/bus/stops" ? [stop] : path === "/bus/attendance" ? [] : null } }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.resetAllMocks(); });

it("durak zaman aşımında ilk gövdeyi ve kimliği kilitler, yeni satıra taşımaz", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("timeout")).mockImplementationOnce(async (_path, body) => ({ data: { data: { id: (body as { request_id: string }).request_id, version: "b".repeat(64) } } }));
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  const form = await screen.findByRole("form", { name: "Servis durağını kaydet" });
  fireEvent.change(within(form).getByLabelText("Durak adı"), { target: { value: "New stop" } });
  fireEvent.change(within(form).getByLabelText("Durak sırası"), { target: { value: "2" } });
  fireEvent.submit(form); await screen.findByRole("alert");
  expect(within(form).getByLabelText("Durak adı")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Durağı düzenle" })).toBeDisabled();
  fireEvent.submit(form); await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.post).mock.calls[1]).toEqual(vi.mocked(api.post).mock.calls[0]);
});

it("durak düzenlemesi version gönderir ve timeout sonrası aynı hedefi tekrarlar", async () => {
  vi.mocked(api.put).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce({ data: { data: { id: stop.id, version: "b".repeat(64) } } });
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Durağı düzenle" }));
  const form = screen.getByRole("form", { name: "Servis durağını kaydet" });
  fireEvent.change(within(form).getByLabelText("Durak adı"), { target: { value: "Updated stop" } });
  fireEvent.submit(form); await screen.findByRole("alert");
  expect(vi.mocked(api.put).mock.calls[0]).toEqual(["/bus/stops/stop-a", expect.objectContaining({ expected_version: stop.version, stop_name: "Updated stop" })]);
  expect(within(form).getByRole("button", { name: "Yeni durak" })).toBeDisabled();
  fireEvent.submit(form); await waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.put).mock.calls[1]).toEqual(vi.mocked(api.put).mock.calls[0]);
});

it("sürücü araması ve sayfalama mevcut atamayı ve öğrenci seçimini korur", async () => {
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  await screen.findByRole("option", { name: "Current Driver" });
  fireEvent.change(screen.getByRole("combobox", { name: "Servis öğrencisi" }), { target: { value: "student" } });
  fireEvent.change(screen.getByLabelText("Rota sürücüsü ara"), { target: { value: "Driver104" } });
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([path, config]) => path === "/bus/options" && config?.params?.driver_search === "Driver104" && config?.params?.selected_driver_id === "current-driver")).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Sonraki sürücüler" }));
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([path, config]) => path === "/bus/options" && config?.params?.driver_page === 2)).toBe(true));
  expect(screen.getByRole("combobox", { name: "Servis öğrencisi" })).toHaveValue("student");
  expect(screen.getByRole("combobox", { name: "Rota sürücüsü", exact: true })).toHaveValue("current-driver");
});

it("belirsiz durak isteğini yeniden açmada aynı hedef ve gövdeyle sürdürür", async () => {
  vi.mocked(api.put).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce({ data: { data: { id: stop.id, version: "b".repeat(64) } } });
  const mounted = render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Durağı düzenle" }));
  let form = screen.getByRole("form", { name: "Servis durağını kaydet" });
  fireEvent.change(within(form).getByLabelText("Durak adı"), { target: { value: "Persistent stop" } });
  fireEvent.submit(form); await screen.findByRole("alert");
  const original = vi.mocked(api.put).mock.calls[0]; mounted.unmount();
  const reopened = render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  form = screen.getByRole("form", { name: "Servis durağını kaydet" });
  expect(within(form).getByLabelText("Durak adı")).toHaveValue("Persistent stop");
  expect(within(form).getByLabelText("Durak adı")).toBeDisabled();
  fireEvent.submit(form); await waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.put).mock.calls[1]).toEqual(original);
  await screen.findByText("Durak kaydedildi"); reopened.unmount();
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  expect(await screen.findByText("Durak kaydedildi")).toBeInTheDocument();
  expect(api.put).toHaveBeenCalledTimes(2);
});

it("durak taslağını farklı kullanıcı ve kuruma taşımaz", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("timeout"));
  const mounted = render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  const form = await screen.findByRole("form", { name: "Servis durağını kaydet" });
  fireEvent.change(within(form).getByLabelText("Durak adı"), { target: { value: "Private draft" } });
  fireEvent.change(within(form).getByLabelText("Durak sırası"), { target: { value: "2" } });
  fireEvent.submit(form); await screen.findByRole("alert"); mounted.unmount();
  viewer = { ...viewer, organization_id: "school-b" };
  const otherSchool = render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  expect(screen.getByLabelText("Durak adı")).toHaveValue(""); otherSchool.unmount();
  viewer = { id: "bus-actor-b", organization_id: "school-a" };
  const otherActor = render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  expect(screen.getByLabelText("Durak adı")).toHaveValue(""); otherActor.unmount();
  viewer = { id: "bus-actor-a", organization_id: "school-a" };
  const otherRoute = render(<BusRouteManager routeId="another-route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  expect(screen.getByLabelText("Durak adı")).toHaveValue(""); otherRoute.unmount();
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  expect(screen.getByLabelText("Durak adı")).toHaveValue("Private draft");
});

it("durak isteği gönderilmeden taslak depolama doğrulanır", async () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {});
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  const form = await screen.findByRole("form", { name: "Servis durağını kaydet" });
  fireEvent.change(within(form).getByLabelText("Durak adı"), { target: { value: "Unsaved draft" } });
  fireEvent.change(within(form).getByLabelText("Durak sırası"), { target: { value: "2" } });
  fireEvent.submit(form); await screen.findByRole("alert");
  expect(api.post).not.toHaveBeenCalled();
});

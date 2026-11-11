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
  fireEvent.change(screen.getByLabelText("Rota sürücüsü ara"), { target: { value: "Başka arama" } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.submit(form); await waitFor(() => expect(close).toHaveBeenCalledOnce());
  expect(vi.mocked(api.post).mock.calls[0]).toEqual(vi.mocked(api.post).mock.calls[1]);
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual(expect.objectContaining({ branch_id: "school-branch", route_name: "Kuzey", capacity: 40 }));
});

it("ilk sayfa dışındaki sürücüyü arar ve arama değişince seçimi koruyarak kaydeder", async () => {
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    const params = config?.params as Record<string, unknown> | undefined;
    return { data: { data: path === "/bus/options" ? {
    branches: [{ id: "school-branch", name: "Seçilen okul şubesi" }], students: [], today: "2026-11-10",
    more_drivers: !params?.driver_search,
    drivers: params?.driver_search === "Zeynep" || params?.driver_id === "later-driver"
      ? [{ id: "later-driver", name: "Zeynep Taşcı" }] : [],
  } : [] } };
  });
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "route" } } });
  render(<BusRouteManager routeId={null} canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  await screen.findByText("Diğer sürücüler için ad veya soyadla arayın.");
  fireEvent.change(screen.getByLabelText("Rota şubesi"), { target: { value: "school-branch" } });
  fireEvent.change(screen.getByLabelText("Rota sürücüsü ara"), { target: { value: "Zeynep" } });
  await screen.findByRole("option", { name: "Zeynep Taşcı" });
  await waitFor(() => expect(screen.getByLabelText("Rota sürücüsü")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Rota sürücüsü"), { target: { value: "later-driver" } });
  fireEvent.change(screen.getByLabelText("Rota sürücüsü ara"), { target: { value: "Diğer" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/bus/options", expect.objectContaining({
    params: expect.objectContaining({ driver_search: "Diğer", driver_id: "later-driver", branch_id: "school-branch" }),
  })));
  expect(screen.getByLabelText("Rota sürücüsü")).toHaveValue("later-driver");
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Rota adı"), { target: { value: "Kuzey" } });
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/bus/routes", expect.objectContaining({ driver_id: "later-driver" })));
});

it("yalnız okuma rolü rota veya durak yazma formu alamaz", async () => {
  render(<BusRouteManager routeId="route" canWrite={false} onClose={vi.fn()} onRefresh={vi.fn()} />);
  await screen.findByRole("heading", { name: "Duraklar" });
  expect(screen.queryByRole("form")).not.toBeInTheDocument(); expect(api.post).not.toHaveBeenCalled(); expect(api.put).not.toHaveBeenCalled();
});

const existingRoute = { id: "route", branch_id: "school-branch", route_name: "Kuzey", route_number: "K1",
  vehicle_plate: "34 SCS 360", driver_id: null, capacity: 40, status: "ACTIVE", description: "",
  updated_at: "2026-11-10T20:00:00+00:00" };
const routeOptions = { branches: [{ id: "school-branch", name: "Seçilen okul şubesi" }], drivers: [], students: [], today: "2026-11-10" };
const existingStop = { id: "stop", route_id: "route", stop_name: "Old stop", stop_order: 1,
  latitude: 0, longitude: 1.12345678, estimated_arrival: "08:30:45.123456", version: "a".repeat(64) };

it("durak yanıtı kaybolunca aynı sürümle tekrarlar ve dokunulmayan tam saat bilgisini korur", async () => {
  let stopReads = 0;
  const updated = { ...existingStop, stop_name: "First edit", version: "b".repeat(64) };
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/bus/routes/route" ? existingRoute
    : path === "/bus/options" ? routeOptions : path === "/bus/stops" ? [++stopReads === 1 ? existingStop : updated] : [] } }));
  vi.mocked(api.put).mockRejectedValueOnce(new Error("lost response")).mockResolvedValue({ data: { data: { id: "stop", version: updated.version } } });
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Durağı düzenle" }));
  expect(screen.getByLabelText("Tahmini varış saati")).toHaveValue("08:30:45.123");
  fireEvent.change(screen.getByLabelText("Durak adı"), { target: { value: "First edit" } });
  fireEvent.submit(screen.getByRole("form", { name: "Servis durağını kaydet" }));
  await screen.findByRole("alert");
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis durağını kaydet" })).toBeEnabled());
  fireEvent.submit(screen.getByRole("form", { name: "Servis durağını kaydet" }));
  await screen.findByText("Durak kaydedildi");
  expect(vi.mocked(api.put).mock.calls[0]).toEqual(vi.mocked(api.put).mock.calls[1]);
  expect(vi.mocked(api.put).mock.calls[0][1]).toEqual(expect.objectContaining({ expected_version: existingStop.version,
    estimated_arrival: "08:30:45.123456", latitude: 0, longitude: 1.12345678 }));
});

it("aynı durak yeni sürümle yeniden seçilirse formu da yeni kayıttan doldurur", async () => {
  let stopReads = 0;
  const updated = { ...existingStop, stop_name: "Other operator edit", version: "b".repeat(64) };
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/bus/routes/route" ? existingRoute
    : path === "/bus/options" ? routeOptions : path === "/bus/stops" ? [++stopReads === 1 ? existingStop : updated] : [] } }));
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Durağı düzenle" }));
  fireEvent.change(screen.getByLabelText("Durak adı"), { target: { value: "Local draft" } });
  fireEvent.click(screen.getByRole("button", { name: "Rota verilerini yenile" }));
  await screen.findByRole("cell", { name: "Other operator edit" });
  fireEvent.click(screen.getByRole("button", { name: "Durağı düzenle" }));
  expect(screen.getByLabelText("Durak adı")).toHaveValue("Other operator edit");
});

it("mevcut şube listede bulunmasa da korunur; sürümsüz eski durak yanıtıyla yazmaz", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/bus/routes/route" ? { ...existingRoute, branch_name: "Mevcut uzak şube" }
    : path === "/bus/options" ? { ...routeOptions, branches: [] } : path === "/bus/stops" ? [{ ...existingStop, version: undefined }] : [] } }));
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  await screen.findByRole("option", { name: "Mevcut uzak şube" });
  expect(screen.getByLabelText("Rota şubesi")).toHaveValue("school-branch");
  fireEvent.click(await screen.findByRole("button", { name: "Durağı düzenle" }));
  await screen.findByText("Durağın güncel sürümü alınamadı. Durak listesini yenileyip yeniden seçin.");
  expect(screen.getByRole("button", { name: "Servis durağını kaydet" })).toBeDisabled();
  fireEvent.submit(screen.getByRole("form", { name: "Servis durağını kaydet" }));
  expect(api.put).not.toHaveBeenCalled();
});

it("yanıtı kaybolan rota güncellemesini aynı kimlik ve sürümle tekrarlar, yeni sürüm yüklenene kadar yazmaz", async () => {
  const latest = { ...existingRoute, route_name: "Yeni rota", updated_at: "2026-11-10T20:01:00+00:00" };
  let deliver: (value: { data: { data: typeof existingRoute } }) => void = () => { throw new Error("Response not scheduled"); };
  const pending = new Promise<{ data: { data: typeof existingRoute } }>((resolve) => { deliver = resolve; });
  let routeReads = 0;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/bus/routes/route") return ++routeReads === 1 ? { data: { data: existingRoute } } : routeReads === 2 ? pending : { data: { data: latest } };
    return { data: { data: path === "/bus/options" ? routeOptions : [] } };
  });
  vi.mocked(api.put).mockRejectedValueOnce(new Error("lost response")).mockResolvedValue({ data: { data: { id: "route", updated_at: latest.updated_at } } });
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  const button = await screen.findByRole("button", { name: "Servis rotasını kaydet" });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Rota adı"), { target: { value: "Yeni rota" } });
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await screen.findByRole("alert");
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await waitFor(() => expect(routeReads).toBe(2));
  expect(vi.mocked(api.put).mock.calls[0]).toEqual(vi.mocked(api.put).mock.calls[1]);
  expect(vi.mocked(api.put).mock.calls[0][1]).toEqual(expect.objectContaining({ expected_updated_at: existingRoute.updated_at }));
  expect(button).toBeDisabled();
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  expect(api.put).toHaveBeenCalledTimes(2);
  deliver({ data: { data: latest } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Rota adı"), { target: { value: "Son rota" } });
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(3));
  expect(vi.mocked(api.put).mock.calls[2][1]).toEqual(expect.objectContaining({ expected_updated_at: latest.updated_at }));
});

it("güncelleme sonrası rota okunamazsa eski sürümle yeni kayıt göndermez", async () => {
  let routeReads = 0;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/bus/routes/route") {
      if (++routeReads > 1) throw new Error("refresh unavailable");
      return { data: { data: existingRoute } };
    }
    return { data: { data: path === "/bus/options" ? routeOptions : [] } };
  });
  vi.mocked(api.put).mockResolvedValue({ data: { data: { id: "route", updated_at: "2026-11-10T20:01:00+00:00" } } });
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await screen.findByText("Rota bilgileri yüklenemedi. Kaydetmeden önce rota verilerini yenileyin.");
  expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeDisabled();
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  expect(api.put).toHaveBeenCalledOnce();
});

it("yanıtı belirsiz kayıttan sonra güncel sürüm elle yüklenirse yeni işlem kimliği kullanır", async () => {
  let reads = 0;
  const latest = { ...existingRoute, route_name: "Yeni rota", updated_at: "2026-11-10T20:01:00+00:00" };
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/bus/routes/route"
    ? (++reads === 1 ? existingRoute : latest) : path === "/bus/options" ? routeOptions : [] } }));
  vi.mocked(api.put).mockRejectedValueOnce(new Error("lost response")).mockResolvedValue({ data: { data: { id: "route", updated_at: latest.updated_at } } });
  render(<BusRouteManager routeId="route" canWrite onClose={vi.fn()} onRefresh={vi.fn()} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Rota adı"), { target: { value: "Yeni rota" } });
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await screen.findByRole("alert");
  await waitFor(() => expect(screen.getByRole("button", { name: "Rota verilerini yenile" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Rota verilerini yenile" }));
  await waitFor(() => expect(screen.getByLabelText("Rota adı")).toHaveValue("Yeni rota"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Servis rotasını kaydet" })).toBeEnabled());
  fireEvent.submit(screen.getByRole("form", { name: "Servis rotasını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
  const original = vi.mocked(api.put).mock.calls[0][1] as { request_id: string };
  const next = vi.mocked(api.put).mock.calls[1][1] as { request_id: string; expected_updated_at: string };
  expect(next.request_id).not.toBe(original.request_id);
  expect(next.expected_updated_at).toBe(latest.updated_at);
});

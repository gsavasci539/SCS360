import axios, { AxiosError, type AxiosAdapter, type AxiosResponse } from "axios";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { useAuthStore, hasPermission } from "../stores/auth";
import type { AuthUser } from "../types/api";
import { usePlatformWorkspace } from "../stores/platformWorkspace";

const user: AuthUser = { id: "user", first_name: "Test", last_name: "User", email: "test@example.com", is_super_admin: false,
  organization_id: "org", roles: [{ id: "role", name: "Kantin", slug: "canteen_staff" }], permissions: ["canteen.read", "canteen.write"], branch_ids: ["branch"] };
afterEach(() => { useAuthStore.getState().clearSession(); vi.restoreAllMocks(); });

it("eşzamanlı 401 yanıtında bir kez yeniler ve kaldırılan yetkiyi arayüzden çıkarır", async () => {
  useAuthStore.getState().setSession({ access_token: "old", refresh_token: "refresh-old", token_type: "bearer", user }, true);
  const refreshedUser = { ...user, permissions: ["canteen.read"] };
  const refresh = vi.spyOn(axios, "post").mockResolvedValue({ data: { data: { access_token: "new", refresh_token: "refresh-new", user: refreshedUser } } });
  const adapter: AxiosAdapter = async (config) => {
    const response: AxiosResponse = { status: 200, statusText: "OK", config, headers: {}, data: { success: true } };
    if (config.headers.Authorization !== "Bearer new") {
      response.status = 401;
      throw new AxiosError("Expired", "ERR_BAD_REQUEST", config, undefined, response);
    }
    return response;
  };
  const results = await Promise.all([api.get("/private/first", { adapter }), api.get("/private/second", { adapter })]);
  expect(results.every((response) => response.status === 200)).toBe(true);
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(useAuthStore.getState().can("canteen.read")).toBe(true);
  expect(useAuthStore.getState().can("canteen.write")).toBe(false);
  expect(JSON.parse(localStorage.getItem("scs360-session")!).user.permissions).toEqual(["canteen.read"]);
});

it("rol adı tek başına yazma yetkisi vermez", () => {
  expect(hasPermission({ ...user, permissions: [] }, "canteen.write")).toBe(false);
  expect(hasPermission(user, "canteen.write")).toBe(true);
});

it("401 yenilemesi sırasında kurum değişse bile başlayan istek ilk kurumda kalır", async () => {
  const root = { ...user, is_super_admin: true };
  useAuthStore.getState().setSession({ access_token: "old", refresh_token: "refresh", token_type: "bearer", user: root });
  usePlatformWorkspace.getState().select({ id: "school-a", name: "A", operatorId: root.id });
  vi.spyOn(axios, "post").mockImplementation(async () => {
    usePlatformWorkspace.getState().select({ id: "school-b", name: "B", operatorId: root.id });
    return { data: { data: { access_token: "new", refresh_token: "next", user: root } } };
  });
  const schools: unknown[] = [];
  const adapter: AxiosAdapter = async (config) => {
    schools.push(config.headers.get("X-SCS360-Organization-Id"));
    const response: AxiosResponse = { status: 200, statusText: "OK", config, headers: {}, data: {} };
    if (config.headers.Authorization !== "Bearer new") { response.status = 401; throw new AxiosError("Expired", "ERR_BAD_REQUEST", config, undefined, response); }
    return response;
  };
  await api.get("/students", { adapter }); await api.get("/students", { adapter });
  expect(schools).toEqual(["school-a", "school-a", "school-b"]);
  const control: unknown[] = []; await api.get("/platform/plans", { adapter: async (config) => { control.push(config.headers.get("X-SCS360-Organization-Id")); return { config, status: 200, statusText: "OK", headers: {}, data: {} }; } });
  expect(control).toEqual([undefined]);
});

it("eski token ile gelen üyelik engelini oturuma yansıtır ve token yenilemeye çalışmaz", async () => {
  useAuthStore.getState().setSession({ access_token: "old", refresh_token: "refresh-old", token_type: "bearer", user });
  const refresh = vi.spyOn(axios, "post");
  const access = { status: "PAST_DUE", restricted: true, billing_path: "/subscription", warning: "Üyelik ödemesi bekleniyor", period_end: null, grace_end: null, days_remaining: 0 };
  const adapter: AxiosAdapter = async (config) => {
    throw new AxiosError("Subscription required", "ERR_BAD_REQUEST", config, undefined, {
      config, status: 402, statusText: "Payment Required", headers: {}, data: { errors: [{ code: "SUBSCRIPTION_REQUIRED", access }] },
    });
  };
  await expect(api.get("/users", { adapter })).rejects.toBeInstanceOf(AxiosError);
  expect(useAuthStore.getState().user?.organization_access).toEqual(access);
  expect(useAuthStore.getState().accessToken).toBe("old");
  expect(refresh).not.toHaveBeenCalled();
});

it("geç dönen yenileme yeni giriş yapılan hesabı ezmez veya tekrar istek göndermez", async () => {
  useAuthStore.getState().setSession({ access_token: "old", refresh_token: "refresh-old", token_type: "bearer", user });
  let finish!: (value: unknown) => void;
  const refresh = vi.spyOn(axios, "post").mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  const adapter = vi.fn<AxiosAdapter>(async (config) => { throw new AxiosError("Expired", "ERR_BAD_REQUEST", config, undefined, { config, status: 401, statusText: "Unauthorized", headers: {}, data: {} }); });
  const pending = api.get("/students", { adapter }).catch((reason) => reason);
  await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  const next = { ...user, id: "next-user" };
  useAuthStore.getState().clearSession(); useAuthStore.getState().setSession({ access_token: "next", refresh_token: "next-refresh", token_type: "bearer", user: next });
  finish({ data: { data: { access_token: "old-refreshed", refresh_token: "old-rotated", user } } });
  expect(axios.isCancel(await pending)).toBe(true); expect(adapter).toHaveBeenCalledOnce();
  expect(useAuthStore.getState().user?.id).toBe("next-user"); expect(useAuthStore.getState().accessToken).toBe("next");
});

it("Root yetkisi yenilemede kaldırılırsa kapsam başlığını silerek global sorguya geçmez", async () => {
  useAuthStore.getState().setSession({ access_token: "old", refresh_token: "refresh", token_type: "bearer", user: { ...user, is_super_admin: true } });
  usePlatformWorkspace.getState().select({ id: "school-a", name: "A", operatorId: user.id });
  vi.spyOn(axios, "post").mockResolvedValue({ data: { data: { access_token: "new", refresh_token: "next", user } } });
  const adapter = vi.fn<AxiosAdapter>(async (config) => { throw new AxiosError("Expired", "ERR_BAD_REQUEST", config, undefined, { config, status: 401, statusText: "Unauthorized", headers: {}, data: {} }); });
  const reason = await api.get("/students", { adapter }).catch((error) => error);
  expect(axios.isCancel(reason)).toBe(true); expect(adapter).toHaveBeenCalledOnce();
  expect(useAuthStore.getState().accessToken).toBe("new"); expect(useAuthStore.getState().user?.is_super_admin).toBe(false);
});

it("önceki oturumun geç yanıtı ve üyelik engeli yeni hesaba uygulanmaz", async () => {
  useAuthStore.getState().setSession({ access_token: "old", refresh_token: "refresh", token_type: "bearer", user });
  let fail!: (reason: unknown) => void;
  const adapter: AxiosAdapter = (config) => new Promise((_resolve, reject) => { fail = () => reject(new AxiosError("Old subscription", "ERR_BAD_REQUEST", config, undefined, { config, status: 402, statusText: "Payment Required", headers: {}, data: { errors: [{ code: "SUBSCRIPTION_REQUIRED", access: { status: "PAST_DUE", restricted: true, billing_path: "/subscription", period_end: null, grace_end: null, days_remaining: 0, warning: "Old" } }] } })); });
  const pending = api.get("/students", { adapter }).catch((reason) => reason);
  await vi.waitFor(() => expect(fail).toBeDefined());
  useAuthStore.getState().setSession({ access_token: "next", refresh_token: "next-refresh", token_type: "bearer", user: { ...user, id: "next-user" } });
  fail(new Error()); expect(axios.isCancel(await pending)).toBe(true);
  expect(useAuthStore.getState().user?.organization_access).toBeUndefined();
});

import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { AxiosRequestConfig } from "axios";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ExcuseReviewPanel } from "../features/communications/ExcuseRequests";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() }, apiMessage: () => "İşlem başarısız" }));
const actor: AuthUser = { id: "operator", first_name: "Test", last_name: "Operator", email: "operator@example.invalid",
  organization_id: "institution", is_super_admin: false, roles: [], permissions: ["students.write", "branch.read", "dashboard.view"], branch_ids: [] };
const row = { id: "excuse", student_id: "student", student_name: "İlk şubenin öğrencisi", status: "PENDING",
  start_date: "2026-11-20", end_date: "2026-11-21", description: "İzole talep" };
const branch = (config?: AxiosRequestConfig) => (config?.params as { branch_id?: string } | undefined)?.branch_id;
const actions = (id: string, items: typeof row[]) => ({ data: { data: { branch_id: id, excuse_requests: { count: items.length, items } } } });

beforeEach(() => {
  useAuthStore.setState({ user: actor });
  vi.mocked(api.get).mockImplementation(async (path, config) => path === "/branches" ? {
    data: { data: [{ id: "first", name: "İlk şube" }, { id: "second", name: "İkinci şube" }] },
  } : actions(branch(config) ?? "first", [row]));
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

it("şube değişiminde eski satırı gizler ve farklı şube yanıtını reddeder", async () => {
  const get = vi.mocked(api.get).getMockImplementation()!;
  let respond = () => {};
  vi.mocked(api.get).mockImplementation((path, config) => {
    if (path !== "/dashboard/pending-actions" || branch(config) !== "second") return get(path, config);
    return new Promise((resolve) => { respond = () => resolve(actions("first", [row])); });
  });
  render(<ExcuseReviewPanel />);
  await screen.findByText(row.student_name);
  fireEvent.change(screen.getByRole("combobox", { name: "Mazeret şubesi" }), { target: { value: "second" } });
  expect(screen.queryByText(row.student_name)).not.toBeInTheDocument();
  expect(screen.getByText("Mazeret talepleri yükleniyor")).toBeInTheDocument();
  await act(async () => respond());
  expect(screen.getByText("Bekleyen mazeretler seçili şubeyle eşleşmiyor.")).toBeInTheDocument();
});

it("uyuşmayan kararda notu korur, kayıt doğrulanınca listeyi yeniden okur", async () => {
  const get = vi.mocked(api.get).getMockImplementation()!;
  const note = "İzole karar notu";
  const saved = { ...row, status: "APPROVED", reviewed_by: actor.id, review_comment: note };
  let approved = false;
  vi.mocked(api.put).mockResolvedValueOnce({ data: { data: { ...saved, student_id: "other" } } })
    .mockImplementationOnce(async () => { approved = true; return { data: { data: saved } }; });
  vi.mocked(api.get).mockImplementation((path, config) => path === "/dashboard/pending-actions" && approved ?
    Promise.resolve(actions("first", [])) : get(path, config));
  render(<ExcuseReviewPanel />);
  const form = await screen.findByRole("form", { name: `Mazeret kararı ${row.student_name}` });
  const submit = within(form).getByRole("button", { name: "Onayla" });
  fireEvent.change(within(form).getByLabelText("Değerlendirme notu"), { target: { value: note } });
  fireEvent.click(submit);
  expect(await screen.findByRole("alert")).toHaveTextContent("Sunucu yanıtı seçili mazeret");
  expect(within(form).getByLabelText("Değerlendirme notu")).toHaveValue(note);
  expect(screen.queryByText("Mazeret kararı kaydedildi.")).not.toBeInTheDocument();
  fireEvent.click(submit);
  await waitFor(() => expect(api.put).toHaveBeenLastCalledWith("/dashboard/excuse-requests/excuse",
    { status: "APPROVED", comment: note }, expect.objectContaining({ signal: expect.any(AbortSignal) })));
  expect(await screen.findByText("Mazeret kararı kaydedildi.")).toBeInTheDocument();
  expect(await screen.findByText("Bekleyen mazeret talebi bulunmuyor.")).toBeInTheDocument();
});

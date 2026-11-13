import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AttendancePage } from "../features/attendance/AttendancePage";
import { api } from "../lib/api";

const state = vi.hoisted(() => ({ canWrite: true, toast: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() }, apiMessage: () => "Yoklama kaydı alınamadı" }));
vi.mock("../lib/analysis", () => ({ canAnalyze: () => false, getAnalysis: vi.fn() }));
vi.mock("../stores/auth", () => ({ useAuthStore: (select: (value: { can: () => boolean }) => unknown) => select({ can: () => state.canWrite }) }));
vi.mock("../components/Toast", () => ({ useToast: () => ({ showToast: state.toast }) }));

const pupil = { id: "student", first_name: "Ayşe", last_name: "Örnek" };
const history = { id: "record", student_id: pupil.id, first_name: pupil.first_name, last_name: pupil.last_name,
  status: "ABSENT", notes: "Eski not korunmalı", version: "a".repeat(64) };
beforeEach(() => {
  state.canWrite = true;
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/classes"
    ? [{ id: "class", name: "Sınıf A" }] : path === "/students" ? [pupil] : [history] } }));
  vi.mocked(api.put).mockResolvedValue({ data: { data: { created: 0, updated: 1, unchanged: 0 } } });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("sınıf listesi hatasını tekrar okuyup düzenleme formunu açar", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("classes unavailable"));
  render(<AttendancePage />);
  fireEvent.click(await screen.findByRole("button", { name: /Tekrar dene/i }));
  expect(await screen.findByDisplayValue("Eski not korunmalı")).toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.filter(([path]) => path === "/classes")).toHaveLength(2);
});

it("mevcut durum/not/sürümü yükler ve gerçek güncelleme sayısıyla kaydeder", async () => {
  render(<AttendancePage />);
  const note = await screen.findByDisplayValue("Eski not korunmalı");
  expect(screen.getByRole("button", { name: "Gelmedi" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.change(note, { target: { value: "Düzenlenen not" } });
  fireEvent.click(screen.getByRole("button", { name: "Geç geldi" }));
  fireEvent.click(screen.getByRole("button", { name: "Yoklamayı kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/attendance/bulk", expect.objectContaining({
    class_id: "class", records: [{ student_id: "student", status: "LATE", notes: "Düzenlenen not", expected_version: history.version }],
    request_id: expect.any(String),
  })));
  expect(api.post).not.toHaveBeenCalled();
  await waitFor(() => expect(state.toast).toHaveBeenCalledWith("Yoklama kaydedildi", "0 yeni, 1 güncellenen, 0 değişmeyen kayıt."));
});

it("mevcut kaydı olmayan öğrenciyi geldi varsaymaz ve yalnız seçilen durumları gönderir", async () => {
  const second = { id: "student-2", first_name: "Mehmet", last_name: "Örnek" };
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/classes"
    ? [{ id: "class", name: "Sınıf A" }] : path === "/students" ? [pupil, second] : [] } }));
  render(<AttendancePage />);
  await screen.findByLabelText("Ayşe Örnek için yoklama notu");
  expect(screen.getAllByRole("button", { name: "Geldi" }).every((button) => button.getAttribute("aria-pressed") === "false")).toBe(true);
  expect(screen.getByRole("button", { name: "Yoklamayı kaydet" })).toBeDisabled();
  expect(screen.getByLabelText("Mehmet Örnek için yoklama notu")).toBeDisabled();
  fireEvent.click(screen.getAllByRole("button", { name: "Gelmedi" })[0]);
  fireEvent.click(screen.getByRole("button", { name: "Yoklamayı kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/attendance/bulk", expect.objectContaining({
    records: [{ student_id: "student", status: "ABSENT", notes: null, expected_version: null }],
  })));
});

it("tarih değişirken kaydı engeller ve geç gelen eski yanıtı forma taşımaz", async () => {
  let release: (value: unknown) => void = () => {};
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    const params = config?.params as { attendance_date?: string } | undefined;
    if (path === "/attendance" && params?.attendance_date === "2026-11-09") return await new Promise((resolve) => { release = resolve; });
    return { data: { data: path === "/classes" ? [{ id: "class", name: "Sınıf" }] : path === "/students" ? [pupil]
      : [{ ...history, notes: params?.attendance_date === "2026-11-08" ? "Son seçili gün" : history.notes }] } };
  });
  render(<AttendancePage />);
  await screen.findByDisplayValue(history.notes);
  fireEvent.change(screen.getByLabelText("Yoklama tarihi"), { target: { value: "2026-11-09" } });
  expect(screen.getByRole("button", { name: "Yoklamayı kaydet" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Yoklama tarihi"), { target: { value: "2026-11-08" } });
  await screen.findByDisplayValue("Son seçili gün");
  release({ data: { data: [{ ...history, notes: "Eski geç yanıt" }] } });
  await waitFor(() => expect(screen.getByLabelText("Ayşe Örnek için yoklama notu")).toHaveValue("Son seçili gün"));
});

it("başlangıç okuması başarısızsa kayıt açılmaz, yeniden okuma ile açılır", async () => {
  let failed = true;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/attendance" && failed) throw new Error("503");
    return { data: { data: path === "/classes" ? [{ id: "class", name: "Sınıf" }] : path === "/students" ? [pupil] : [history] } };
  });
  render(<AttendancePage />);
  await screen.findByText("Yoklama kaydı alınamadı");
  expect(screen.getByRole("button", { name: "Yoklamayı kaydet" })).toBeDisabled();
  failed = false;
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  await screen.findByDisplayValue(history.notes);
  expect(screen.getByRole("button", { name: "Yoklamayı kaydet" })).toBeEnabled();
});

it("yanıt kaybolursa aynı istek kimliği ve gövdeyle tekrarlar", async () => {
  vi.mocked(api.put).mockRejectedValueOnce(new Error("timeout"));
  render(<AttendancePage />);
  await screen.findByDisplayValue(history.notes);
  fireEvent.click(screen.getByRole("button", { name: "Yoklamayı kaydet" }));
  const retry = await screen.findByRole("button", { name: "Kaydı tekrar dene" });
  expect(screen.getByLabelText("Yoklama tarihi")).toBeDisabled();
  expect(screen.getByLabelText("Ayşe Örnek için yoklama notu")).toBeDisabled();
  fireEvent.click(retry);
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.put).mock.calls[0]).toEqual(vi.mocked(api.put).mock.calls[1]);
});

it("salt okunur kullanıcı kaydı görür, düzenleyemez", async () => {
  state.canWrite = false;
  render(<AttendancePage />);
  expect(await screen.findByDisplayValue(history.notes)).toBeDisabled();
  expect(screen.queryByRole("button", { name: "Yoklamayı kaydet" })).not.toBeInTheDocument();
});

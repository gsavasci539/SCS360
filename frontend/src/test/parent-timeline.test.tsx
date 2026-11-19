import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ParentDayTimeline } from "../features/parent/ParentDayTimeline";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Akış yüklenemedi" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("gerçek etkinlik saatini ve detay bağlantısını gösterir, tarihi değişince doğru günü ister", async () => {
  vi.mocked(api.get).mockImplementation(async (_path, config) => ({ data: { data: { student_id: "child-1",
    date: (config?.params as { date: string }).date, events: [{ id: "attendance-1", type: "ATTENDANCE",
      title: "Yoklama kaydı", status: "PRESENT", time: "08:30", details: {}, detail_url: "/parent/attendance" }] } } }));
  render(<MemoryRouter><ParentDayTimeline studentId="child-1" initialDate="2026-11-03" /></MemoryRouter>);
  expect(await screen.findByText("08:30 · Yoklama kaydı")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "İlgili sayfayı aç" })).toHaveAttribute("href", "/parent/attendance");
  fireEvent.change(screen.getByLabelText("Akış tarihi"), { target: { value: "2026-11-02" } });
  await waitFor(() => expect(api.get).toHaveBeenLastCalledWith("/parent/child/child-1/timeline",
    expect.objectContaining({ params: { date: "2026-11-02" } })));
});

it("saati olmayan kayda saat uydurmaz ve eski çocuğun gecikmiş yanıtını göstermez", async () => {
  let complete!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise((resolve) => { complete = resolve; }))
    .mockResolvedValueOnce({ data: { data: { student_id: "child-2", date: "2026-11-03", events: [
      { id: "new-child", type: "DAILY_REPORT", title: "Yeni çocuğun karnesi", status: "RECORDED", time: null,
        details: { activities: ["Kitap okuma", "Çizim"], sleep_status: "30 dk" }, detail_url: "/parent/reports" },
    ] } } });
  const view = render(<MemoryRouter><ParentDayTimeline studentId="child-1" initialDate="2026-11-03" /></MemoryRouter>);
  view.rerender(<MemoryRouter><ParentDayTimeline studentId="child-2" initialDate="2026-11-03" /></MemoryRouter>);
  await screen.findByText("Saat belirtilmedi · Yeni çocuğun karnesi");
  expect(screen.getByText("Etkinlikler · Kitap okuma, Çizim")).toBeInTheDocument();
  expect(screen.getByText("Uyku · 30 dk")).toBeInTheDocument();
  await act(async () => { complete({ data: { data: { student_id: "child-1", date: "2026-11-03", events: [
    { id: "old-child", title: "Eski çocuğun kaydı", status: "PRESENT", time: "08:00", details: {}, detail_url: "/parent/attendance" },
  ] } } }); });
  await waitFor(() => expect(screen.queryByText(/Eski çocuğun kaydı/)).not.toBeInTheDocument());
});

it("hata sonrası yeniden denemede gerçek boş durumu gösterir", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ data: { data: { student_id: "child-1", date: "2026-11-03", events: [] } } });
  render(<MemoryRouter><ParentDayTimeline studentId="child-1" initialDate="2026-11-03" /></MemoryRouter>);
  await screen.findByText("Akış yüklenemedi");
  fireEvent.click(screen.getByRole("button", { name: /tekrar dene/i }));
  expect(await screen.findByText("Bu gün için kayıtlı etkinlik yok.")).toBeInTheDocument();
});

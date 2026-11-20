import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
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
  fireEvent.click(screen.getByRole("button", { name: "Karne ayrıntısını aç" }));
  expect(screen.getByText("Etkinlikler · Kitap okuma, Çizim")).toBeInTheDocument();
  expect(screen.getByText("Uyku · 30 dk")).toBeInTheDocument();
  await act(async () => { complete({ data: { data: { student_id: "child-1", date: "2026-11-03", events: [
    { id: "old-child", title: "Eski çocuğun kaydı", status: "PRESENT", time: "08:00", details: {}, detail_url: "/parent/attendance" },
  ] } } }); });
  await waitFor(() => expect(screen.queryByText(/Eski çocuğun kaydı/)).not.toBeInTheDocument());
});

it("karne ayrıntısı seçili çocuğu, tarihi ve konumu korur", async () => {
  vi.mocked(api.get).mockImplementation(async (_path, config) => {
    const date = (config?.params as { date: string }).date;
    return { data: { data: { student_id: "child-2", date, events: [
      { id: "stored-report", type: "DAILY_REPORT", title: "Öğretmen günlük raporu", status: "RECORDED", time: null,
        details: { teacher_notes: `Gözlem ${date}` }, detail_url: "/parent/reports" },
    ] } } };
  });
  function CurrentLocation() { return <output aria-label="Konum">{useLocation().pathname}</output>; }
  render(<MemoryRouter initialEntries={["/parent/children"]}><CurrentLocation />
    <ParentDayTimeline studentId="child-2" initialDate="2026-11-03" />
  </MemoryRouter>);

  const open = await screen.findByRole("button", { name: "Karne ayrıntısını aç" });
  expect(open).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("link", { name: "İlgili sayfayı aç" })).not.toBeInTheDocument();
  fireEvent.click(open);
  expect(screen.getByText("Öğretmen notu · Gözlem 2026-11-03")).toBeVisible();
  expect(screen.getByLabelText("Konum")).toHaveTextContent("/parent/children");
  expect(screen.getByLabelText("Akış tarihi")).toHaveValue("2026-11-03");
  expect(api.get).toHaveBeenCalledTimes(1);

  fireEvent.change(screen.getByLabelText("Akış tarihi"), { target: { value: "2026-11-02" } });
  const reopened = await screen.findByRole("button", { name: "Karne ayrıntısını aç" });
  expect(screen.queryByText("Öğretmen notu · Gözlem 2026-11-03")).not.toBeInTheDocument();
  expect(api.get).toHaveBeenLastCalledWith("/parent/child/child-2/timeline", expect.objectContaining({ params: { date: "2026-11-02" } }));
  fireEvent.click(reopened);
  expect(screen.getByText("Öğretmen notu · Gözlem 2026-11-02")).toBeVisible();
});

it("hata sonrası yeniden denemede gerçek boş durumu gösterir", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ data: { data: { student_id: "child-1", date: "2026-11-03", events: [] } } });
  render(<MemoryRouter><ParentDayTimeline studentId="child-1" initialDate="2026-11-03" /></MemoryRouter>);
  await screen.findByText("Akış yüklenemedi");
  fireEvent.click(screen.getByRole("button", { name: /tekrar dene/i }));
  expect(await screen.findByText("Bu gün için kayıtlı etkinlik yok.")).toBeInTheDocument();
});

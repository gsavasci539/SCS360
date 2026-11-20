import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ParentDayTimeline } from "../features/parent/ParentDayTimeline";
import { ParentPortalPage } from "../features/parent/ParentPortalPage";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Akış yüklenemedi" }));
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });

function parentWithAttendanceAccess() {
  useAuthStore.getState().setUser({ id: "parent", organization_id: "school", first_name: "Veli", last_name: "Test",
    email: "parent@test.invalid", roles: [], branch_ids: [], is_super_admin: false, permissions: ["parent.view_attendance"] });
}

const attendanceEvent = { id: "attendance-1", type: "ATTENDANCE", title: "Yoklama kaydı", status: "PRESENT",
  time: "08:30", details: {}, detail_url: "/parent/attendance" };

const children = [{ student_id: "child-1", first_name: "Deniz", last_name: "Test" },
  { student_id: "child-2", first_name: "Ada", last_name: "Test" }];

it("ilaç, revir, servis ve teslim kayıtlarını seçili günde kendi ayrıntılarıyla gösterir", async () => {
  const dateWithRecords = "2025-10-07";
  const events = [
    { id: "med-1", type: "MEDICATION", title: "İlaç takip kaydı", status: "GIVEN", time: "10:00",
      details: { medicine_name: "Kayıtlı ilaç", dosage: "5 mL", notes: "Yemekten sonra" }, detail_url: "/parent/health" },
    { id: "visit-1", type: "INFIRMARY", title: "Revir ziyareti", status: "LOW", time: "11:00",
      details: { complaint: "Baş ağrısı", treatment_given: "Dinlenme" }, detail_url: "/parent/health" },
    { id: "bus-1", type: "BUS_PICKUP", title: "Servise biniş", status: "PRESENT", time: "08:00",
      details: {}, detail_url: "/parent/children" },
    { id: "bus-2", type: "BUS_DROPOFF", title: "Servisten iniş", status: "PRESENT", time: "09:00",
      details: {}, detail_url: "/parent/children" },
    { id: "pickup-1", type: "PICKUP", title: "Okuldan teslim", status: "RECORDED", time: "17:00",
      details: { pickup_person_name: "Yetkili kişi" }, detail_url: "/parent/children" },
  ];
  vi.mocked(api.get).mockImplementation(async (_path, config) => {
    const { date } = config?.params as { date: string };
    return { data: { data: { student_id: "child-2", date, events: date === dateWithRecords ? events : [] } } };
  });
  render(<MemoryRouter><ParentDayTimeline studentId="child-2" initialDate={dateWithRecords} /></MemoryRouter>);
  expect(await screen.findByText("Uygulama · Dinlenme")).toBeInTheDocument();
  expect(screen.getByText("Şikâyet · Baş ağrısı")).toBeInTheDocument();
  expect(screen.getByText("İlaç · Kayıtlı ilaç")).toBeInTheDocument();
  expect(screen.getByText("Doz · 5 mL")).toBeInTheDocument();
  expect(screen.getByText("Not · Yemekten sonra")).toBeInTheDocument();
  expect(screen.getByText("08:00 · Servise biniş")).toBeInTheDocument();
  expect(screen.getByText("09:00 · Servisten iniş")).toBeInTheDocument();
  expect(screen.getByText("Teslim alan · Yetkili kişi")).toBeInTheDocument();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Akış tarihi"), { target: { value: "2025-10-08" } });
  expect(await screen.findByText("Bu gün için kayıtlı etkinlik yok.")).toBeInTheDocument();
  expect(screen.queryByText("Uygulama · Dinlenme")).not.toBeInTheDocument();
});

it("gerçek etkinlik saatini ve detay bağlantısını gösterir, tarihi değişince doğru günü ister", async () => {
  parentWithAttendanceAccess();
  vi.mocked(api.get).mockImplementation(async (_path, config) => ({ data: { data: { student_id: "child-1",
    date: (config?.params as { date: string }).date, events: [attendanceEvent] } } }));
  render(<MemoryRouter><ParentDayTimeline studentId="child-1" initialDate="2026-11-03" /></MemoryRouter>);
  expect(await screen.findByText("08:30 · Yoklama kaydı")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "İlgili sayfayı aç" })).toHaveAttribute("href", "/parent/attendance");
  fireEvent.change(screen.getByLabelText("Akış tarihi"), { target: { value: "2026-11-02" } });
  await waitFor(() => expect(api.get).toHaveBeenLastCalledWith("/parent/child/child-1/timeline",
    expect.objectContaining({ params: { date: "2026-11-02" } })));
});

it("yoklama bağlantısı doğrulanmış çocuğun kayıtlı gününü açar ve sonraki ay eski ayrıntıyı temizler", async () => {
  parentWithAttendanceAccess();
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path.endsWith("/timeline")) return { data: { data: { student_id: "child-2", date: "2025-10-07", events: [attendanceEvent] } } };
    if (path === "/parent/my-children") return { data: { data: children } };
    if (path === "/parent/child/child-2/attendance") {
      const month = (config?.params as { month: number }).month;
      return { data: { data: { student_id: "child-2", year: 2025, month,
        summary: { present: month === 10 ? 1 : 0, late: 0, absent: 0 }, calendar: month === 10 ? {
          "7": { date: "2025-10-07", status: "PRESENT", check_in_time: "08:45", check_out_time: null, note: "Kayıtlı yoklama notu" },
          "8": { date: "2025-10-08", status: null },
        } : {} } } };
    }
    return { data: { data: null } };
  });
  render(<MemoryRouter initialEntries={["/parent/children"]}><Routes>
    <Route path="/parent/children" element={<ParentDayTimeline studentId="child-2" initialDate="2025-10-07" />} />
    <Route path="/parent/attendance" element={<ParentPortalPage view="attendance" />} />
  </Routes></MemoryRouter>);
  fireEvent.click(await screen.findByRole("link", { name: "İlgili sayfayı aç" }));
  expect(await screen.findByText("Yoklama dönemi · 10/2025")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Öğrenci Seçin" })).toHaveValue("child-2");
  expect(await screen.findByText("Kayıtlı yoklama notu")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "2025-10-07 · Mevcut" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Giriş · 08:45")).toBeInTheDocument();
  expect(screen.queryByText(/Çıkış ·/)).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/parent/child/child-2/attendance", expect.objectContaining({
    params: { year: 2025, month: 10 },
  }));
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/parent/child/child-1/attendance")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "2025-10-08 · Kayıt yok" }));
  expect(screen.getByText("2025-10-08 · Kayıt yok")).toBeInTheDocument();
  expect(screen.queryByText("Kayıtlı yoklama notu")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sonraki ay" }));
  expect(await screen.findByRole("button", { name: "2025-11-01 · Kayıt yok" })).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/parent/child/child-2/attendance", expect.objectContaining({ params: { year: 2025, month: 11 } }));
  expect(screen.queryByRole("button", { name: "2025-10-07 · Mevcut" })).not.toBeInTheDocument();
});

it("yoklama izni yoksa akışta geçiş sunmaz ve takvim isteği yapmaz", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path.endsWith("/timeline")
    ? { student_id: "child-2", date: "2025-10-07", events: [attendanceEvent] }
    : path === "/parent/my-children" ? children : null } }));
  const { unmount } = render(<MemoryRouter><ParentDayTimeline studentId="child-2" initialDate="2025-10-07" /></MemoryRouter>);
  expect(await screen.findByText("08:30 · Yoklama kaydı")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "İlgili sayfayı aç" })).not.toBeInTheDocument();
  unmount();
  render(<MemoryRouter><ParentPortalPage view="attendance" /></MemoryRouter>);
  expect(await screen.findByText("Yoklama kayıtlarını görüntüleme yetkiniz yok.")).toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.endsWith("/attendance"))).toBe(false);
});

it("yoklama ile günlük akış arasında geri ve ileri giderken seçimi doğrular", async () => {
  parentWithAttendanceAccess();
  const today = "2026-11-20";
  const historicDay = "2025-10-07";
  let linkedChildren = children;
  vi.mocked(api.get).mockImplementation(async (path, config) => {
    if (path === "/parent/my-children") return { data: { data: linkedChildren } };
    const student_id = path.split("/")[3];
    if (path.endsWith("/today-status")) return { data: { data: { student_id, date: today } } };
    if (path.endsWith("/timeline")) {
      const { date } = config?.params as { date: string };
      return { data: { data: { student_id, date, events: date === historicDay ? [attendanceEvent] : [] } } };
    }
    if (path.endsWith("/attendance")) {
      const { year, month } = config?.params as { year: number; month: number };
      return { data: { data: { student_id, year, month, summary: { present: 0, late: 0, absent: 0 }, calendar: {} } } };
    }
    return { data: { data: null } };
  });

  function HistoryControls() {
    const navigate = useNavigate();
    return <><button onClick={() => navigate(-1)}>Geri</button><button onClick={() => navigate(1)}>İleri</button></>;
  }

  render(<MemoryRouter initialEntries={["/parent/children"]}>
    <HistoryControls />
    <Routes>
      <Route path="/parent/children" element={<ParentPortalPage view="children" />} />
      <Route path="/parent/attendance" element={<ParentPortalPage view="attendance" />} />
    </Routes>
  </MemoryRouter>);
  const childSelector = () => screen.getByRole("combobox", { name: "Öğrenci Seçin" });
  await screen.findByLabelText("Akış tarihi");
  fireEvent.change(childSelector(), { target: { value: "child-2" } });
  fireEvent.change(await screen.findByLabelText("Akış tarihi"), { target: { value: historicDay } });
  fireEvent.click(await screen.findByRole("link", { name: "İlgili sayfayı aç" }));
  expect(await screen.findByText("Yoklama dönemi · 10/2025")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Geri" }));
  expect(await screen.findByLabelText("Akış tarihi")).toHaveValue(historicDay);
  expect(childSelector()).toHaveValue("child-2");
  expect(await screen.findByText("08:30 · Yoklama kaydı")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "İleri" }));
  expect(await screen.findByText("Yoklama dönemi · 10/2025")).toBeInTheDocument();
  expect(childSelector()).toHaveValue("child-2");

  linkedChildren = [children[0]];
  vi.mocked(api.get).mockClear();
  fireEvent.click(screen.getByRole("button", { name: "Geri" }));
  expect(await screen.findByLabelText("Akış tarihi")).toHaveValue(today);
  expect(childSelector()).toHaveValue("child-1");
  expect(api.get).toHaveBeenCalledWith("/parent/child/child-1/timeline", expect.objectContaining({ params: { date: today } }));
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes("/child-2/"))).toBe(false);
});

it("bağlı olmayan çocukla gelen yoklama adresinden yetkisiz istek göndermez", async () => {
  parentWithAttendanceAccess();
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/parent/my-children" ? children : null } }));
  render(<MemoryRouter initialEntries={[{ pathname: "/parent/attendance", state: {
    parentAttendance: { studentId: "outside", date: "2025-10-07" },
  } }]}><ParentPortalPage view="attendance" /></MemoryRouter>);
  expect(await screen.findByRole("combobox", { name: "Öğrenci Seçin" })).toHaveValue("child-1");
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/parent/child/child-1/attendance", expect.anything()));
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes("/outside/"))).toBe(false);
  expect(screen.queryByText("Yoklama dönemi · 10/2025")).not.toBeInTheDocument();
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

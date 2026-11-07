import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { SurveysPage } from "../features/surveys/SurveysPage";
import { ParentSurveys, StaffSurveysPage } from "../features/parent/ParentSurveys";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }, apiMessage: () => "Yanıt kaydedilemedi" }));
const manager: AuthUser = { id: "manager", first_name: "Test", last_name: "User", email: "test@example.com", organization_id: "org", is_super_admin: false, roles: [], permissions: ["surveys.read", "surveys.write"], branch_ids: [] };
const questions = [{ id: "rating", question_text: "Okul puanı", question_type: "RATING", is_required: true }, { id: "choice", question_text: "Tekrar katılır mısınız?", question_type: "MULTIPLE_CHOICE", options: ["Evet", "Hayır"], is_required: true }];
const survey = { id: "survey", title: "Veli görüşü", status: "DRAFT", start_date: "2026-11-03", end_date: "2030-01-01", is_anonymous: true, questions };
beforeEach(() => {
  useAuthStore.setState({ user: manager });
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path === "/surveys/options" ? { organizations: [{ id: "org", name: "Okul" }] } : path === "/surveys/summary" ? { total_surveys: 300, total_responses: 4000 } : path === "/surveys/questions" ? questions : path.endsWith("/results") ? { question_results: [] } : path === "/surveys/surveys/survey" ? survey : path === "/surveys/responses" ? [] : [survey] } }));
  vi.mocked(api.post).mockResolvedValue({ data: { data: { id: "survey" } } });
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); vi.resetAllMocks(); });
const openManager = () => render(<MemoryRouter><ToastProvider><SurveysPage /></ToastProvider></MemoryRouter>);

it("salt okuma hesabı gerçek toplamı ve bağlantıyı görür, yazma seçeneklerini istemez", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["surveys.read"] } }); openManager();
  expect(await screen.findByText(/Toplam anket: 300/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Veli görüşü" })).toHaveAttribute("href", "/surveys?survey=survey");
  expect(screen.queryByRole("button", { name: "Anket taslağını oluştur" })).not.toBeInTheDocument();
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path === "/surveys/options")).toBe(false);
});

it("veli sorulara uygun sayısal ve seçenekli yanıtı gönderir", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["parent.respond_survey"] } });
  render(<ParentSurveys studentId="child" />);
  await screen.findByLabelText("Okul puanı");
  fireEvent.change(screen.getByLabelText("Okul puanı"), { target: { value: "5" } });
  fireEvent.change(screen.getByLabelText("Tekrar katılır mısınız?"), { target: { value: "Evet" } });
  fireEvent.click(screen.getByRole("button", { name: "Anketi yanıtla" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/parent/child/child/surveys/survey/respond", { response_data: { rating: 5, choice: "Evet" } }));
});

it("personel yanıt hakkıyla kendi yolunu kullanır ve başarısız gönderimde yanıtı korur", async () => {
  useAuthStore.setState({ user: { ...manager, permissions: ["surveys.respond"] } });
  vi.mocked(api.post).mockRejectedValue(new Error("failed"));
  render(<StaffSurveysPage />);
  await screen.findByLabelText("Okul puanı");
  fireEvent.change(screen.getByLabelText("Okul puanı"), { target: { value: "4" } });
  fireEvent.change(screen.getByLabelText("Tekrar katılır mısınız?"), { target: { value: "Hayır" } });
  fireEvent.click(screen.getByRole("button", { name: "Anketi yanıtla" }));
  expect(await screen.findByText("Yanıt kaydedilemedi")).toBeInTheDocument();
  expect(screen.getByLabelText("Okul puanı")).toHaveValue("4");
  expect(api.post).toHaveBeenCalledWith("/surveys/responses", { survey_id: "survey", response_data: { rating: 4, choice: "Hayır" } });
});

it("taslak oluşturunca ayrıntı adresine geçer ve gerçek soru ekler", async () => {
  openManager(); await screen.findByRole("option", { name: "Okul" });
  fireEvent.change(screen.getByLabelText("Anket başlığı"), { target: { value: "Yeni geri bildirim" } });
  fireEvent.change(screen.getByLabelText("Başlangıç tarihi"), { target: { value: "2026-11-03" } });
  fireEvent.change(screen.getByLabelText("Bitiş tarihi"), { target: { value: "2030-01-01" } });
  fireEvent.click(screen.getByRole("button", { name: "Anket taslağını oluştur" }));
  await screen.findByRole("region", { name: "Anket ayrıntısı" });
  fireEvent.change(screen.getByLabelText("Soru metni"), { target: { value: "Yeni soru" } });
  fireEvent.click(screen.getByRole("button", { name: "Soruyu ekle" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/surveys/questions", expect.objectContaining({ survey_id: "survey", question_type: "RATING", question_text: "Yeni soru" })));
});

it("kurum seçenekleri gecikirse oluşturmayı hazır olana kadar kapalı tutar", async () => {
  let ready: (value: unknown) => void = () => {};
  const pending = new Promise((resolve) => { ready = resolve; });
  const base = vi.mocked(api.get).getMockImplementation()!;
  vi.mocked(api.get).mockImplementation((...args) => args[0] === "/surveys/options" ? pending as ReturnType<typeof api.get> : base(...args));
  openManager();
  await screen.findByText(/Toplam anket: 300/);
  expect(screen.getByRole("button", { name: "Anket taslağını oluştur" })).toBeDisabled();
  ready({ data: { data: { organizations: [{ id: "org", name: "Okul" }] } } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Anket taslağını oluştur" })).toBeEnabled());
});

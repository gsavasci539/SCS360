import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Chatbot } from "../components/Chatbot";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../types/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));

const first = { id: "student-1", student_id: "student-1", first_name: "Deniz", last_name: "Test" };
const second = { id: "student-2", student_id: "student-2", first_name: "Ece", last_name: "Test" };
const admin: AuthUser = { id: "admin", email: "admin@example.com", first_name: "Admin", last_name: "Test",
  is_super_admin: true, organization_id: "org", roles: [], permissions: [], branch_ids: [] };
const answer = (text: string, extra = {}) => ({ data: { data: { intent: "GENERAL", response_markdown: text, suggested_actions: [], ...extra } } });
const scroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
  useAuthStore.setState({ user: admin, accessToken: "test", refreshToken: "test", hydrated: true });
  vi.mocked(api.get).mockResolvedValue({ data: { data: { items: [first, second], total: 2 } } } as any);
  vi.mocked(api.post).mockResolvedValue(answer("Yanıt geldi.") as any);
});
afterEach(() => { cleanup(); useAuthStore.getState().clearSession(); });
afterAll(() => { if (scroll) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", scroll); else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView"); });

function open() {
  render(<MemoryRouter><Chatbot /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Chatbot'u aç" }));
}

describe("chatbot kullanıcı işlemleri", () => {
  it("hazır soruyu Türkçe karakterleriyle hemen gönderir ve sayfalı öğrenci listesini kullanır", async () => {
    open();
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Öğrenci seçin" })).toHaveValue(first.id));
    const suggestion = "🧠 LLM Chat Analitiği ve Konuşma Denetimi";
    fireEvent.click(screen.getByRole("button", { name: suggestion }));
    await screen.findByText("Yanıt geldi.");
    expect(api.post).toHaveBeenCalledWith("/v1/chatbot/process-query", expect.objectContaining({ query: suggestion, student_id: first.id, role: "SUPER_ADMIN" }));
    expect(screen.getByRole("option", { name: "Ece Test" })).toBeInTheDocument();
  });

  it("öğrenci seçildikten sonra silinen giriş alanı yerine asıl soruyu yeni öğrenciyle tekrar gönderir", async () => {
    let resolveStudents!: (value: any) => void;
    vi.mocked(api.get).mockImplementation(() => new Promise((resolve) => { resolveStudents = resolve; }));
    vi.mocked(api.post).mockResolvedValueOnce(answer("Lütfen öğrenci seçin.", { intent: "GRADES" }) as any)
      .mockResolvedValueOnce(answer("Ece için kayıt bulundu.", { intent: "GRADES" }) as any);
    open();
    fireEvent.change(screen.getByPlaceholderText("Bir şey yazın..."), { target: { value: "Öğrencinin notları" } });
    fireEvent.click(screen.getByRole("button", { name: "Mesaj gönder" }));
    await screen.findByText("Lütfen öğrenci seçin.");
    await act(async () => { resolveStudents({ data: { data: [first, second] } }); });
    fireEvent.change(screen.getByRole("combobox", { name: "Bu mesaj için öğrenci seçin" }), { target: { value: second.id } });
    await screen.findByText("Ece için kayıt bulundu.");
    expect(api.post).toHaveBeenLastCalledWith("/v1/chatbot/process-query", expect.objectContaining({ query: "Öğrencinin notları", student_id: second.id }));
  });

  it("öğrenci okuma yetkisi olmayan muhasebe kullanıcısı için yetkisiz öğrenci isteği oluşturmaz", () => {
    useAuthStore.setState({ user: { ...admin, is_super_admin: false,
      roles: [{ id: "accountant", name: "Muhasebe", slug: "accountant" }], permissions: ["finance.read"] } });
    open();
    expect(screen.getByText("Mali İşler & Tahsilat Danışmanı")).toBeInTheDocument();
    expect(api.get).not.toHaveBeenCalled();
  });

  it("öğretmene bağlan düğmesinde standart API yanıtındaki katılımcı adını gösterir", async () => {
    useAuthStore.setState({ user: { ...admin, is_super_admin: false,
      roles: [{ id: "parent", name: "Veli", slug: "parent" }], permissions: ["parent.view_children"] } });
    vi.mocked(api.get).mockResolvedValue({ data: { data: [first] } } as any);
    vi.mocked(api.post).mockResolvedValueOnce(answer("Öğretmeninize bağlanabilirsiniz.", {
      suggested_actions: [{ label: "Öğretmene bağlan", action_tag: "CONNECT_TEACHER_1", target_teacher_id: "teacher-1" }],
    }) as any).mockResolvedValueOnce({ data: { data: { participant_name: "Ayşe Öğretmen" } } } as any);
    open();
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Öğrenci seçin" })).toHaveValue(first.id));
    fireEvent.change(screen.getByPlaceholderText("Bir şey yazın..."), { target: { value: "Öğretmenime ulaşmak istiyorum" } });
    fireEvent.click(screen.getByRole("button", { name: "Mesaj gönder" }));
    fireEvent.click(await screen.findByRole("button", { name: "Öğretmene bağlan" }));
    await screen.findByText("✅ Ayşe Öğretmen ile sohbet başlatıldı!");
    expect(api.post).toHaveBeenLastCalledWith("/v1/chatbot/chat/conversations/connect-teacher", expect.objectContaining({ student_id: first.id, teacher_id: "teacher-1" }));
  });
});

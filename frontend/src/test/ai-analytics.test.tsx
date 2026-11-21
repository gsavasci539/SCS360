import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ChatbotManagementPage } from "../features/ai/ChatbotManagementPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() },
  apiMessage: (failure: Error) => failure.message.startsWith("Kaydedilen") ? failure.message : "Analitik geçici olarak kullanılamıyor" }));
vi.mock("../lib/diagnostics", () => ({ reportClientError: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

const metrics = { overview: { total_logs: 3, avg_latency_ms: 200, avg_quality_rating: 3,
  quality_rated_count: 2, finetuning_ready_count: 1 },
  distributions: { sentiment: {}, topic: {}, intent: {}, feedback_status: {} } };

it("gerçek kalite ortalamasını puanlı kayıt sayısıyla gösterir", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path.includes("analytics") ? metrics : { logs: [], total: 0 } } }));
  render(<ChatbotManagementPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Analitik" }));
  expect(await screen.findByText("3.0/5")).toBeInTheDocument();
  expect(screen.getByText("2 puanlı kayıt")).toBeInTheDocument();
  expect(screen.getByText("200ms")).toBeInTheDocument();
});

it("boş veya puanlanmamış kayıtta sıfır kalite uydurmaz", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => ({ data: { data: path.includes("analytics")
    ? { ...metrics, overview: { ...metrics.overview, total_logs: 0, avg_latency_ms: null, avg_quality_rating: null, quality_rated_count: 0 } }
    : { logs: [], total: 0 } } }));
  render(<ChatbotManagementPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Analitik" }));
  expect(await screen.findByText("Puanlanmadı")).toBeInTheDocument();
  expect(screen.getByText("Veri yok")).toBeInTheDocument();
  expect(screen.queryByText("0.0/5")).not.toBeInTheDocument();
});

it("analitik hatasını gösterir ve yeniden denemeyle gerçek veriyi yükler", async () => {
  let reads = 0;
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path.includes("analytics") && reads++ === 0) throw new Error("503");
    return { data: { data: path.includes("analytics") ? metrics : { logs: [], total: 0 } } };
  });
  render(<ChatbotManagementPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Analitik" }));
  expect(await screen.findByText("Analitik geçici olarak kullanılamıyor")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
  expect(await screen.findByText("3.0/5")).toBeInTheDocument();
  expect(screen.queryByText("Analitik geçici olarak kullanılamıyor")).not.toBeInTheDocument();
});

it("kayıt aynı kurumdan doğrulanana kadar düzenleme taslağını korur", async () => {
  const log = { id: "audit-log", organization_id: "school", sender_name: "İzole hesap", sender_role: "teacher",
    user_query: "İzole soru", ai_response: "İzole yanıt", detected_intent: null, topic_category: null,
    sentiment: "NEUTRAL", feedback_status: "NEEDS_REVIEW", quality_rating: 0, is_fine_tuning_ready: false,
    created_at: "2026-11-21T10:00:00Z", token_count: 10, latency_ms: 20 };
  vi.mocked(api.get).mockImplementation(async (path) => ({
    data: { success: true, data: path.includes("analytics") ? metrics : { logs: [log], total: 1 } },
  }));
  vi.mocked(api.put).mockResolvedValue({ data: { success: true, data: { log_id: log.id } } });
  render(<ChatbotManagementPage />);
  const search = await screen.findByPlaceholderText("Mesajlarda ara...");
  fireEvent.change(search, { target: { value: "eşleşmeyen" } });
  expect(screen.queryByText("İzole soru")).not.toBeInTheDocument();
  fireEvent.change(search, { target: { value: "" } });
  fireEvent.click(await screen.findByText("İzole soru"));
  fireEvent.click(screen.getByRole("button", { name: "Düzenle" }));
  fireEvent.click(screen.getByRole("button", { name: "Kalite puanı 4" }));
  fireEvent.change(screen.getByLabelText("Durum"), { target: { value: "CORRECTED" } });
  fireEvent.change(screen.getByLabelText("Düzeltilmiş yanıt"), { target: { value: "Doğrulanacak yanıt" } });
  fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Kaydedilen geri bildirim doğrulanamadı.");
  expect(screen.getByLabelText("Düzeltilmiş yanıt")).toHaveValue("Doğrulanacak yanıt");
  expect(api.get).toHaveBeenCalledWith("/v1/chatbot/ai/audit-logs", { params: { record_id: log.id, page: 1, page_size: 1 } });
});

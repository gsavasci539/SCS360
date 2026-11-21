import { getAnalysis } from "../../lib/analysis";
import { reportClientError } from "../../lib/diagnostics";
import { Utensils, CreditCard, AlertCircle, CheckCircle, Search, Plus, Minus, X, TrendingUp, Package } from "lucide-react";
import { useState, useEffect, useLayoutEffect, useRef } from "react";
import { PageHeader, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { CanteenReceipt } from "./CanteenReceipt";
import { newRequestId } from "../../lib/requestId";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import { hasPermission, useAuthStore } from "../../stores/auth";
import type { ApiResponse } from "../../types/api";

interface CanteenProduct {
  id: string;
  branch_id: string;
  name: string;
  category: string;
  price: number;
  image_url: string;
  is_available: boolean;
  allergens: string[];
}

interface CartItem {
  product: CanteenProduct;
  quantity: number;
}

interface StudentInfo {
  id: string;
  name: string;
  branch: string;
  balance: number;
  daily_limit: number | null;
  daily_spent: number;
  dietary_restrictions: string[];
}

type StudentChoice = { id: string; name: string; active: boolean };
type CanteenReceiptRecord = Parameters<typeof CanteenReceipt>[0]["order"];
interface WalletApi {
  student_id: string; student_name: string; branch_id: string;
  balance: number; daily_limit: number | null; daily_spent: number; dietary_restrictions: string[];
}
interface CartReceiptItem { order_id: string; product_id: string; quantity: number; total: number }
interface StoredOrder {
  id: string; student_id: string; student_name: string; branch_id: string; branch_name?: string;
  product_id: string; product_name: string; quantity: number; unit_price: number; total_price: number;
  status: string; payment_method: string; order_date: string; order_time: string; processed_by_name?: string;
}

interface RfidCard {
  id: string;
  card_number: string;
  holder_name: string;
  card_type: string;
  status: string;
}

function recordedAmount(value: unknown) {
  const amount = typeof value === "number" ? value
    : typeof value === "string" && /^\d+(?:\.\d+)?$/.test(value) ? Number(value) : Number.NaN;
  return Number.isFinite(amount) && amount >= 0 ? `${amount.toFixed(2)} TL` : "Tutar bilinmiyor";
}

function recordedDate(value: unknown, exclusive = false) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Tarih bilinmiyor";
  const parsed = new Date(`${value}T00:00:00Z`);
  if (!Number.isFinite(parsed.getTime())) return "Tarih bilinmiyor";
  if (exclusive) parsed.setUTCDate(parsed.getUTCDate() - 1);
  return parsed.toLocaleDateString("tr-TR", { timeZone: "UTC" });
}

function recordedAsOf(value: unknown, timezone: unknown) {
  if (typeof value !== "string") return "Güncelleme zamanı bilinmiyor";
  const parsed = new Date(value);
  if (!Number.isFinite(parsed.getTime())) return "Güncelleme zamanı bilinmiyor";
  try {
    return parsed.toLocaleString("tr-TR", { timeZone: typeof timezone === "string" ? timezone : "Europe/Istanbul" });
  } catch { return "Güncelleme zamanı bilinmiyor"; }
}

function stockPresentation(status: unknown) {
  if (status === "healthy") return { label: "İyi", background: "#dcfce7" };
  if (status === "warning") return { label: "Uyarı", background: "#fef3c7" };
  if (status === "critical") return { label: "Kritik", background: "#fee2e2" };
  return { label: "Stok verisi yok", background: "#f8faf8" };
}

function recordedTrend(trend: unknown) {
  if (trend === "increasing") return "Artış";
  if (trend === "decreasing") return "Düşüş";
  if (trend === "stable") return "Stabil";
  if (trend === "recorded") return "Kayıtlı satış özeti";
  return "Trend için veri yetersiz";
}

export function CanteenSalesPage() {
  const viewer = useWorkspaceUser();
  const session = useAuthStore((state) => state.sessionVersion);
  const canWrite = hasPermission(viewer, "canteen.write");
  if (viewer?.is_super_admin) return <p>Kantin işlemleri için kurum çalışma alanını seçin.</p>;
  return <CanteenSalesWorkspace canWrite={canWrite}
    key={JSON.stringify([session, viewer?.id, viewer?.organization_id, viewer?.branch_ids, canWrite])} />;
}

function CanteenSalesWorkspace({ canWrite }: { canWrite: boolean }) {
  const [products, setProducts] = useState<CanteenProduct[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [studentInfo, setStudentInfo] = useState<StudentInfo | null>(null);
  const [choices, setChoices] = useState<StudentChoice[]>([]);
  const [studentSearch, setStudentSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [rfidCards, setRfidCards] = useState<RfidCard[]>([]);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [selectedCard, setSelectedCard] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [wifiDeviceId, setWifiDeviceId] = useState("");
  const [showReceipt, setShowReceipt] = useState(false);
  const [lastOrder, setLastOrder] = useState<CanteenReceiptRecord | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const selection = useRef<AbortController | null>(null);
  const sale = useRef<AbortController | null>(null);
  const operation = useRef<{ id: string; signature: string } | null>(null);
  const lastCardRead = useRef("");
  const [unconfirmed, setUnconfirmed] = useState(false);
  useLayoutEffect(() => () => { selection.current?.abort(); sale.current?.abort(); }, []);

  async function loadRfidCards() {
    setCardsLoading(true);
    try {
      const response = await api.get<ApiResponse<RfidCard[]>>("/rfid-cards");
      setRfidCards(response.data.data || []);
    } catch (err) {
      reportClientError("Failed to load RFID cards:", err);
    } finally {
      setCardsLoading(false);
    }
  }

  async function loadAiAnalysis() {
    try {
      const response = await getAnalysis<ApiResponse<any>>("/ai/canteen-analysis");
      if (response.data.success) {
        setAiAnalysis(response.data.data);
      }
    } catch (err) {
      // AI analysis is optional, don't fail the page if it errors
      reportClientError("Failed to load AI analysis:", err);
    }
  }

  const handleCardSelect = (cardNumber: string) => {
    setStudentSearch(cardNumber);
    setSelectedCard(cardNumber);
  };

  async function loadWallet(studentId: string, signal: AbortSignal) {
    const read = await api.get<ApiResponse<WalletApi>>(`/canteen/student/${encodeURIComponent(studentId)}/wallet`, { signal });
    if (signal.aborted) return null;
    const wallet = read.data.data;
    if (wallet?.student_id !== studentId || !wallet.branch_id || typeof wallet.student_name !== "string" ||
        ![wallet.balance, wallet.daily_spent].every(Number.isFinite) ||
        (wallet.daily_limit !== null && !Number.isFinite(wallet.daily_limit)) || !Array.isArray(wallet.dietary_restrictions)) {
      throw new Error("Sunucudaki öğrenci cüzdanı doğrulanamadı.");
    }
    return { id: wallet.student_id, name: wallet.student_name, branch: wallet.branch_id, balance: wallet.balance,
      daily_limit: wallet.daily_limit, daily_spent: wallet.daily_spent, dietary_restrictions: wallet.dietary_restrictions };
  }

  async function selectWallet(studentId: string, signal: AbortSignal) {
    const wallet = await loadWallet(studentId, signal);
    if (!wallet || signal.aborted) return;
    const response = await api.get<ApiResponse<CanteenProduct[]>>("/canteen/products", {
      params: { branch_id: wallet.branch, is_available: true, limit: 1000 }, signal,
    });
    if (signal.aborted) return;
    if (!Array.isArray(response.data.data) || response.data.data.some((row) => row.branch_id !== wallet.branch)) {
      throw new Error("Kantin ürünleri öğrencinin şubesiyle eşleşmedi.");
    }
    setProducts(response.data.data);
    setStudentInfo(wallet);
    setChoices([]);
    if (studentInfo?.id !== wallet.id || studentInfo?.branch !== wallet.branch) {
      setCart([]);
      operation.current = null;
      setUnconfirmed(false);
    }
  }

  async function selectTarget(action: (signal: AbortSignal) => Promise<void>) {
    if (sale.current || unconfirmed) return;
    selection.current?.abort();
    const controller = new AbortController();
    selection.current = controller;
    setLoading(true);
    setError("");
    setSuccess("");
    try { await action(controller.signal); }
    catch (reason) {
      if (!controller.signal.aborted) { setError(apiMessage(reason)); setStudentInfo(null); setCart([]); }
    } finally {
      if (selection.current === controller) { selection.current = null; setLoading(false); }
    }
  }

  async function handleCardRead(cardNumber: string) {
    if (sale.current || unconfirmed) return;
    setStudentSearch(cardNumber);
    setSelectedCard(cardNumber);
    await selectTarget(async (signal) => {
      const response = await api.post<ApiResponse<{ holder_id: string; holder_type?: string }>>(
        "/hardware/card/balance", { card_number: cardNumber.trim() }, { signal },
      );
      if (signal.aborted) return;
      const card = response.data.data;
      if (!card?.holder_id || (card.holder_type && card.holder_type !== "STUDENT")) throw new Error("Öğrenci kartı doğrulanamadı.");
      await selectWallet(card.holder_id, signal);
    });
  }

  async function loadProducts() {
    setLoading(true);
    try {
      const response = await api.get<ApiResponse<CanteenProduct[]>>("/canteen/products?is_available=true");
      if (!selection.current && !sale.current) setProducts(response.data.data || []);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProducts();
    void loadRfidCards();
    void loadAiAnalysis();
  }, []);

  useEffect(() => {
    if (!wifiDeviceId.trim() || unconfirmed) return;
    const controller = new AbortController();
    let pending = false;
    const pollInterval = setInterval(async () => {
      if (pending || sale.current || selection.current) return;
      pending = true;
      try {
        const response = await api.get<ApiResponse<{ id: string; card_number: string; success: boolean }[]>>("/hardware/wifi/card-reads", {
          params: { device_id: wifiDeviceId.trim(), limit: 1 }, signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        const newest = response.data.data?.[0];
        if (newest?.id && newest.success && newest.card_number && newest.id !== lastCardRead.current) {
          lastCardRead.current = newest.id;
          await handleCardRead(newest.card_number);
        }
      } catch (err) {
        if (!controller.signal.aborted) reportClientError("Error polling WiFi card reads:", err);
      } finally {
        pending = false;
      }
    }, 1000);
    return () => { controller.abort(); clearInterval(pollInterval); };
  }, [wifiDeviceId, unconfirmed, studentInfo?.id, studentInfo?.branch]);

  // RFID kart okuma için keyboard input dinleme
  useEffect(() => {
    let cardBuffer = "";
    let lastKeyTime = 0;
    const CARD_READ_TIMEOUT = 100; // ms between keystrokes
    const MIN_CARD_LENGTH = 8;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Sadece input odaklı değilse dinle
      if (document.activeElement instanceof HTMLInputElement) return;
      
      const currentTime = Date.now();
      
      // Enter tuşu ile kart okuma tamamlandı
      if (e.key === "Enter") {
        if (cardBuffer.length >= MIN_CARD_LENGTH && (currentTime - lastKeyTime) < 500) {
          void handleCardRead(cardBuffer);
          cardBuffer = "";
        }
        return;
      }
      
      // Kart okuma zaman aşımı kontrolü
      if (currentTime - lastKeyTime > CARD_READ_TIMEOUT) {
        cardBuffer = "";
      }
      
      // Sadece sayıları kabul et
      if (e.key >= "0" && e.key <= "9") {
        cardBuffer += e.key;
        lastKeyTime = currentTime;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [studentInfo?.id, studentInfo?.branch, unconfirmed]);

  const searchStudent = async (searchTerm?: string) => {
    const term = (searchTerm ?? studentSearch).trim();
    if (!term) { setError("Öğrenci adı veya kart numarası girin."); return; }
    if (selectedCard && selectedCard === term) { await handleCardRead(term); return; }
    await selectTarget(async (signal) => {
      const response = await api.get<ApiResponse<{ students: StudentChoice[] }>>("/canteen/options", {
        params: { search: term }, signal,
      });
      if (signal.aborted) return;
      const students = (response.data.data?.students ?? []).filter((row) => row.active);
      if (students.length === 1) { await selectWallet(students[0].id, signal); return; }
      setStudentInfo(null);
      setCart([]);
      setChoices(students);
      if (!students.length) setError("Öğrenci bulunamadı. Kart ile aramak için teslim edilen kartı okutun.");
    });
  };

  const addToCart = (product: CanteenProduct) => {
    if (!canWrite || unconfirmed || sale.current) return;
    if (!studentInfo || product.branch_id !== studentInfo.branch) { setError("Önce şubedeki öğrenciyi seçin."); return; }
    // Alerjen kontrolü
    if (studentInfo && studentInfo.dietary_restrictions.length > 0) {
      const conflicts = product.allergens.filter(a => studentInfo.dietary_restrictions.includes(a));
      if (conflicts.length > 0) {
        setError(`Bu ürün öğrencinin diyet kısıtlamaları içeriyor: ${conflicts.join(", ")}`);
        return;
      }
    }

    const existingItem = cart.find(item => item.product.id === product.id);
    if (existingItem) {
      setCart(cart.map(item => 
        item.product.id === product.id 
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, { product, quantity: 1 }]);
    }
    setError("");
  };

  const removeFromCart = (productId: string) => {
    if (unconfirmed || sale.current) return;
    setCart(cart.filter(item => item.product.id !== productId));
  };

  const updateQuantity = (productId: string, delta: number) => {
    if (unconfirmed || sale.current) return;
    setCart(cart.map(item => {
      if (item.product.id === productId) {
        const newQuantity = Math.max(1, item.quantity + delta);
        return { ...item, quantity: newQuantity };
      }
      return item;
    }));
  };

  const clearCart = () => {
    if (unconfirmed || sale.current) return;
    setCart([]);
  };

  const checkout = async () => {
    if (!canWrite || sale.current || selection.current || !studentInfo || !cart.length) return;
    const wallet = studentInfo;
    const items = cart.map((line) => ({ product_id: line.product.id, quantity: line.quantity, expected_unit_price: line.product.price }));
    if (cart.some((line) => line.product.branch_id !== wallet.branch)) {
      setError("Sepette öğrencinin şubesi dışından ürün var.");
      return;
    }
    const signature = JSON.stringify([wallet.id, wallet.branch, items]);
    if (!operation.current || operation.current.signature !== signature) operation.current = { signature, id: newRequestId() };
    const id = operation.current.id;
    const controller = new AbortController();
    sale.current = controller;
    const { signal } = controller;
    setProcessing(true);
    setUnconfirmed(true);
    setError("");
    setSuccess("");
    let acknowledged = false;
    try {
      const response = await api.post<ApiResponse<{
        operation_id: string; student_id: string; branch_id: string; authorized: boolean; items: CartReceiptItem[];
      }>>("/canteen/pos/cart-checkout", { student_id: wallet.id, branch_id: wallet.branch, request_id: id, items }, { signal });
      if (signal.aborted) return;
      const ack = response.data.data;
      if (ack?.operation_id !== id || ack.student_id !== wallet.id || ack.branch_id !== wallet.branch ||
          ack.authorized !== true || !Array.isArray(ack.items) || ack.items.length !== items.length ||
          new Set(ack.items.map((item) => item.order_id)).size !== items.length) {
        throw new Error("Kantin satış kimliği doğrulanamadı.");
      }
      acknowledged = true;
      const confirmed = await Promise.all(ack.items.map(async (receipt): Promise<StoredOrder> => {
        const expected = items.find((item) => item.product_id === receipt.product_id);
        if (!expected || expected.quantity !== receipt.quantity || !receipt.order_id) throw new Error("Sepet satırı eşleşmedi.");
        const read = await api.get<ApiResponse<StoredOrder[]>>("/canteen/orders", {
          params: { student_id: wallet.id, branch_id: wallet.branch, record_id: receipt.order_id, limit: 1 }, signal,
        });
        const rows = read.data.data;
        const stored = Array.isArray(rows) && rows.length === 1 ? rows[0] : undefined;
        if (!stored || stored.id !== receipt.order_id || stored.student_id !== wallet.id || stored.branch_id !== wallet.branch ||
            stored.product_id !== receipt.product_id || stored.quantity !== receipt.quantity || stored.status !== "COMPLETED" ||
            stored.payment_method !== "WALLET" || Number(stored.unit_price) !== expected.expected_unit_price ||
            Number(stored.total_price) !== Number(receipt.total)) throw new Error("Kayıtlı sipariş satırı eşleşmedi.");
        return stored;
      }));
      const fresh = await loadWallet(wallet.id, signal);
      if (signal.aborted) return;
      if (!fresh || fresh.branch !== wallet.branch) throw new Error("Güncel cüzdan kapsamı doğrulanamadı.");
      const first = confirmed[0];
      setLastOrder({
        id, order_number: id, order_date: first.order_date, order_time: first.order_time,
        items: confirmed.map((row) => ({ product: { id: row.product_id, name: row.product_name,
          category: "", price: Number(row.unit_price) }, quantity: row.quantity })),
        total_amount: confirmed.reduce((sum, line) => sum + Math.round(Number(line.total_price) * 100), 0) / 100,
        payment_method: "Cüzdan", student_name: first.student_name, branch_name: first.branch_name ?? "",
        organization_name: "", processed_by: first.processed_by_name,
      });
      setStudentInfo(fresh);
      setSuccess("Sipariş sunucudan doğrulandı");
      setCart([]);
      setShowReceipt(true);
      operation.current = null;
      setUnconfirmed(false);
    } catch (reason) {
      if (signal.aborted) return;
      const status = (reason as { response?: { status?: number } } | null)?.response?.status;
      if (!acknowledged && status && [400, 401, 403, 404, 409, 422].includes(status)) {
        operation.current = null;
        setUnconfirmed(false);
      }
      setError(apiMessage(reason));
    } finally {
      if (sale.current === controller) { sale.current = null; setProcessing(false); }
    }
  };

  const categories = ["all", ...Array.from(new Set(products.map(p => p.category)))];
  const filteredProducts = selectedCategory === "all" 
    ? products 
    : products.filter(p => p.category === selectedCategory);
  const total = cart.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);

  if (loading && products.length === 0) return <div className="card"><LoadingState label="Yükleniyor" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Kantin"
        title="Satış Ekranı"
        description="Kantin ürün satışı ve sipariş yönetimi"
      />

      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>Kayıtlı Kantin Özeti</h2>
              <p>Tamamlanan cüzdan harcamaları ve doğrudan satışlar</p>
            </div>
            <TrendingUp size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <p style={{ fontSize: 13, marginBottom: 16 }}>
              Dönem: {recordedDate(aiAnalysis.period_start)} – {recordedDate(aiAnalysis.period_end_exclusive, true)}
              {Number.isInteger(aiAnalysis.observed_day_count) && aiAnalysis.observed_day_count >= 0 && <> · {aiAnalysis.observed_day_count} gözlenen gün</>}
              <br />Son durum: {recordedAsOf(aiAnalysis.as_of, aiAnalysis.timezone)}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Satış</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{recordedAmount(aiAnalysis.total_sales)}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Günlük Ortalama</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{recordedAmount(aiAnalysis.daily_average)}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: stockPresentation(aiAnalysis.inventory_status).background }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Stok Durumu</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{stockPresentation(aiAnalysis.inventory_status).label}</div>
              </div>
            </div>
            <dl style={{ fontSize: 14, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12, marginBottom: 16 }}>
              <div><dt>Cüzdandan harcama</dt><dd>{recordedAmount(aiAnalysis.wallet_debit_amount)}</dd></div>
              <div><dt>Doğrudan satış</dt><dd>{recordedAmount(aiAnalysis.direct_sale_amount)}</dd></div>
              <div><dt>Bakiye yüklemeleri</dt><dd>{recordedAmount(aiAnalysis.topup_amount)}</dd></div>
              <div><dt>Eski katalog siparişleri</dt><dd>{recordedAmount(aiAnalysis.catalog_orders?.amount)}</dd></div>
            </dl>
            <p style={{ fontSize: 13, marginBottom: 16 }}>Bakiye yüklemeleri ve eski katalog siparişleri satış toplamına dahil edilmez. Katalog kayıt sayısı ödeme fişi sayısı değildir.</p>
            {aiAnalysis.requires_review === true && <p role="status">Bazı kayıtlar incelenmeli; belirsiz tutarlar toplam olarak gösterilmez.</p>}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Trend</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: aiAnalysis.trend === "increasing" ? "#166534" : aiAnalysis.trend === "decreasing" ? "#991b1b" : "#1b2b2e" }}>
                {recordedTrend(aiAnalysis.trend)}
              </div>
            </div>
            {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                {aiAnalysis.recommendations.slice(0, 2).map((rec: string, index: number) => (
                  <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                    <Package size={16} color="#176b5b" style={{ flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: 13 }}>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 18, marginTop: 18 }}>
        {/* Ürünler */}
        <div className="card">
          <div className="card-head">
            <h2>Ürünler</h2>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{
                padding: "6px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 4,
                fontSize: 14
              }}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {cat === "all" ? "Tümü" : cat}
                </option>
              ))}
            </select>
          </div>
          <div className="card-pad">
            <div style={{ 
              display: "grid", 
              gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 180px), 1fr))",
              gap: 16 
            }}>
              {filteredProducts.map(product => (
                <div
                  key={product.id}
                  onClick={() => addToCart(product)}
                  role={canWrite ? "button" : undefined}
                  tabIndex={canWrite && !unconfirmed ? 0 : undefined}
                  aria-disabled={canWrite && unconfirmed ? true : undefined}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); addToCart(product); }
                  }}
                  style={{
                    border: "1px solid #e5e7eb",
                    borderRadius: 8,
                    padding: 16,
                    cursor: "pointer",
                    transition: "all 0.2s",
                    backgroundColor: "white"
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = "#3b82f6"}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = "#e5e7eb"}
                >
                  <div style={{ 
                    width: 48, 
                    height: 48, 
                    borderRadius: 8, 
                    backgroundColor: "#f3f4f6", 
                    display: "flex", 
                    alignItems: "center", 
                    justifyContent: "center",
                    marginBottom: 12
                  }}>
                    <Utensils size={24} color="#6b7280" />
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{product.name}</div>
                  <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>{product.category}</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "#059669" }}>{product.price.toFixed(2)} TL</div>
                  {product.allergens.length > 0 && (
                    <div style={{ fontSize: 10, color: "#dc2626", marginTop: 4 }}>
                      Alerjen: {product.allergens.join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sepet ve Öğrenci Bilgisi */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {/* Öğrenci Arama */}
          <div className="card">
            <div className="card-head">
              <h2>Öğrenci</h2>
            </div>
            <div className="card-pad">
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                  WiFi Cihaz ID (Opsiyonel)
                </label>
                <input
                  type="text"
                  placeholder="WiFi RFID cihaz ID'si girin"
                  value={wifiDeviceId}
                  onChange={(e) => setWifiDeviceId(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4,
                    fontSize: 14
                  }}
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                  Sistemdeki Kartlardan Seçin
                </label>
                <select
                  value={selectedCard}
                  onChange={(e) => handleCardSelect(e.target.value)}
                  disabled={cardsLoading || processing || unconfirmed}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    border: "1px solid #d1d5db",
                    borderRadius: 6,
                    fontSize: 14,
                    backgroundColor: "white"
                  }}
                >
                  <option value="">Kart seçin...</option>
                  {rfidCards.map((card) => (
                    <option key={card.id} value={card.card_number}>
                      {card.card_number} - {card.holder_name} ({card.card_type})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                <input
                  type="text"
                  placeholder="Öğrenci ara veya kart okutun"
                  value={studentSearch}
                  disabled={unconfirmed || processing}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && searchStudent()}
                  ref={inputRef}
                  style={{
                    flex: "1 1 180px",
                    minWidth: 0,
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4,
                    fontSize: 14
                  }}
                />
                <button
                  className="btn btn-primary"
                  aria-label="Öğrenciyi ara"
                  onClick={() => searchStudent()}
                  disabled={loading || processing || unconfirmed}
                >
                  <Search size={16} />
                </button>
              </div>
              {choices.length > 1 && <ul aria-label="Eşleşen öğrenciler">
                {choices.map((choice) => <li key={choice.id}>
                  <button className="btn btn-secondary" disabled={processing || unconfirmed}
                    onClick={() => void selectTarget((signal) => selectWallet(choice.id, signal))}>{choice.name}</button>
                </li>)}
              </ul>}

              {studentInfo && (
                <div style={{
                  padding: 12,
                  backgroundColor: "#f0f9ff",
                  border: "1px solid #bae6fd",
                  borderRadius: 6
                }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{studentInfo.name}</div>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>
                    Bakiye: <span style={{ fontWeight: 600, color: "#059669" }}>{studentInfo.balance.toFixed(2)} TL</span>
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>
                    Günlük harcama {studentInfo.daily_spent.toFixed(2)} TL
                    {studentInfo.daily_limit !== null && ` / ${studentInfo.daily_limit.toFixed(2)} TL`}
                  </div>
                  {studentInfo.dietary_restrictions.length > 0 && (
                    <div style={{ fontSize: 11, color: "#dc2626", marginTop: 4 }}>
                      Alerjiler: {studentInfo.dietary_restrictions.join(", ")}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sepet */}
          <div className="card">
            <div className="card-head">
              <h2>Sepet</h2>
              {cart.length > 0 && (
                <button
                  onClick={clearCart}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#dc2626",
                    cursor: "pointer",
                    fontSize: 12
                  }}
                >
                  Temizle
                </button>
              )}
            </div>
            <div className="card-pad">
              {cart.length === 0 ? (
                <p style={{ color: "#6b7280", fontSize: 14, textAlign: "center", padding: 20 }}>
                  Sepet boş
                </p>
              ) : (
                <>
                  {cart.map(item => (
                    <div
                      key={item.product.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 0",
                        borderBottom: "1px solid #f3f4f6"
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 500 }}>{item.product.name}</div>
                        <div style={{ fontSize: 12, color: "#6b7280" }}>{item.product.price.toFixed(2)} TL</div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <button
                          onClick={() => updateQuantity(item.product.id, -1)}
                          style={{
                            width: 24,
                            height: 24,
                            borderRadius: 4,
                            border: "1px solid #d1d5db",
                            background: "white",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                          }}
                        >
                          <Minus size={14} />
                        </button>
                        <span style={{ fontSize: 14, fontWeight: 600, minWidth: 24, textAlign: "center" }}>
                          {item.quantity}
                        </span>
                        <button
                          onClick={() => updateQuantity(item.product.id, 1)}
                          style={{
                            width: 24,
                            height: 24,
                            borderRadius: 4,
                            border: "1px solid #d1d5db",
                            background: "white",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                          }}
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                      <button
                        onClick={() => removeFromCart(item.product.id)}
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: 4,
                          border: "none",
                          background: "#fee2e2",
                          color: "#dc2626",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                  <div style={{
                    marginTop: 16,
                    paddingTop: 16,
                    borderTop: "2px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}>
                    <span style={{ fontSize: 14, fontWeight: 600 }}>Toplam</span>
                    <span style={{ fontSize: 18, fontWeight: 600, color: "#059669" }}>{total.toFixed(2)} TL</span>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={checkout}
                    disabled={processing || !studentInfo || !canWrite}
                    style={{
                      width: "100%",
                      marginTop: 12,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    {processing ? <LoadingState label="İşleniyor..." /> : (
                      <>
                        <CreditCard size={16} />
                        {unconfirmed ? "Aynı siparişi doğrula" : "Cüzdandan satışı kaydet"}
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {showReceipt && lastOrder && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0, 0, 0, 0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>
          <div style={{
            background: "white",
            borderRadius: 8,
            maxWidth: "90%",
            maxHeight: "90vh",
            overflow: "auto"
          }}>
            <CanteenReceipt 
              order={lastOrder} 
              onClose={() => setShowReceipt(false)} 
            />
          </div>
        </div>
      )}

      {error && (
        <div style={{ 
          marginTop: 18,
          padding: 12, 
          backgroundColor: "#fee2e2", 
          border: "1px solid #fecaca", 
          borderRadius: 6,
          color: "#991b1b",
          display: "flex",
          alignItems: "center",
          gap: 8
        }}>
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {success && (
        <div style={{ 
          marginTop: 18,
          padding: 12, 
          backgroundColor: "#dcfce7", 
          border: "1px solid #bbf7d0", 
          borderRadius: 6,
          color: "#166534",
          display: "flex",
          alignItems: "center",
          gap: 8
        }}>
          <CheckCircle size={16} />
          {success}
        </div>
      )}
    </>
  );
}

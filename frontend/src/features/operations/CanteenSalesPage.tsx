import { getAnalysis } from "../../lib/analysis";
import { reportClientError } from "../../lib/diagnostics";
import { Utensils, CreditCard, AlertCircle, CheckCircle, Search, Plus, Minus, X, TrendingUp, Package } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { PageHeader, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { CanteenReceipt } from "./CanteenReceipt";
import type { ApiResponse } from "../../types/api";

interface CanteenProduct {
  id: string;
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
  balance: number;
  daily_limit: number;
  daily_spent: number;
  dietary_restrictions: string[];
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
  const [products, setProducts] = useState<CanteenProduct[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [studentInfo, setStudentInfo] = useState<StudentInfo | null>(null);
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
  const [lastOrder, setLastOrder] = useState<any>(null);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);

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

  async function handleCardRead(cardNumber: string) {
    setStudentSearch(cardNumber);
    setSelectedCard(cardNumber);
    
    // Önce öğrenci bilgilerini al
    setLoading(true);
    setError("");
    try {
      const cardResponse = await api.post<ApiResponse<any>>("/hardware/card/balance", {
        card_number: cardNumber.trim()
      });
      
      if (cardResponse.data.success && cardResponse.data.data) {
        const cardData = cardResponse.data.data;
        setStudentInfo({
          id: cardData.holder_id,
          name: cardData.holder_name,
          balance: cardData.balance,
          daily_limit: cardData.daily_limit,
          daily_spent: cardData.daily_spent,
          dietary_restrictions: []
        });
        
        // Sepette ürün varsa otomatik checkout yap
        if (cart.length > 0) {
          await checkoutWithCard(cardData.holder_id);
        }
      }
    } catch (err) {
      setError(apiMessage(err));
      setStudentInfo(null);
    } finally {
      setLoading(false);
    }
  }

  async function checkoutWithCard(studentId: string) {
    if (cart.length === 0) {
      setError("Sepet boş");
      return;
    }

    const total = cart.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);
    
    if (studentInfo && studentInfo.balance < total) {
      setError(`Yetersiz bakiye. Mevcut: ${studentInfo.balance} TL, Toplam: ${total} TL`);
      return;
    }

    if (studentInfo && studentInfo.daily_spent + total > studentInfo.daily_limit) {
      setError(`Günlük limit aşıldı. Bugün harcanan: ${studentInfo.daily_spent} TL, Limit: ${studentInfo.daily_limit} TL`);
      return;
    }

    setProcessing(true);
    setError("");

    try {
      // Her ürün için sipariş oluştur
      const orderItems = [];
      for (const item of cart) {
        await api.post("/canteen/pos/checkout", {
          student_id: studentId,
          product_id: item.product.id,
          quantity: item.quantity,
          payment_method: "WALLET"
        });
        orderItems.push(item);
      }

      // Sipariş detaylarını kaydet ve makbuzu göster
      const totalAmount = cart.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);
      const now = new Date();
      const orderNumber = `KAN-${now.getTime()}`;
      
      setLastOrder({
        id: orderNumber,
        order_number: orderNumber,
        order_date: now.toISOString(),
        order_time: now.toTimeString(),
        items: orderItems,
        total_amount: totalAmount,
        payment_method: "Cüzdan",
        student_name: studentInfo?.name || "Öğrenci",
        student_number: studentInfo?.id,
        branch_name: "Ana Şube",
        organization_name: "SCS360",
        organization_address: "İstanbul, Türkiye",
        organization_phone: "+90 212 123 4567",
        processed_by: "Kantin Personeli"
      });

      setSuccess("Sipariş başarıyla tamamlandı");
      clearCart();
      setShowReceipt(true);
      
      // Öğrenci bilgilerini yenile
      const walletResponse = await api.get<ApiResponse<StudentInfo>>(`/canteen/student/${studentId}/wallet`);
      setStudentInfo(walletResponse.data.data);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setProcessing(false);
    }
  }

  async function loadProducts() {
    setLoading(true);
    try {
      const response = await api.get<ApiResponse<CanteenProduct[]>>("/canteen/products?is_available=true");
      setProducts(response.data.data || []);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProducts();
    loadRfidCards();
    loadAiAnalysis();
    
    // WiFi card read polling
    const pollInterval = setInterval(async () => {
      if (wifiDeviceId && cart.length > 0) {
        try {
          const response = await api.get<ApiResponse<any[]>>(`/hardware/wifi/card-reads?device_id=${wifiDeviceId}&limit=1`);
          const cardReads = response.data.data || [];
          
          if (cardReads.length > 0) {
            const latestRead = cardReads[0];
            if (latestRead.card_number && latestRead.success) {
              await handleCardRead(latestRead.card_number);
            }
          }
        } catch (err) {
          reportClientError("Error polling WiFi card reads:", err);
        }
      }
    }, 1000); // Poll every second
    
    return () => clearInterval(pollInterval);
  }, [wifiDeviceId, cart]);

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
          // Kart okundu - otomatik checkout yap
          handleCardRead(cardBuffer);
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
  }, [cart, studentInfo]);

  const searchStudent = async (searchTerm?: string) => {
    const termToSearch = searchTerm || studentSearch;
    if (!termToSearch.trim()) {
      setError("Lütfen öğrenci adı, ID veya kart numarası girin");
      return;
    }

    setLoading(true);
    setError("");
    try {
      // Önce kart numarası ile ara
      const cardResponse = await api.post<ApiResponse<any>>("/hardware/card/balance", {
        card_number: termToSearch.trim()
      });
      
      if (cardResponse.data.success && cardResponse.data.data) {
        const cardData = cardResponse.data.data;
        setStudentInfo({
          id: cardData.holder_id,
          name: cardData.holder_name,
          balance: cardData.balance,
          daily_limit: cardData.daily_limit,
          daily_spent: cardData.daily_spent,
          dietary_restrictions: []
        });
        setSuccess("");
        return;
      }
      
      // Kart bulunamazsa öğrenci ara
      const response = await api.get<ApiResponse<any>>(`/students?search=${termToSearch}`);
      const students = response.data.data || [];
      
      if (students.length === 0) {
        setError("Öğrenci veya kart bulunamadı");
        setStudentInfo(null);
        return;
      }

      const student = students[0];
      
      // Cüzdan bilgilerini al
      const walletResponse = await api.get<ApiResponse<StudentInfo>>(`/canteen/student/${student.id}/wallet`);
      setStudentInfo(walletResponse.data.data);
      setSuccess("");
    } catch (err) {
      setError(apiMessage(err));
      setStudentInfo(null);
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (product: CanteenProduct) => {
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
    setCart(cart.filter(item => item.product.id !== productId));
  };

  const updateQuantity = (productId: string, delta: number) => {
    setCart(cart.map(item => {
      if (item.product.id === productId) {
        const newQuantity = Math.max(1, item.quantity + delta);
        return { ...item, quantity: newQuantity };
      }
      return item;
    }));
  };

  const clearCart = () => {
    setCart([]);
  };

  const checkout = async () => {
    if (!studentInfo) {
      setError("Lütfen önce öğrenci seçin");
      return;
    }

    if (cart.length === 0) {
      setError("Sepet boş");
      return;
    }

    const total = cart.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);
    
    if (studentInfo.balance < total) {
      setError(`Yetersiz bakiye. Mevcut: ${studentInfo.balance} TL, Toplam: ${total} TL`);
      return;
    }

    if (studentInfo.daily_spent + total > studentInfo.daily_limit) {
      setError(`Günlük limit aşıldı. Bugün harcanan: ${studentInfo.daily_spent} TL, Limit: ${studentInfo.daily_limit} TL`);
      return;
    }

    setProcessing(true);
    setError("");

    try {
      // Her ürün için sipariş oluştur
      for (const item of cart) {
        await api.post("/canteen/pos/checkout", {
          student_id: studentInfo.id,
          product_id: item.product.id,
          quantity: item.quantity,
          payment_method: "WALLET"
        });
      }

      setSuccess("Sipariş başarıyla tamamlandı");
      clearCart();
      
      // Öğrenci bilgilerini yenile
      const walletResponse = await api.get<ApiResponse<StudentInfo>>(`/canteen/student/${studentInfo.id}/wallet`);
      setStudentInfo(walletResponse.data.data);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setProcessing(false);
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
              <h2>AI Kantin Analizi</h2>
              <p>Satış trendleri ve stok durumu</p>
            </div>
            <TrendingUp size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}>
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr 350px", gap: 18, marginTop: 18 }}>
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
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", 
              gap: 16 
            }}>
              {filteredProducts.map(product => (
                <div
                  key={product.id}
                  onClick={() => addToCart(product)}
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
                  disabled={cardsLoading}
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

              <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                <input
                  type="text"
                  placeholder="Öğrenci adı, ID veya kart okutun"
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && searchStudent()}
                  ref={inputRef}
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4,
                    fontSize: 14
                  }}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => searchStudent()}
                  disabled={loading}
                >
                  <Search size={16} />
                </button>
              </div>

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
                    Günlük: {studentInfo.daily_spent.toFixed(2)} / {studentInfo.daily_limit.toFixed(2)} TL
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
                    disabled={processing || !studentInfo}
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
                        Ödeme Yap
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

import { CreditCard, Plus, AlertCircle, CheckCircle, Search, User, GraduationCap, ShieldCheck } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { PageHeader, Badge, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

interface CardBalanceInfo {
  card_number: string;
  holder_id: string;
  holder_name: string;
  holder_type: string; // STUDENT, TEACHER, ADMIN
  holder_role?: string;
  balance: number;
  daily_limit: number;
  daily_spent: number;
  card_status: string;
  class_name?: string;
  branch_name?: string;
}

interface RfidCard {
  id: string;
  card_number: string;
  holder_name: string;
  card_type: string;
  status: string;
}

export function CardBalancePage() {
  const [cardNumber, setCardNumber] = useState("");
  const [cardInfo, setCardInfo] = useState<CardBalanceInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [topUpAmount, setTopUpAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("CASH");
  const [referenceNumber, setReferenceNumber] = useState("");
  const [topUpLoading, setTopUpLoading] = useState(false);
  const [topUpSuccess, setTopUpSuccess] = useState(false);
  const [topUpMessage, setTopUpMessage] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [rfidCards, setRfidCards] = useState<RfidCard[]>([]);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [selectedCard, setSelectedCard] = useState("");

  // RFID kartlarını yükle
  useEffect(() => {
    async function loadRfidCards() {
      setCardsLoading(true);
      try {
        const response = await api.get<ApiResponse<RfidCard[]>>("/rfid-cards");
        setRfidCards(response.data.data || []);
      } catch (err) {
        console.error("Failed to load RFID cards:", err);
      } finally {
        setCardsLoading(false);
      }
    }
    loadRfidCards();
  }, []);

  // RFID kart okuma için keyboard input dinleme
  useEffect(() => {
    let cardBuffer = "";
    let lastKeyTime = 0;
    const CARD_READ_TIMEOUT = 100; // ms between keystrokes
    const MIN_CARD_LENGTH = 8;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Sadece input odaklıyken veya sayfa aktifken dinle
      if (e.key === "Enter") {
        const currentTime = Date.now();
        if (cardBuffer.length >= MIN_CARD_LENGTH && (currentTime - lastKeyTime) < 500) {
          // Kart okundu
          setCardNumber(cardBuffer);
          cardBuffer = "";
          return;
        }
        cardBuffer = "";
        return;
      }

      // Sadece sayıları ve harfleri kabul et
      if (e.key.length === 1) {
        const currentTime = Date.now();
        
        // Eğer son çok hızlı girilmişse, bu bir kart okuması olabilir
        if (currentTime - lastKeyTime < CARD_READ_TIMEOUT) {
          cardBuffer += e.key;
        } else {
          // Çok yavaş girilmiş, manuel giriş olabilir
          cardBuffer = e.key;
        }
        
        lastKeyTime = currentTime;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    
    // Sayfa yüklendiğinde input'a odaklan
    if (inputRef.current) {
      inputRef.current.focus();
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const handleCardSelect = (cardNumber: string) => {
    setCardNumber(cardNumber);
    setSelectedCard(cardNumber);
  };

  const handleSearchCard = async (cardNum?: string, isRefresh: boolean = false) => {
    const numberToSearch = cardNum || cardNumber;
    if (!numberToSearch.trim()) {
      if (!isRefresh) {
        setError("Lütfen kart numarası girin veya kart okutun");
      }
      return;
    }

    setLoading(true);
    setError("");
    // Sadece manuel arama yapılırsa cardInfo'yi temizle
    if (!cardNum && !isRefresh) {
      setCardInfo(null);
    }
    setTopUpSuccess(false);
    setTopUpMessage("");

    try {
      const response = await api.post<ApiResponse<CardBalanceInfo>>("/hardware/card/balance", {
        card_number: numberToSearch.trim()
      });
      setCardInfo(response.data.data);
      // Sadece manuel arama yapılırsa kart numarasını temizle
      if (!cardNum && !isRefresh) {
        setCardNumber("");
        setSelectedCard("");
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleTopUp = async () => {
    if (!cardInfo) return;
    
    const amount = parseFloat(topUpAmount);
    if (!amount || amount <= 0) {
      setError("Lütfen geçerli bir tutar girin");
      return;
    }

    setTopUpLoading(true);
    setError("");
    setTopUpSuccess(false);
    setTopUpMessage("");

    try {
      const response = await api.post<ApiResponse<any>>(`/hardware/card/topup?card_number=${cardInfo.card_number}&amount=${amount}&payment_method=${paymentMethod}${referenceNumber ? `&reference_number=${referenceNumber}` : ""}`, {});
      
      if (response.data.success) {
        setTopUpSuccess(true);
        setTopUpMessage("Bakiye başarıyla yüklendi");
        setTopUpAmount("");
        setReferenceNumber("");
        
        // Update balance from response
        if (response.data.data && response.data.data.new_balance !== undefined && cardInfo) {
          console.log('Updating balance from response:', response.data.data.new_balance);
          setCardInfo({
            ...cardInfo,
            balance: response.data.data.new_balance
          });
        }
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setTopUpLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearchCard();
    }
  };

  const getHolderIcon = (type: string) => {
    switch (type) {
      case "STUDENT":
        return GraduationCap;
      case "TEACHER":
        return User;
      case "ADMIN":
        return ShieldCheck;
      default:
        return User;
    }
  };

  const getHolderTypeLabel = (type: string) => {
    switch (type) {
      case "STUDENT":
        return "Öğrenci";
      case "TEACHER":
        return "Öğretmen";
      case "ADMIN":
        return "İdareci";
      default:
        return type;
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Operasyonel"
        title="Kart Bakiye Yükleme"
        description="RFID kartlarına bakiye yükleme ve kart bilgilerini görüntüleme"
      />

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kart Sorgula</h2>
        </div>
        <div className="card-pad">
          <div style={{ marginBottom: 16 }}>
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

          <div style={{ 
            padding: 12, 
            backgroundColor: "#f3f4f6", 
            borderRadius: 6, 
            marginBottom: 16,
            textAlign: "center",
            fontSize: 13,
            color: "#6b7280"
          }}>
            veya
          </div>

          <div style={{ display: "flex", gap: 12, marginBottom: 18 }}>
            <input
              ref={inputRef}
              type="text"
              placeholder="Kart numarası girin veya kart okutun..."
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              onKeyPress={handleKeyPress}
              style={{
                flex: 1,
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
                fontSize: 14
              }}
            />
            <button
              className="btn btn-primary"
              onClick={() => handleSearchCard()}
              disabled={loading}
            >
              {loading ? <LoadingState label="Aranıyor..." /> : <Search size={16} />}
              {!loading && " Sorgula"}
            </button>
          </div>

          {error && (
            <div style={{ 
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

          {topUpSuccess && (
            <div style={{ 
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
              {topUpMessage}
            </div>
          )}
        </div>
      </div>

      {cardInfo && (
        <>
          <div className="card" style={{ marginTop: 18 }}>
            <div className="card-head">
              <h2>Kart Bilgileri</h2>
              <Badge value={cardInfo.card_status} />
            </div>
            <div className="card-pad">
              <div style={{ 
                padding: 16, 
                backgroundColor: "#f0f9ff", 
                border: "1px solid #bae6fd", 
                borderRadius: 8,
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 16
              }}>
                <div style={{ 
                  width: 48, 
                  height: 48, 
                  borderRadius: "50%", 
                  backgroundColor: "#3b82f6", 
                  display: "flex", 
                  alignItems: "center", 
                  justifyContent: "center",
                  color: "white"
                }}>
                  {(() => {
                    const HolderIcon = getHolderIcon(cardInfo.holder_type);
                    return <HolderIcon size={24} />;
                  })()}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 18, fontWeight: 600, color: "#1e3a8a" }}>{cardInfo.holder_name}</div>
                  <div style={{ fontSize: 14, color: "#64748b", display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                    <span style={{ 
                      padding: "2px 8px", 
                      backgroundColor: "#dbeafe", 
                      borderRadius: 4, 
                      fontSize: 12, 
                      fontWeight: 500,
                      color: "#1e40af"
                    }}>
                      {getHolderTypeLabel(cardInfo.holder_type)}
                    </span>
                    {cardInfo.holder_role && (
                      <span style={{ fontSize: 13, color: "#64748b" }}>• {cardInfo.holder_role}</span>
                    )}
                  </div>
                  {cardInfo.class_name && (
                    <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>
                      {cardInfo.class_name}
                    </div>
                  )}
                  {cardInfo.branch_name && (
                    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
                      {cardInfo.branch_name}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Kart Numarası</label>
                  <div style={{ fontSize: 16, fontWeight: 500, display: "flex", alignItems: "center", gap: 8 }}>
                    <CreditCard size={18} />
                    {cardInfo.card_number}
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Mevcut Bakiye</label>
                  <div style={{ fontSize: 20, fontWeight: 600, color: "#059669" }}>
                    {cardInfo.balance !== undefined && cardInfo.balance !== null ? `${cardInfo.balance.toFixed(2)} TL` : '0.00 TL'}
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Günlük Limit</label>
                  <div style={{ fontSize: 16, fontWeight: 500 }}>{cardInfo.daily_limit.toFixed(2)} TL</div>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Bugün Harcanan</label>
                  <div style={{ fontSize: 16, fontWeight: 500 }}>{cardInfo.daily_spent.toFixed(2)} TL</div>
                </div>
              </div>

              <div style={{ marginTop: 16, padding: 12, backgroundColor: "#f3f4f6", borderRadius: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 14, color: "#6b7280" }}>Günlük Kullanım</span>
                  <span style={{ fontSize: 14, fontWeight: 500 }}>
                    {cardInfo.daily_spent.toFixed(2)} / {cardInfo.daily_limit.toFixed(2)} TL
                  </span>
                </div>
                <div style={{ 
                  marginTop: 8, 
                  height: 8, 
                  backgroundColor: "#e5e7eb", 
                  borderRadius: 4, 
                  overflow: "hidden" 
                }}>
                  <div 
                    style={{ 
                      height: "100%", 
                      width: `${Math.min((cardInfo.daily_spent / cardInfo.daily_limit) * 100, 100)}%`,
                      backgroundColor: cardInfo.daily_spent > cardInfo.daily_limit ? "#ef4444" : "#10b981"
                    }} 
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 18 }}>
            <div className="card-head">
              <h2>Bakiye Yükle</h2>
              <Plus size={20} />
            </div>
            <div className="card-pad">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Yüklenecek Tutar (TL)</label>
                  <input
                    type="number"
                    placeholder="0.00"
                    value={topUpAmount}
                    onChange={(e) => setTopUpAmount(e.target.value)}
                    min="0"
                    step="0.01"
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      border: "1px solid #d1d5db",
                      borderRadius: 6,
                      fontSize: 14
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Ödeme Yöntemi</label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      border: "1px solid #d1d5db",
                      borderRadius: 6,
                      fontSize: 14,
                      backgroundColor: "white"
                    }}
                  >
                    <option value="CASH">Nakit</option>
                    <option value="CARD">Kredi Kartı</option>
                    <option value="BANK_TRANSFER">Banka Havalesi</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>Referans Numarası (Opsiyonel)</label>
                  <input
                    type="text"
                    placeholder="Referans numarası"
                    value={referenceNumber}
                    onChange={(e) => setReferenceNumber(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      border: "1px solid #d1d5db",
                      borderRadius: 6,
                      fontSize: 14
                    }}
                  />
                </div>
              </div>

              <div style={{ 
                padding: 16, 
                backgroundColor: "#f0fdf4", 
                border: "1px solid #bbf7d0", 
                borderRadius: 6,
                marginBottom: 16
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 14, color: "#166534" }}>Yükleme Sonrası Bakiye</span>
                  <span style={{ fontSize: 18, fontWeight: 600, color: "#166534" }}>
                    {(cardInfo.balance + (parseFloat(topUpAmount) || 0)).toFixed(2)} TL
                  </span>
                </div>
              </div>

              <button
                className="btn btn-primary"
                onClick={handleTopUp}
                disabled={topUpLoading || !topUpAmount || parseFloat(topUpAmount) <= 0}
                style={{ width: "100%" }}
              >
                {topUpLoading ? <LoadingState label="Yükleniyor..." /> : <Plus size={16} />}
                {!topUpLoading && " Bakiye Yükle"}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}

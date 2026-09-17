import { Printer, ArrowLeft } from "lucide-react";
import { useState } from "react";
import { money, shortDate, formatTime } from "../lib/format";

interface ReceiptItem {
  name: string;
  description?: string;
  quantity?: number;
  price?: number;
  total?: number;
}

interface GenericReceiptProps {
  receipt: {
    id: string;
    receipt_number: string;
    receipt_date: string;
    receipt_time: string;
    title: string;
    items: ReceiptItem[];
    total_amount: number;
    payment_method: string;
    entity_info: {
      name: string;
      tax_number?: string;
      address?: string;
      phone?: string;
    };
    customer_info?: {
      name: string;
      number?: string;
      additional_info?: Record<string, string>;
    };
    location_info?: {
      branch?: string;
      class?: string;
    };
    notes?: string;
    processed_by?: string;
  };
  onClose?: () => void;
  type?: "canteen" | "payment" | "generic";
}

export function GenericReceipt({ receipt, onClose, type = "generic" }: GenericReceiptProps) {
  const [showPrint, setShowPrint] = useState(false);

  function handlePrint() {
    setShowPrint(true);
    setTimeout(() => {
      window.print();
      setShowPrint(false);
    }, 100);
  }

  const themeColor = type === "canteen" ? "#2d8f78" : type === "payment" ? "#3b82f6" : "#6366f1";

  return (
    <div style={{ padding: 20, maxWidth: 400, margin: "0 auto" }}>
      {!showPrint && (
        <div style={{ marginBottom: 20, display: "flex", gap: 10 }}>
          {onClose && (
            <button className="btn btn-secondary" onClick={onClose}>
              <ArrowLeft size={16} />Geri
            </button>
          )}
          <button className="btn btn-primary" onClick={handlePrint}>
            <Printer size={16} />Yazdır
          </button>
        </div>
      )}

      <div
        style={{
          background: "white",
          padding: "20px",
          border: "1px solid #e5e7eb",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          fontFamily: "Courier New, monospace",
          fontSize: "12px"
        }}
        className="generic-receipt"
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 20, paddingBottom: 15, borderBottom: `1px dashed ${themeColor}` }}>
          <h1 style={{ fontSize: "18px", fontWeight: "bold", margin: "0 0 5px", color: themeColor }}>
            {receipt.entity_info.name}
          </h1>
          {receipt.entity_info.tax_number && (
            <div style={{ fontSize: "11px", color: "#666", marginBottom: 3 }}>
              Vergi No: {receipt.entity_info.tax_number}
            </div>
          )}
          {receipt.entity_info.address && (
            <div style={{ fontSize: "11px", color: "#666", marginBottom: 3 }}>
              {receipt.entity_info.address}
            </div>
          )}
          {receipt.entity_info.phone && (
            <div style={{ fontSize: "11px", color: "#666" }}>
              Tel: {receipt.entity_info.phone}
            </div>
          )}
        </div>

        {/* Receipt Title */}
        <div style={{ textAlign: "center", marginBottom: 15 }}>
          <div style={{ fontSize: "14px", fontWeight: "bold", marginBottom: 5 }}>{receipt.title}</div>
          <div style={{ fontSize: "11px", color: "#666" }}>
            {receipt.receipt_number}
          </div>
          <div style={{ fontSize: "11px", color: "#666" }}>
            {shortDate(receipt.receipt_date)} - {formatTime(receipt.receipt_time)}
          </div>
        </div>

        {/* Customer Info */}
        {receipt.customer_info && (
          <div style={{ background: "#f8f9fa", padding: 10, borderRadius: 4, marginBottom: 15 }}>
            <div style={{ fontSize: "12px", fontWeight: "bold", marginBottom: 5 }}>
              {receipt.customer_info.name ? "Müşteri Bilgileri" : "Bilgiler"}
            </div>
            <div style={{ fontSize: "11px" }}>
              <strong>Ad Soyad:</strong> {receipt.customer_info.name}
            </div>
            {receipt.customer_info.number && (
              <div style={{ fontSize: "11px" }}>
                <strong>No:</strong> {receipt.customer_info.number}
              </div>
            )}
            {receipt.customer_info.additional_info && 
              Object.entries(receipt.customer_info.additional_info).map(([key, value]) => (
                <div key={key} style={{ fontSize: "11px" }}>
                  <strong>{key}:</strong> {value}
                </div>
              ))
            }
          </div>
        )}

        {/* Location Info */}
        {receipt.location_info && (
          <div style={{ marginBottom: 15, fontSize: "11px" }}>
            {receipt.location_info.branch && (
              <div><strong>Şube:</strong> {receipt.location_info.branch}</div>
            )}
            {receipt.location_info.class && (
              <div><strong>Sınıf:</strong> {receipt.location_info.class}</div>
            )}
          </div>
        )}

        {/* Items */}
        <div style={{ marginBottom: 15 }}>
          <div style={{ fontSize: "12px", fontWeight: "bold", marginBottom: 8, paddingBottom: 5, borderBottom: "1px dashed #ccc" }}>
            Kalem Bilgileri
          </div>
          {receipt.items.map((item, index) => (
            <div key={index} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span>{item.name}</span>
                {item.quantity && <span>x{item.quantity}</span>}
              </div>
              {item.description && (
                <div style={{ fontSize: "10px", color: "#666" }}>
                  {item.description}
                </div>
              )}
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#666" }}>
                <span>{item.price ? money(item.price) : ""}</span>
                <span>{item.total ? money(item.total) : (item.price && item.quantity ? money(item.price * item.quantity) : "")}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Summary */}
        <div style={{ borderTop: "1px dashed #333", paddingTop: 10, marginBottom: 15 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: 5 }}>
            <span>Ödeme Yöntemi:</span>
            <span>{receipt.payment_method}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: 5 }}>
            <span>Tarih:</span>
            <span>{shortDate(receipt.receipt_date)}</span>
          </div>
          {receipt.notes && (
            <div style={{ fontSize: "11px", color: "#666", marginBottom: 5 }}>
              <strong>Not:</strong> {receipt.notes}
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", fontWeight: "bold", marginTop: 10, paddingTop: 10, borderTop: "1px solid #333" }}>
            <span>TOPLAM:</span>
            <span>{money(receipt.total_amount)}</span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 15, paddingTop: 10, borderTop: "1px dashed #333", textAlign: "center", fontSize: "10px", color: "#666" }}>
          <div style={{ marginBottom: 3 }}>Bu makbuz bilgisayar ortamında üretilmiştir.</div>
          <div>{receipt.receipt_number}</div>
          {receipt.processed_by && (
            <div>İşlemi Yapan: {receipt.processed_by}</div>
          )}
        </div>
      </div>

      <style>{`
        @media print {
          body { 
            padding: 0; 
            margin: 0; 
            background: white !important;
          }
          .generic-receipt { 
            box-shadow: none !important; 
            border: none !important;
            margin: 0 !important;
            padding: 10px !important;
            width: 100% !important;
            max-width: none !important;
          }
          button, a { display: none !important; }
          @page {
            margin: 0;
            size: 80mm auto;
          }
        }
      `}</style>
    </div>
  );
}

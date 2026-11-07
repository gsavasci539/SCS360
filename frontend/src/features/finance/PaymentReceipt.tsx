import { Printer, ArrowLeft } from "lucide-react";
import { useState } from "react";
import { ReceiptBrand } from "../../components/Brand";
import { money, shortDate, formatTime } from "../../lib/format";

interface PaymentReceiptProps {
  payment: {
    id: string;
    payment_number: string;
    payment_date: string;
    payment_time: string;
    amount: number;
    payment_method: string;
    payment_type: string;
    student_name: string;
    student_number?: string;
    class_name?: string;
    branch_name: string;
    organization_name: string;
    organization_tax_number?: string;
    organization_address?: string;
    organization_phone?: string;
    description?: string;
    processed_by?: string;
  };
  onClose?: () => void;
}

export function PaymentReceipt({ payment, onClose }: PaymentReceiptProps) {
  const [showPrint, setShowPrint] = useState(false);

  function handlePrint() {
    setShowPrint(true);
    setTimeout(() => {
      window.print();
      setShowPrint(false);
    }, 100);
  }

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
        className="payment-receipt"
      >
        {/* Header */}
        <ReceiptBrand />
        <div style={{ textAlign: "center", marginBottom: 20, paddingBottom: 15, borderBottom: "1px dashed #333" }}>
          <h1 style={{ fontSize: "18px", fontWeight: "bold", margin: "0 0 5px", color: "#2d8f78" }}>
            {payment.organization_name}
          </h1>
          {payment.organization_tax_number && (
            <div style={{ fontSize: "11px", color: "#666", marginBottom: 3 }}>
              Vergi No: {payment.organization_tax_number}
            </div>
          )}
          {payment.organization_address && (
            <div style={{ fontSize: "11px", color: "#666", marginBottom: 3 }}>
              {payment.organization_address}
            </div>
          )}
          {payment.organization_phone && (
            <div style={{ fontSize: "11px", color: "#666" }}>
              Tel: {payment.organization_phone}
            </div>
          )}
        </div>

        {/* Receipt Title */}
        <div style={{ textAlign: "center", marginBottom: 15 }}>
          <div style={{ fontSize: "14px", fontWeight: "bold", marginBottom: 5 }}>ÖDEME MAKBUZU</div>
          <div style={{ fontSize: "11px", color: "#666" }}>
            Ödeme No: {payment.payment_number}
          </div>
          <div style={{ fontSize: "11px", color: "#666" }}>
            {shortDate(payment.payment_date)} - {formatTime(payment.payment_time)}
          </div>
        </div>

        {/* Student Info */}
        <div style={{ background: "#f8f9fa", padding: 10, borderRadius: 4, marginBottom: 15 }}>
          <div style={{ fontSize: "12px", fontWeight: "bold", marginBottom: 5 }}>Öğrenci Bilgileri</div>
          <div style={{ fontSize: "11px" }}>
            <strong>Ad Soyad:</strong> {payment.student_name}
          </div>
          {payment.student_number && (
            <div style={{ fontSize: "11px" }}>
              <strong>Öğrenci No:</strong> {payment.student_number}
            </div>
          )}
          {payment.class_name && (
            <div style={{ fontSize: "11px" }}>
              <strong>Sınıf:</strong> {payment.class_name}
            </div>
          )}
          <div style={{ fontSize: "11px" }}>
            <strong>Şube:</strong> {payment.branch_name}
          </div>
        </div>

        {/* Payment Details */}
        <div style={{ marginBottom: 15 }}>
          <div style={{ fontSize: "12px", fontWeight: "bold", marginBottom: 8, paddingBottom: 5, borderBottom: "1px dashed #ccc" }}>
            Ödeme Detayları
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
              <span>Ödeme Türü:</span>
              <span>{payment.payment_type}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#666" }}>
              <span>Ödeme Yöntemi:</span>
              <span>{payment.payment_method}</span>
            </div>
          </div>
          {payment.description && (
            <div style={{ fontSize: "11px", color: "#666", marginBottom: 8 }}>
              <strong>Açıklama:</strong> {payment.description}
            </div>
          )}
        </div>

        {/* Summary */}
        <div style={{ borderTop: "1px dashed #333", paddingTop: 10, marginBottom: 15 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: 5 }}>
            <span>Ödeme Tarihi:</span>
            <span>{shortDate(payment.payment_date)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", fontWeight: "bold", marginTop: 10, paddingTop: 10, borderTop: "1px solid #333" }}>
            <span>TOPLAM:</span>
            <span>{money(payment.amount)}</span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 15, paddingTop: 10, borderTop: "1px dashed #333", textAlign: "center", fontSize: "10px", color: "#666" }}>
          <div style={{ marginBottom: 3 }}>Bu makbuz bilgisayar ortamında üretilmiştir.</div>
          <div>Ödeme No: {payment.payment_number}</div>
          {payment.processed_by && (
            <div>İşlemi Yapan: {payment.processed_by}</div>
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
          .payment-receipt { 
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

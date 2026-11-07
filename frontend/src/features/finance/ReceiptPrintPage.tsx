import { ArrowLeft, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "../../components/ui";
import { ReceiptBrand } from "../../components/Brand";
import { api, apiMessage } from "../../lib/api";
import { textValue } from "../../lib/data";
import { money, shortDate } from "../../lib/format";
import type { ApiResponse } from "../../types/api";

interface Receipt {
  status?: string;
  id: string;
  payment_id?: string;
  receipt_number: string;
  payment_date: string;
  amount: number;
  payment_method: string;
  student_name: string;
  student_number?: string;
  parent_name?: string;
  organization_name: string;
  organization_tax_number?: string;
  organization_address?: string;
  organization_phone?: string;
  branch_name: string;
  branch_address?: string;
  notes?: string;
  remaining_debt?: number;
  received_by?: string;
}

export function ReceiptPrintPage() {
  const { id } = useParams();
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await api.get<ApiResponse<Partial<Receipt> & Record<string, unknown>>>(`/receipts/${id}`);
        const receiptRecord = response.data.data;
        if (!receiptRecord) throw new Error("Makbuz bulunamadı.");

        let payment: Record<string, unknown> = {};
        const paymentId = textValue(receiptRecord.payment_id, "");
        if (paymentId) {
          const paymentResponse = await api.get<ApiResponse<Record<string, unknown>>>(`/payments/${paymentId}`);
          payment = paymentResponse.data.data || {};
        }

        let student: Record<string, unknown> = {};
        const studentId = textValue(payment.student_id || receiptRecord.student_id, "");
        if (studentId) {
          const studentResponse = await api.get<ApiResponse<Record<string, unknown>>>(`/students/${studentId}`);
          student = studentResponse.data.data || {};
        }

        setReceipt({
          id: textValue(receiptRecord.id, id || ""),
          payment_id: paymentId,
          receipt_number: textValue(receiptRecord.receipt_number),
          status: textValue(receiptRecord.status, "ACTIVE"),
          payment_date: textValue(payment.payment_date || receiptRecord.payment_date || receiptRecord.issued_at, ""),
          amount: Number(payment.amount || receiptRecord.amount || 0),
          payment_method: textValue(payment.payment_method || receiptRecord.payment_method),
          student_name: textValue(receiptRecord.student_name, [student.first_name, student.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ") || "Öğrenci"),
          student_number: textValue(receiptRecord.student_number || student.student_number, "") || undefined,
          parent_name: textValue(receiptRecord.parent_name, "") || undefined,
          organization_name: textValue(receiptRecord.organization_name, "Okul Yönetim Sistemi"),
          organization_tax_number: textValue(receiptRecord.organization_tax_number, "") || undefined,
          organization_address: textValue(receiptRecord.organization_address, "") || undefined,
          organization_phone: textValue(receiptRecord.organization_phone, "") || undefined,
          branch_name: textValue(receiptRecord.branch_name, ""),
          branch_address: textValue(receiptRecord.branch_address, "") || undefined,
          notes: textValue(payment.notes || receiptRecord.notes, "") || undefined,
          remaining_debt: Number(receiptRecord.remaining_debt || 0),
          received_by: textValue(receiptRecord.received_by, "") || undefined,
        });
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  function handlePrint() {
    window.print();
  }

  if (loading) return <div className="card"><LoadingState label="Makbuz yükleniyor" /></div>;
  if (error || !receipt) return <div className="card"><ErrorState message={error || "Makbuz bulunamadı."} /></div>;

  const printReceipt = receipt;

  function renderReceiptCopy(copyType: "parent" | "management") {
    return (
      <div style={{
        width: "100%",
        height: "50%",
        padding: "10mm",
        borderBottom: copyType === "parent" ? "3px dashed #ddd" : "none",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        boxSizing: "border-box"
      }}>
        {/* Header */}
        <ReceiptBrand />
        <div style={{
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          color: "white",
          padding: "8mm",
          borderRadius: "6px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "8mm",
          boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)"
        }}>
          <h3 style={{ font: "700 12px Manrope", margin: 0, letterSpacing: "0.5px" }}>
            {printReceipt.organization_name}
          </h3>
          <span style={{
            fontSize: "9px",
            fontWeight: "700",
            color: "white",
            background: "rgba(255, 255, 255, 0.2)",
            padding: "2mm 6mm",
            borderRadius: "15px",
            backdropFilter: "blur(10px)"
          }}>
            {copyType === "parent" ? "VELİ KOPYASI" : "YÖNETİM KOPYASI"}
          </span>
        </div>

        {/* Receipt Title */}
        <div style={{ textAlign: "center", marginBottom: "8mm" }}>
          <h2 style={{ 
            font: "700 14px Manrope", 
            margin: "0 0 4px", 
            color: receipt?.status === "CANCELLED" ? "#b42318" : "#333",
            letterSpacing: "1px",
            textTransform: "uppercase"
          }}>
            {receipt?.status === "CANCELLED" ? "İPTAL EDİLMİŞ MAKBUZ" : "TAHSİLAT MAKBUZU"}
          </h2>
        </div>

        {/* Receipt Info */}
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "8mm",
          padding: "5mm",
          background: "#f8f9fa",
          borderRadius: "4px",
          borderLeft: "3px solid #667eea"
        }}>
          <div style={{ display: "flex", gap: "2mm", alignItems: "center" }}>
            <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", textTransform: "uppercase" }}>Makbuz No:</span>
            <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.receipt_number}</span>
          </div>
          <div style={{ display: "flex", gap: "2mm", alignItems: "center" }}>
            <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", textTransform: "uppercase" }}>Tarih:</span>
            <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{shortDate(printReceipt.payment_date)}</span>
          </div>
        </div>

        {/* Receipt Details */}
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
            <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Şube:</span>
            <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.branch_name}</span>
          </div>
          <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
            <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Öğrenci:</span>
            <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.student_name}</span>
          </div>
          {printReceipt.student_number && (
            <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Öğrenci No:</span>
              <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.student_number}</span>
            </div>
          )}
          {printReceipt.parent_name && (
            <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Veli:</span>
              <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.parent_name}</span>
            </div>
          )}
          <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
            <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Ödeme Tutarı:</span>
            <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{money(printReceipt.amount)} TL</span>
          </div>
          <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
            <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Ödeme Yöntemi:</span>
            <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.payment_method}</span>
          </div>
          {printReceipt.remaining_debt !== undefined && printReceipt.remaining_debt > 0 && (
            <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Kalan Borç:</span>
              <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{money(printReceipt.remaining_debt)} TL</span>
            </div>
          )}
          {printReceipt.received_by && (
            <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Tahsilatı Alan:</span>
              <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.received_by}</span>
            </div>
          )}
          {printReceipt.notes && (
            <div style={{ display: "flex", marginBottom: "3mm", padding: "2mm 0", borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ fontWeight: "600", fontSize: "8px", color: "#555", width: "25mm", textTransform: "uppercase" }}>Not:</span>
              <span style={{ fontSize: "8px", color: "#333", fontWeight: "500" }}>{printReceipt.notes}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          marginTop: "auto",
          paddingTop: "5mm",
          borderTop: "1px solid #f0f0f0"
        }}>
          <p style={{ fontSize: "7px", color: "#666", fontStyle: "italic", margin: "0 0 4mm 0", textAlign: "center" }}>
            Bu belge SCS360 üzerinden oluşturulmuştur.
          </p>
          {copyType === "management" && (
            <div style={{ display: "flex", alignItems: "center", gap: "2mm", justifyContent: "center" }}>
              <span style={{ fontSize: "7px", fontWeight: "600", color: "#555" }}>İmza:</span>
              <div style={{ 
                flex: 1, 
                height: "1px", 
                background: "linear-gradient(90deg, #667eea 0%, #764ba2 100%)",
                maxWidth: "35mm"
              }}></div>
            </div>
          )}
        </div>

        {/* Cut line for parent copy */}
        {copyType === "parent" && (
          <div style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "3px",
            background: "repeating-linear-gradient(90deg, #ddd, #ddd 10px, transparent 10px, transparent 20px)"
          }}></div>
        )}
      </div>
    );
  }

  return (
    <div style={{ 
      padding: 20, 
      maxWidth: "900px", 
      margin: "0 auto",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      minHeight: "100vh"
    }}>
      <div style={{ marginBottom: 20 }}>
        <Link className="btn btn-secondary" to={`/finance/receipts/${id}`}>
          <ArrowLeft size={16} />Makbuz detayına dön
        </Link>
        <button className="btn btn-primary" onClick={handlePrint} style={{ marginLeft: 10 }}>
          <Printer size={16} />Yazdır
        </button>
      </div>

      <div
        style={{
          width: "210mm",
          height: "297mm",
          background: "white",
          margin: "0 auto",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          borderRadius: "10px",
          overflow: "hidden"
        }}
        className="print-page"
      >
        {renderReceiptCopy("parent")}
        {renderReceiptCopy("management")}
      </div>

      <style>{`
        @media print {
          body { 
            background: white;
            padding: 0;
          }
          .print-page { 
            box-shadow: none;
            border-radius: 0;
          }
          button, a { display: none !important; }
          @page {
            size: A4 portrait;
            margin: 0;
          }
        }
      `}</style>
    </div>
  );
}

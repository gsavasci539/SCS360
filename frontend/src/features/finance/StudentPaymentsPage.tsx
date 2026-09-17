import { ArrowLeft, CreditCard, Receipt, Wallet, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, StatCard, Badge } from "../../components/ui";
import { PaymentReceipt } from "./PaymentReceipt";
import { api, apiMessage } from "../../lib/api";
import { textValue, toArray } from "../../lib/data";
import { shortDate, money } from "../../lib/format";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

interface Payment {
  id: string;
  amount: number;
  payment_date: string;
  payment_method: string;
  notes?: string;
  receipt_id?: string;
}

interface Debt {
  id: string;
  amount: number;
  paid_amount: number;
  remaining_amount: number;
  due_date: string;
  status: string;
  type: string;
}

export function StudentPaymentsPage() {
  const { id } = useParams();
  const [student, setStudent] = useState<DataRecord | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showReceipt, setShowReceipt] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [studentRes, paymentsRes, debtsRes] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord>>(`/students/${id}`),
        api.get<ApiResponse<Payment[] | Paginated<Payment>>>(`/students/${id}/payments`),
        api.get<ApiResponse<Debt[] | Paginated<Debt>>>(`/debts`, { params: { student_id: id, limit: 100, page_size: 100 } })
      ]);

      if (studentRes.status === "fulfilled") {
        setStudent(studentRes.value.data.data);
      } else {
        throw new Error(apiMessage(studentRes.reason));
      }

      if (paymentsRes.status === "fulfilled") {
        setPayments(toArray(paymentsRes.value.data.data));
      } else {
        throw new Error(apiMessage(paymentsRes.reason));
      }

      if (debtsRes.status === "fulfilled") {
        setDebts(toArray(debtsRes.value.data.data));
      } else {
        throw new Error(apiMessage(debtsRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount), 0);
  const totalDebt = debts.reduce((sum, d) => sum + Number(d.amount), 0);
  const remainingDebt = debts.reduce((sum, d) => sum + Number(d.remaining_amount), 0);

  if (loading) return <div className="card"><LoadingState label="Ödeme geçmişi yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;

  const studentName = [student?.first_name, student?.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ");

  return (
    <>
      <PageHeader
        eyebrow="Ödeme geçmişi"
        title={studentName || "Öğrenci"}
        description="Öğrencinin borç ve ödeme kayıtları."
      >
        <Link className="btn btn-secondary" to={`/students/${id}`}>
          <ArrowLeft size={16} />Öğrenciye dön
        </Link>
      </PageHeader>

      <div className="grid stats-grid">
        <StatCard icon={<Wallet size={19} />} label="Toplam borç" value={money(totalDebt)} meta="Tüm borçlar" color="red" />
        <StatCard icon={<CreditCard size={19} />} label="Ödenen" value={money(totalPaid)} meta="Toplam tahsilat" color="green" />
        <StatCard icon={<Receipt size={19} />} label="Kalan borç" value={money(remainingDebt)} meta="Ödenmesi gereken" color="orange" />
      </div>

      <div className="grid dashboard-grid" style={{ marginTop: 18 }}>
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Borçlar</h2>
              <p>Öğrencinin aktif borç kayıtları</p>
            </div>
          </div>
          {debts.length === 0 ? (
            <div className="card-pad" style={{ textAlign: "center", padding: "40px 20px" }}>
              <Wallet size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
              <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Borç kaydı yok</h3>
              <p style={{ color: "#7a8888", fontSize: 13 }}>Öğrencinin aktif borç kaydı bulunmuyor.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Borç türü</th>
                    <th>Tutar</th>
                    <th>Vade</th>
                    <th>Kalan</th>
                    <th>Durum</th>
                  </tr>
                </thead>
                <tbody>
                  {debts.map((debt) => (
                    <tr key={debt.id}>
                      <td>{debt.type}</td>
                      <td>{money(debt.amount)}</td>
                      <td>{shortDate(debt.due_date)}</td>
                      <td>{money(debt.remaining_amount)}</td>
                      <td><Badge value={debt.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-head">
            <div>
              <h2>Ödemeler</h2>
              <p>Yapılan ödeme kayıtları</p>
            </div>
          </div>
          {payments.length === 0 ? (
            <div className="card-pad" style={{ textAlign: "center", padding: "40px 20px" }}>
              <CreditCard size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
              <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Ödeme kaydı yok</h3>
              <p style={{ color: "#7a8888", fontSize: 13 }}>Henüz ödeme yapılmamış.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tarih</th>
                    <th>Tutar</th>
                    <th>Yöntem</th>
                    <th>Makbuz</th>
                  </tr>
                </thead>
                <tbody>
                  {[...payments].sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime()).map((payment) => (
                    <tr key={payment.id}>
                      <td>{shortDate(payment.payment_date)}</td>
                      <td>{money(payment.amount)}</td>
                      <td><Badge value={payment.payment_method} /></td>
                      <td>
                        {payment.receipt_id ? (
                          <button
                            className="btn btn-ghost btn-icon"
                            onClick={() => {
                              setSelectedPayment(payment);
                              setShowReceipt(true);
                            }}
                            title="Makbuz yazdır"
                          >
                            <Printer size={15} />
                          </button>
                        ) : (
                          <span style={{ color: "#7a8888", fontSize: 13 }}>-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {showReceipt && selectedPayment && student && (
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
            <PaymentReceipt 
              payment={{
                id: selectedPayment.id,
                payment_number: selectedPayment.receipt_id || `ODE-${Date.now()}`,
                payment_date: selectedPayment.payment_date,
                payment_time: new Date(selectedPayment.payment_date).toTimeString(),
                amount: selectedPayment.amount,
                payment_method: selectedPayment.payment_method,
                payment_type: "Ödeme",
                student_name: `${student.first_name} ${student.last_name}`,
                student_number: student.student_number as string | undefined,
                class_name: student.class_name as string | undefined,
                branch_name: (student.branch_name as string | undefined) || "Ana Şube",
                organization_name: "Okul360",
                organization_tax_number: "1234567890",
                organization_address: "İstanbul, Türkiye",
                organization_phone: "+90 212 123 4567",
                description: selectedPayment.notes,
                processed_by: "Muhasebe Personeli"
              }}
              onClose={() => setShowReceipt(false)} 
            />
          </div>
        </div>
      )}
    </>
  );
}

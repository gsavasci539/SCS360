import { AlertTriangle, Bell, Download, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { money } from "../../lib/format";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface OverdueDebt {
  id: string;
  student_name: string;
  amount: number;
  remaining_amount: number;
  due_date: string;
  days_overdue: number;
  branch_name?: string;
  parent_phone?: string;
  parent_email?: string;
}

export function OverdueDebtsReport() {
  const [daysOverdue, setDaysOverdue] = useState("30");
  const [branchId, setBranchId] = useState("");
  const [branches, setBranches] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<OverdueDebt[]>([]);
  const [summary, setSummary] = useState({ count: 0, total: 0, avgDays: 0 });
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [branchesRes, dataRes] = await Promise.allSettled([
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/branches", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<OverdueDebt[] | Paginated<OverdueDebt>>>("/reports/overdue-debts", {
          params: {
            days_overdue: Number(daysOverdue),
            branch_id: branchId || undefined
          }
        })
      ]);

      if (branchesRes.status === "fulfilled") {
        setBranches(toArray(branchesRes.value.data.data));
      }

      if (dataRes.status === "fulfilled") {
        const reportData = toArray(dataRes.value.data.data);
        setData(reportData);
        const total = reportData.reduce((sum, item) => sum + Number(item.remaining_amount), 0);
        const avgDays = reportData.length > 0
          ? Math.round(reportData.reduce((sum, item) => sum + Number(item.days_overdue), 0) / reportData.length)
          : 0;
        setSummary({ count: reportData.length, total, avgDays });
      } else {
        throw new Error(apiMessage(dataRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [daysOverdue, branchId]);

  async function sendReminders() {
    setSending(true);
    try {
      await api.post("/reports/overdue-debts/remind", {
        debt_ids: data.map((d) => d.id)
      });
      showToast("Hatırlatmalar gönderildi", "Velilere borç hatırlatma bildirimleri gönderildi.");
    } catch (err) {
      showToast("Hatırlatmalar gönderilemedi", apiMessage(err), "error");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Finans raporları"
        title="Gecikmiş Borçlar"
        description="Vadesi geçmiş borçlar ve veli hatırlatmaları."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv("gecikmis-borclar", data)} disabled={!data.length}>
          <Download size={16} />Dışa aktar
        </button>
        {data.length > 0 && (
          <button className="btn btn-primary" onClick={sendReminders} disabled={sending}>
            {sending ? <><Bell size={16} className="spin" />Gönderiliyor...</> : <><Send size={16} />Hatırlatma gönder</>}
          </button>
        )}
      </PageHeader>

      <div className="card">
        <div className="toolbar">
          <select
            className="filter-select"
            value={daysOverdue}
            onChange={(e) => setDaysOverdue(e.target.value)}
          >
            <option value="7">7+ gün gecikmiş</option>
            <option value="30">30+ gün gecikmiş</option>
            <option value="60">60+ gün gecikmiş</option>
            <option value="90">90+ gün gecikmiş</option>
          </select>
          <select
            className="filter-select"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
          >
            <option value="">Tüm şubeler</option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} retry={load} />
        ) : (
          <>
            <div className="grid stats-grid" style={{ marginBottom: 18 }}>
              <StatCard icon={<AlertTriangle size={19} />} label="Gecikmiş borç" value={summary.count} color="red" />
              <StatCard icon={<AlertTriangle size={19} />} label="Toplam tutar" value={money(summary.total)} color="orange" />
              <StatCard icon={<AlertTriangle size={19} />} label="Ortalama gecikme" value={`${summary.avgDays} gün`} color="red" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                <AlertTriangle size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
                <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Gecikmiş borç yok</h3>
                <p>Seçili kriterlere uygun gecikmiş borç kaydı bulunmuyor.</p>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Öğrenci</th>
                      <th>Şube</th>
                      <th>Kalan borç</th>
                      <th>Vade</th>
                      <th>Gecikme</th>
                      <th>Veli iletişim</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item) => (
                      <tr key={item.id}>
                        <td>{item.student_name}</td>
                        <td>{item.branch_name || "-"}</td>
                        <td style={{ color: "#b14545", fontWeight: 600 }}>{money(item.remaining_amount)}</td>
                        <td>{item.due_date}</td>
                        <td>
                          <span style={{ color: "#b14545", fontWeight: 600 }}>
                            {item.days_overdue} gün
                          </span>
                        </td>
                        <td>
                          <div style={{ fontSize: 12 }}>
                            {item.parent_phone && <div>{item.parent_phone}</div>}
                            {item.parent_email && <div>{item.parent_email}</div>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

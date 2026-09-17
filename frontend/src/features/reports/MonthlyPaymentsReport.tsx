import { Calendar, Download, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { money, monthInputValue } from "../../lib/format";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface MonthlyData {
  month: string;
  year: string;
  total_amount: number;
  payment_count: number;
  branch_name?: string;
}

export function MonthlyPaymentsReport() {
  const [month, setMonth] = useState(monthInputValue());
  const [branchId, setBranchId] = useState("");
  const [branches, setBranches] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<MonthlyData[]>([]);
  const [summary, setSummary] = useState({ total: 0, count: 0, avg: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [branchesRes, dataRes] = await Promise.allSettled([
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/branches", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<MonthlyData[] | Paginated<MonthlyData>>>("/reports/monthly-payments", {
          params: { year: Number(month.slice(0, 4)), month: Number(month.slice(5, 7)), branch_id: branchId || undefined }
        })
      ]);

      if (branchesRes.status === "fulfilled") {
        setBranches(toArray(branchesRes.value.data.data));
      }

      if (dataRes.status === "fulfilled") {
        const reportData = toArray(dataRes.value.data.data);
        setData(reportData);
        const total = reportData.reduce((sum, item) => sum + Number(item.total_amount), 0);
        const count = reportData.reduce((sum, item) => sum + Number(item.payment_count), 0);
        setSummary({
          total,
          count,
          avg: count > 0 ? Math.round(total / count) : 0
        });
      } else {
        throw new Error(apiMessage(dataRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [month, branchId]);

  return (
    <>
      <PageHeader
        eyebrow="Finans raporları"
        title="Aylık Ödeme Raporu"
        description="Seçili aydaki ödeme tahsilatları ve istatistikler."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv(`aylik-odeme-${month}`, data)} disabled={!data.length}>
          <Download size={16} />Dışa aktar
        </button>
      </PageHeader>

      <div className="card">
        <div className="toolbar">
          <div className="search" style={{ maxWidth: 200 }}>
            <Calendar size={16} />
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            />
          </div>
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
              <StatCard icon={<TrendingUp size={19} />} label="Toplam tahsilat" value={money(summary.total)} color="green" />
              <StatCard icon={<Calendar size={19} />} label="Ödeme sayısı" value={summary.count} color="blue" />
              <StatCard icon={<TrendingUp size={19} />} label="Ortalama tutar" value={money(summary.avg)} color="orange" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                Bu dönem için ödeme kaydı bulunmuyor.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Ay</th>
                      <th>Şube</th>
                      <th>Toplam tutar</th>
                      <th>Ödeme sayısı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item, index) => (
                      <tr key={index}>
                        <td>{item.month}</td>
                        <td>{item.branch_name || "-"}</td>
                        <td>{money(item.total_amount)}</td>
                        <td>{item.payment_count}</td>
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

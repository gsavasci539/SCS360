import { AlertTriangle, Calendar, Download, Filter } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { money } from "../../lib/format";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface DebtData {
  id: string;
  student_name: string;
  amount: number;
  paid_amount: number;
  remaining_amount: number;
  due_date: string;
  status: string;
  type: string;
  branch_name?: string;
}

export function DebtReport() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [branchId, setBranchId] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [branches, setBranches] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<DebtData[]>([]);
  const [summary, setSummary] = useState({ total: 0, paid: 0, remaining: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [branchesRes, dataRes] = await Promise.allSettled([
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/branches", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<DebtData[] | Paginated<DebtData>>>("/reports/debts", {
          params: {
            start_date: startDate || undefined,
            end_date: endDate || undefined,
            branch_id: branchId || undefined,
            status: status || undefined,
            type: type || undefined
          }
        })
      ]);

      if (branchesRes.status === "fulfilled") {
        setBranches(toArray(branchesRes.value.data.data));
      }

      if (dataRes.status === "fulfilled") {
        const reportData = toArray(dataRes.value.data.data);
        setData(reportData);
        const total = reportData.reduce((sum, item) => sum + Number(item.amount), 0);
        const paid = reportData.reduce((sum, item) => sum + Number(item.paid_amount), 0);
        const remaining = reportData.reduce((sum, item) => sum + Number(item.remaining_amount), 0);
        setSummary({ total, paid, remaining });
      } else {
        throw new Error(apiMessage(dataRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [startDate, endDate, branchId, status, type]);

  return (
    <>
      <PageHeader
        eyebrow="Finans raporları"
        title="Borç Raporu"
        description="Borç durumları, ödemeler ve kalan bakiyeler."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv("borc-raporu", data)} disabled={!data.length}>
          <Download size={16} />Dışa aktar
        </button>
      </PageHeader>

      <div className="card">
        <div className="toolbar">
          <div className="search" style={{ maxWidth: 160 }}>
            <Calendar size={16} />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              placeholder="Başlangıç"
            />
          </div>
          <div className="search" style={{ maxWidth: 160 }}>
            <Calendar size={16} />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              placeholder="Bitiş"
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
          <select
            className="filter-select"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">Tüm durumlar</option>
            <option value="PENDING">Bekleyen</option>
            <option value="PARTIAL">Kısmi ödenen</option>
            <option value="PAID">Ödenen</option>
            <option value="OVERDUE">Gecikmiş</option>
          </select>
          <select
            className="filter-select"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="">Tüm türler</option>
            <option value="TUITION">Öğretim ücreti</option>
            <option value="MATERIAL">Materyal</option>
            <option value="ACTIVITY">Etkinlik</option>
            <option value="OTHER">Diğer</option>
          </select>
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} retry={load} />
        ) : (
          <>
            <div className="grid stats-grid" style={{ marginBottom: 18 }}>
              <StatCard icon={<AlertTriangle size={19} />} label="Toplam borç" value={money(summary.total)} color="red" />
              <StatCard icon={<Filter size={19} />} label="Ödenen" value={money(summary.paid)} color="green" />
              <StatCard icon={<AlertTriangle size={19} />} label="Kalan" value={money(summary.remaining)} color="orange" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                Belirtilen kriterlere uygun borç kaydı bulunmuyor.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Öğrenci</th>
                      <th>Şube</th>
                      <th>Tür</th>
                      <th>Toplam</th>
                      <th>Ödenen</th>
                      <th>Kalan</th>
                      <th>Vade</th>
                      <th>Durum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item) => (
                      <tr key={item.id}>
                        <td>{item.student_name}</td>
                        <td>{item.branch_name || "-"}</td>
                        <td>{item.type}</td>
                        <td>{money(item.amount)}</td>
                        <td>{money(item.paid_amount)}</td>
                        <td>{money(item.remaining_amount)}</td>
                        <td>{item.due_date}</td>
                        <td><Badge value={item.status} /></td>
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

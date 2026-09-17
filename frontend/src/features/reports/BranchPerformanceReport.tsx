import { Building2, Calendar, CalendarCheck2, Download, TrendingUp, Wallet } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { money } from "../../lib/format";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface BranchPerformanceData {
  branch_id: string;
  branch_name: string;
  total_students: number;
  total_revenue: number;
  attendance_rate: number;
  new_students: number;
  period_start: string;
  period_end: string;
}

export function BranchPerformanceReport() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [data, setData] = useState<BranchPerformanceData[]>([]);
  const [summary, setSummary] = useState({ totalStudents: 0, totalRevenue: 0, avgAttendance: 0, newStudents: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const dataRes = await api.get<ApiResponse<BranchPerformanceData[] | Paginated<BranchPerformanceData>>>("/reports/branch-performance", {
        params: {
          start_date: startDate || undefined,
          end_date: endDate || undefined
        }
      });

      if (dataRes.status === 200) {
        const reportData = toArray(dataRes.data.data);
        setData(reportData);
        const totalStudents = reportData.reduce((sum, item) => sum + Number(item.total_students), 0);
        const totalRevenue = reportData.reduce((sum, item) => sum + Number(item.total_revenue), 0);
        const avgAttendance = reportData.length > 0
          ? Math.round(reportData.reduce((sum, item) => sum + Number(item.attendance_rate), 0) / reportData.length)
          : 0;
        const newStudents = reportData.reduce((sum, item) => sum + Number(item.new_students), 0);
        setSummary({ totalStudents, totalRevenue, avgAttendance, newStudents });
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [startDate, endDate]);

  return (
    <>
      <PageHeader
        eyebrow="Şube raporları"
        title="Şube Performans Raporu"
        description="Şubelerin gelir, öğrenci ve yoklama performansları."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv("sube-performans-raporu", data)} disabled={!data.length}>
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
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} retry={load} />
        ) : (
          <>
            <div className="grid stats-grid" style={{ marginBottom: 18 }}>
              <StatCard icon={<Building2 size={19} />} label="Toplam öğrenci" value={summary.totalStudents} color="blue" />
              <StatCard icon={<Wallet size={19} />} label="Toplam gelir" value={money(summary.totalRevenue)} color="green" />
              <StatCard icon={<CalendarCheck2 size={19} />} label="Ortalama katılım" value={`${summary.avgAttendance}%`} color="orange" />
              <StatCard icon={<TrendingUp size={19} />} label="Yeni öğrenci" value={summary.newStudents} color="green" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                <Building2 size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
                <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Veri yok</h3>
                <p>Seçili dönem için performans verisi bulunmuyor.</p>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Şube</th>
                      <th>Öğrenci sayısı</th>
                      <th>Gelir</th>
                      <th>Katılım oranı</th>
                      <th>Yeni öğrenci</th>
                      <th>Dönem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item) => (
                      <tr key={item.branch_id}>
                        <td>
                          <div style={{ font: "600 14px Manrope" }}>{item.branch_name}</div>
                        </td>
                        <td>{item.total_students}</td>
                        <td>{money(item.total_revenue)}</td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ flex: 1, height: 6, background: "#e7ece8", borderRadius: 3, overflow: "hidden" }}>
                              <div
                                style={{
                                  height: "100%",
                                  width: `${item.attendance_rate}%`,
                                  background: item.attendance_rate >= 80 ? "#2d8f78" : item.attendance_rate >= 60 ? "#ad7020" : "#b14545"
                                }}
                              />
                            </div>
                            <span style={{ fontSize: 12, minWidth: 35 }}>{item.attendance_rate}%</span>
                          </div>
                        </td>
                        <td>
                          <span style={{ color: item.new_students > 0 ? "#176b5b" : "#7a8888", fontWeight: item.new_students > 0 ? 600 : 400 }}>
                            {item.new_students > 0 ? `+${item.new_students}` : item.new_students}
                          </span>
                        </td>
                        <td style={{ fontSize: 12 }}>
                          {item.period_start} - {item.period_end}
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

import { Calendar, CalendarCheck2, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { monthInputValue } from "../../lib/format";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface MonthlyAttendanceData {
  date: string;
  class_name: string;
  total_students: number;
  present: number;
  absent: number;
  excused: number;
  late: number;
  half_day: number;
  attendance_rate: number;
}

export function MonthlyAttendanceReport() {
  const [month, setMonth] = useState(monthInputValue());
  const [classId, setClassId] = useState("");
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<MonthlyAttendanceData[]>([]);
  const [summary, setSummary] = useState({ totalDays: 0, avgRate: 0, totalPresent: 0, totalAbsent: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [classesRes, dataRes] = await Promise.allSettled([
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/classes", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<MonthlyAttendanceData[] | Paginated<MonthlyAttendanceData>>>("/attendance/reports/monthly", {
          params: { year: Number(month.slice(0, 4)), month: Number(month.slice(5, 7)), class_id: classId || undefined }
        })
      ]);

      if (classesRes.status === "fulfilled") {
        setClasses(toArray(classesRes.value.data.data));
      }

      if (dataRes.status === "fulfilled") {
        const reportData = toArray(dataRes.value.data.data);
        setData(reportData);
        const totalDays = reportData.length;
        const avgRate = totalDays > 0
          ? Math.round(reportData.reduce((sum, item) => sum + Number(item.attendance_rate), 0) / totalDays)
          : 0;
        const totalPresent = reportData.reduce((sum, item) => sum + Number(item.present), 0);
        const totalAbsent = reportData.reduce((sum, item) => sum + Number(item.absent), 0);
        setSummary({ totalDays, avgRate, totalPresent, totalAbsent });
      } else {
        throw new Error(apiMessage(dataRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [month, classId]);

  return (
    <>
      <PageHeader
        eyebrow="Yoklama raporları"
        title="Aylık Yoklama Raporu"
        description="Seçili aydaki yoklama istatistikleri ve detaylar."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv(`aylik-yoklama-${month}`, data)} disabled={!data.length}>
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
              aria-label="Rapor ayı"
            />
          </div>
          <select
            className="filter-select"
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
            aria-label="Sınıf filtresi"
          >
            <option value="">Tüm sınıflar</option>
            {classes.map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.name}
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
              <StatCard icon={<Calendar size={19} />} label="Rapor günü" value={summary.totalDays} color="blue" />
              <StatCard icon={<CalendarCheck2 size={19} />} label="Ortalama katılım" value={`${summary.avgRate}%`} color="green" />
              <StatCard icon={<CalendarCheck2 size={19} />} label="Toplam geldi" value={summary.totalPresent} color="green" />
              <StatCard icon={<Calendar size={19} />} label="Toplam gelmedi" value={summary.totalAbsent} color="red" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                Bu dönem için yoklama kaydı bulunmuyor.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tarih</th>
                      <th>Sınıf</th>
                      <th>Toplam</th>
                      <th>Geldi</th>
                      <th>Gelmedi</th>
                      <th>İzinli</th>
                      <th>Geç</th>
                      <th>Yarım</th>
                      <th>Oran</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item, index) => (
                      <tr key={index}>
                        <td>{item.date}</td>
                        <td>{item.class_name}</td>
                        <td>{item.total_students}</td>
                        <td>{item.present}</td>
                        <td>{item.absent}</td>
                        <td>{item.excused}</td>
                        <td>{item.late}</td>
                        <td>{item.half_day}</td>
                        <td>
                          <Badge value={item.attendance_rate >= 80 ? "GOOD" : item.attendance_rate >= 60 ? "WARNING" : "CRITICAL"} />
                          <span style={{ marginLeft: 8 }}>{item.attendance_rate}%</span>
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

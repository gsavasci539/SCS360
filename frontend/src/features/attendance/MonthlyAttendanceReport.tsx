import { Calendar, CalendarCheck2, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { monthInputValue } from "../../lib/format";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface MonthlyAttendanceData {
  date: string;
  class_id: string;
  class_name: string | null;
  total_students: number;
  present: number;
  absent: number;
  excused: number;
  late: number;
  half_day: number;
}

interface MonthlyAttendanceResponse {
  year: number;
  month: number;
  class_id: string | null;
  total: number;
  rows: MonthlyAttendanceData[];
}

const presentRate = (count: number, total: number) => total ? `${Math.round((count / total) * 100)}%` : "—";

export function MonthlyAttendanceReport() {
  const [month, setMonth] = useState(monthInputValue());
  const [classId, setClassId] = useState("");
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<MonthlyAttendanceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setData([]);
    setError("");
    const year = Number(month.slice(0, 4));
    const monthNumber = Number(month.slice(5, 7));
    (async () => {
      try {
        if (!/^\d{4}-\d{2}$/.test(month)) throw new Error("Rapor ayını seçin.");
        const [classesRes, dataRes] = await Promise.allSettled([
          api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/classes", {
            params: { page_size: 100 }, signal: controller.signal,
          }),
          api.get<ApiResponse<MonthlyAttendanceResponse>>("/attendance/reports/monthly", {
            params: { year, month: monthNumber, class_id: classId || undefined }, signal: controller.signal,
          }),
        ]);
        if (controller.signal.aborted) return;
        if (classesRes.status === "fulfilled") setClasses(toArray(classesRes.value.data.data));
        if (dataRes.status === "rejected") throw dataRes.reason;
        const report = dataRes.value.data.data;
        if (dataRes.value.data.success !== true || report?.year !== year || report.month !== monthNumber ||
          report.class_id !== (classId || null) || !Array.isArray(report.rows) ||
          report.rows.some((row) => !row?.class_id || (classId && row.class_id !== classId) || !row.date?.startsWith(`${month}-`) ||
            [row.present, row.absent, row.excused, row.late, row.half_day].some((value) => !Number.isInteger(value) || value < 0) ||
            row.total_students !== row.present + row.absent + row.excused + row.late + row.half_day) ||
          report.total !== report.rows.reduce((sum, row) => sum + row.total_students, 0)) {
          throw new Error("Yoklama raporu doğrulanamadı.");
        }
        setData(report.rows);
      } catch (reason) {
        if (!controller.signal.aborted) setError(apiMessage(reason));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [month, classId, revision]);

  const total = data.reduce((sum, row) => sum + row.total_students, 0);
  const totalPresent = data.reduce((sum, row) => sum + row.present, 0);
  const totalAbsent = data.reduce((sum, row) => sum + row.absent, 0);
  const totalDays = new Set(data.map((row) => row.date)).size;

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
          <ErrorState message={error} retry={() => setRevision((value) => value + 1)} />
        ) : (
          <>
            <div className="grid stats-grid" style={{ marginBottom: 18 }}>
              <StatCard icon={<Calendar size={19} />} label="Kayıt bulunan gün" value={totalDays} color="blue" />
              <StatCard icon={<CalendarCheck2 size={19} />} label="Geldi oranı" value={presentRate(totalPresent, total)} color="green" />
              <StatCard icon={<CalendarCheck2 size={19} />} label="Toplam geldi" value={totalPresent} color="green" />
              <StatCard icon={<Calendar size={19} />} label="Toplam gelmedi" value={totalAbsent} color="red" />
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
                      <th>Geldi oranı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item) => (
                      <tr key={`${item.date}-${item.class_id}`}>
                        <td>{item.date}</td>
                        <td>{item.class_name || "Sınıf adı bulunamadı"}</td>
                        <td>{item.total_students}</td>
                        <td>{item.present}</td>
                        <td>{item.absent}</td>
                        <td>{item.excused}</td>
                        <td>{item.late}</td>
                        <td>{item.half_day}</td>
                        <td>{presentRate(item.present, item.total_students)}</td>
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

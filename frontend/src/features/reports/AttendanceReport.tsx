import { Calendar, CalendarCheck2, Download, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface AttendanceData {
  date: string;
  student_id: string;
  student_name: string;
  class_name: string;
  status: string;
  branch_name?: string;
}

export function AttendanceReport() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [classId, setClassId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [students, setStudents] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<AttendanceData[]>([]);
  const [summary, setSummary] = useState({ present: 0, absent: 0, excused: 0, late: 0, rate: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [classesRes, studentsRes, dataRes] = await Promise.allSettled([
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/classes", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/students", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<AttendanceData[] | Paginated<AttendanceData>>>("/reports/attendance", {
          params: {
            start_date: startDate || undefined,
            end_date: endDate || undefined,
            class_id: classId || undefined,
            student_id: studentId || undefined
          }
        })
      ]);

      if (classesRes.status === "fulfilled") {
        setClasses(toArray(classesRes.value.data.data));
      }

      if (studentsRes.status === "fulfilled") {
        setStudents(toArray(studentsRes.value.data.data));
      }

      if (dataRes.status === "fulfilled") {
        const reportData = toArray(dataRes.value.data.data);
        setData(reportData);
        const present = reportData.filter((d) => d.status === "PRESENT").length;
        const absent = reportData.filter((d) => d.status === "ABSENT").length;
        const excused = reportData.filter((d) => d.status === "EXCUSED").length;
        const late = reportData.filter((d) => d.status === "LATE").length;
        const rate = reportData.length > 0 ? Math.round((present / reportData.length) * 100) : 0;
        setSummary({ present, absent, excused, late, rate });
      } else {
        throw new Error(apiMessage(dataRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [startDate, endDate, classId, studentId]);

  return (
    <>
      <PageHeader
        eyebrow="Yoklama raporları"
        title="Devamsızlık Raporu"
        description="Yoklama kayıtları ve istatistikleri."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv("devamsizlik-raporu", data)} disabled={!data.length}>
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
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
          >
            <option value="">Tüm sınıflar</option>
            {classes.map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.name}
              </option>
            ))}
          </select>
          <select
            className="filter-select"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
          >
            <option value="">Tüm öğrenciler</option>
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.name}
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
              <StatCard icon={<TrendingUp size={19} />} label="Katılım oranı" value={`${summary.rate}%`} color="green" />
              <StatCard icon={<CalendarCheck2 size={19} />} label="Geldi" value={summary.present} color="green" />
              <StatCard icon={<Calendar size={19} />} label="Gelmedi" value={summary.absent} color="red" />
              <StatCard icon={<Calendar size={19} />} label="İzinli" value={summary.excused} color="orange" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                Belirtilen kriterlere uygun yoklama kaydı bulunmuyor.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tarih</th>
                      <th>Öğrenci</th>
                      <th>Sınıf</th>
                      <th>Şube</th>
                      <th>Durum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item, index) => (
                      <tr key={index}>
                        <td>{item.date}</td>
                        <td>{item.student_name}</td>
                        <td>{item.class_name}</td>
                        <td>{item.branch_name || "-"}</td>
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

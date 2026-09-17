import { ArrowLeft, Calendar, CalendarCheck2, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, StatCard, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { textValue, toArray } from "../../lib/data";
import { dateInputValue, shortDate } from "../../lib/format";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

interface AttendanceRecord {
  id: string;
  date: string;
  attendance_date?: string;
  status: string;
  notes?: string;
}

export function StudentAttendancePage() {
  const { id } = useParams();
  const [student, setStudent] = useState<DataRecord | null>(null);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentMonth, setCurrentMonth] = useState(new Date());

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [studentRes, attendanceRes] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord>>(`/students/${id}`),
        api.get<ApiResponse<AttendanceRecord[] | Paginated<AttendanceRecord>>>(`/students/${id}/attendance`, {
          params: {
            start_date: dateInputValue(new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1)),
            end_date: dateInputValue(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0))
          }
        })
      ]);

      if (studentRes.status === "fulfilled") {
        setStudent(studentRes.value.data.data);
      } else {
        throw new Error(apiMessage(studentRes.reason));
      }

      if (attendanceRes.status === "fulfilled") {
        setAttendance(toArray(attendanceRes.value.data.data).map((record) => ({ ...record, date: record.date || record.attendance_date || "" })));
      } else {
        throw new Error(apiMessage(attendanceRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id, currentMonth]);

  const stats = {
    present: attendance.filter((a) => a.status === "PRESENT").length,
    absent: attendance.filter((a) => a.status === "ABSENT").length,
    excused: attendance.filter((a) => a.status === "EXCUSED").length,
    late: attendance.filter((a) => a.status === "LATE").length,
    halfDay: attendance.filter((a) => a.status === "HALF_DAY").length
  };

  const attendanceRate = attendance.length > 0
    ? Math.round((stats.present / attendance.length) * 100)
    : 0;

  function changeMonth(delta: number) {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + delta, 1));
  }

  if (loading) return <div className="card"><LoadingState label="Devamsızlık verileri yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={load} /></div>;

  const studentName = [student?.first_name, student?.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ");
  const monthName = currentMonth.toLocaleDateString("tr-TR", { month: "long", year: "numeric" });

  return (
    <>
      <PageHeader
        eyebrow="Devamsızlık geçmişi"
        title={studentName || "Öğrenci"}
        description={`${monthName} dönemi yoklama kayıtları ve istatistikleri.`}
      >
        <Link className="btn btn-secondary" to={`/students/${id}`}>
          <ArrowLeft size={16} />Öğrenciye dön
        </Link>
      </PageHeader>

      <div className="grid stats-grid">
        <StatCard icon={<CalendarCheck2 size={19} />} label="Katılım oranı" value={`${attendanceRate}%`} meta={`${attendance.length} gün kayıt`} color="green" />
        <StatCard icon={<CalendarCheck2 size={19} />} label="Geldi" value={stats.present} meta="Tam gün" color="green" />
        <StatCard icon={<Calendar size={19} />} label="Gelmedi" value={stats.absent} meta="Devamsız" color="red" />
        <StatCard icon={<Calendar size={19} />} label="İzinli" value={stats.excused} meta="Mazeretli" color="orange" />
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="toolbar">
          <button className="btn btn-ghost" onClick={() => changeMonth(-1)} aria-label="Önceki ay">
            <ChevronLeft size={16} />
          </button>
          <span style={{ font: "600 14px Manrope", minWidth: 150, textAlign: "center" }}>
            {monthName.charAt(0).toUpperCase() + monthName.slice(1)}
          </span>
          <button className="btn btn-ghost" onClick={() => changeMonth(1)} aria-label="Sonraki ay">
            <ChevronRight size={16} />
          </button>
        </div>

        {attendance.length === 0 ? (
          <div style={{ padding: "40px 20px", textAlign: "center" }}>
            <Calendar size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
            <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Bu dönemde yoklama kaydı yok</h3>
            <p style={{ color: "#7a8888", fontSize: 13 }}>Seçili dönem için devamsızlık verisi bulunamadı.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tarih</th>
                  <th>Durum</th>
                  <th>Not</th>
                </tr>
              </thead>
              <tbody>
                {[...attendance].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).map((record) => (
                  <tr key={record.id}>
                    <td>{shortDate(record.date)}</td>
                    <td><Badge value={record.status} /></td>
                    <td>{record.notes || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

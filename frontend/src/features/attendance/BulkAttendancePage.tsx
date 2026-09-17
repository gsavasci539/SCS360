import { CalendarDays, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { dateInputValue } from "../../lib/format";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

const statuses = [
  { value: "PRESENT", label: "Geldi" },
  { value: "ABSENT", label: "Gelmedi" },
  { value: "EXCUSED", label: "İzinli" },
  { value: "LATE", label: "Geç geldi" },
  { value: "HALF_DAY", label: "Yarım gün" }
];

const today = dateInputValue();
const items = (data: DataRecord[] | Paginated<DataRecord>) => Array.isArray(data) ? data : data?.items || [];

export function BulkAttendancePage() {
  const [classes, setClasses] = useState<DataRecord[]>([]);
  const [students, setStudents] = useState<DataRecord[]>([]);
  const [classId, setClassId] = useState("");
  const [date, setDate] = useState(today);
  const [records, setRecords] = useState<Record<string, { status: string; notes: string }>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { showToast } = useToast();

  useEffect(() => {
    api
      .get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/classes", {
        params: { limit: 100, page_size: 100 }
      })
      .then((r) => {
        const list = items(r.data.data);
        setClasses(list);
        if (list[0]) setClassId(list[0].id);
      })
      .catch((e) => setError(apiMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!classId) return;
    setLoading(true);
    api
      .get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/students", {
        params: { class_id: classId, limit: 100, page_size: 100 }
      })
      .then((r) => {
        const list = items(r.data.data);
        setStudents(list);
        setRecords(
          Object.fromEntries(
            list.map((student) => [
              student.id,
              { status: "PRESENT", notes: "" }
            ])
          )
        );
      })
      .catch((e) => setError(apiMessage(e)))
      .finally(() => setLoading(false));
  }, [classId]);

  async function save() {
    setSaving(true);
    try {
      await api.post("/attendance/bulk", {
        class_id: classId,
        attendance_date: date,
        records: students.map((student) => ({
          student_id: student.id,
          status: records[student.id]?.status || "PRESENT",
          notes: records[student.id]?.notes || ""
        }))
      });
      showToast("Yoklama kaydedildi", `${students.length} öğrencinin durumu işlendi.`);
    } catch (e) {
      showToast("Yoklama kaydedilemedi", apiMessage(e), "error");
    } finally {
      setSaving(false);
    }
  }

  function updateRecord(studentId: string, field: "status" | "notes", value: string) {
    setRecords((current) => ({
      ...current,
      [studentId]: { ...current[studentId], [field]: value }
    }));
  }

  return (
    <>
      <PageHeader
        eyebrow="Toplu yoklama"
        title="Yoklama"
        description="Tablo görünümünde toplu yoklama girişi."
      >
        <button
          className="btn btn-primary"
          onClick={save}
          disabled={!students.length || saving}
        >
          <Save size={16} />
          {saving ? "Kaydediliyor..." : "Yoklamayı kaydet"}
        </button>
      </PageHeader>

      <div className="card">
        <div className="toolbar">
          <select
            className="filter-select"
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
            aria-label="Sınıf seç"
          >
            <option value="">Sınıf seçin</option>
            {classes.map((item) => (
              <option value={item.id} key={item.id}>
                {String(item.name)}
              </option>
            ))}
          </select>
          <div className="search" style={{ maxWidth: 180 }}>
            <CalendarDays size={16} />
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              aria-label="Yoklama tarihi"
            />
          </div>
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : !classId ? (
          <EmptyState title="Önce bir sınıf seçin" />
        ) : students.length === 0 ? (
          <EmptyState
            title="Bu sınıfta öğrenci yok"
            description="Sınıfa öğrenci atadıktan sonra yoklama alabilirsiniz."
          />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Durum</th>
                  <th>Not</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <div className="cell-main">
                        {String(student.first_name)} {String(student.last_name)}
                      </div>
                      <div className="cell-sub">
                        {String(student.student_number || "Öğrenci kaydı")}
                      </div>
                    </td>
                    <td>
                      <select
                        className="filter-select"
                        value={records[student.id]?.status || "PRESENT"}
                        onChange={(e) =>
                          updateRecord(student.id, "status", e.target.value)
                        }
                      >
                        {statuses.map((status) => (
                          <option key={status.value} value={status.value}>
                            {status.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="text"
                        className="filter-select"
                        placeholder="Not ekle"
                        value={records[student.id]?.notes || ""}
                        onChange={(e) =>
                          updateRecord(student.id, "notes", e.target.value)
                        }
                      />
                    </td>
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

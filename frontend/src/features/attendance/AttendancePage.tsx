import { canAnalyze, getAnalysis } from "../../lib/analysis";
import { CalendarDays, Check, Save } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { dateInputValue } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { RecordedAttendancePanel, type RecordedAttendanceSummary } from "./RecordedAttendancePanel";

const statuses = [{ value: "PRESENT", label: "Geldi" }, { value: "ABSENT", label: "Gelmedi" }, { value: "EXCUSED", label: "İzinli" }, { value: "LATE", label: "Geç geldi" }, { value: "HALF_DAY", label: "Yarım gün" }];
const today = dateInputValue();
type EditRow = { status: string; notes: string | null; version: string | null };
type BatchBody = { request_id: string; class_id: string; attendance_date: string;
  records: Array<{ student_id: string; status: string; notes: string | null; expected_version: string | null }> };
async function allPages(path: string, params: Record<string, string | number>, signal: AbortSignal): Promise<DataRecord[]> {
  const result: DataRecord[] = [];
  for (let page = 1; page <= 10000; page++) {
    const response = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(path,
      { params: { ...params, page, page_size: 100, limit: 100 }, signal });
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    const data = response.data.data;
    if (Array.isArray(data)) return data;
    if (!data || !Array.isArray(data.items)) throw new Error("Kayıt listesi okunamadı");
    result.push(...data.items);
    if (page >= data.total_pages || result.length >= data.total) return result;
  }
  throw new Error("Liste tamamlanamadı; kayıt işlemi açılmadı");
}

export function AttendancePage() {
  const [classes, setClasses] = useState<DataRecord[]>([]); 
  const [students, setStudents] = useState<DataRecord[]>([]); 
  const [classId, setClassId] = useState(""); 
  const [date, setDate] = useState(today); 
  const [records, setRecords] = useState<Record<string, EditRow>>({});
  const [loading, setLoading] = useState(true); 
  const [saving, setSaving] = useState(false);
  const [snapshotKey, setSnapshotKey] = useState<string | null>(null);
  const [retryPending, setRetryPending] = useState(false);
  const pendingSave = useRef<BatchBody | null>(null);
  const rosterRequest = useRef<AbortController | null>(null);
  const classesRequest = useRef<AbortController | null>(null);
  const scopeKey = `${classId}|${date}`;
  const [error, setError] = useState(""); 
  const [aiAnalysis, setAiAnalysis] = useState<RecordedAttendanceSummary | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const analysisRequest = useRef<AbortController | null>(null);
  const canViewAnalysis = canAnalyze("/ai/attendance-analysis");
  const { showToast } = useToast(); 
  const canWrite = useAuthStore((state) => state.can("attendance.write"));

  async function loadClasses() {
    classesRequest.current?.abort();
    const controller = new AbortController();
    classesRequest.current = controller;
    setLoading(true); setError("");
    try {
      const list = await allPages("/classes", {}, controller.signal);
      if (controller.signal.aborted) return;
      setClasses(list);
      setClassId(current => list.some(row => row.id === current) ? current : list[0]?.id || "");
    } catch (e) { if (!controller.signal.aborted) setError(apiMessage(e)); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  useEffect(() => {
    void loadClasses();
    return () => classesRequest.current?.abort();
  }, []);

  async function loadRoster(selectedClass = classId, selectedDate = date) {
    rosterRequest.current?.abort();
    const controller = new AbortController();
    rosterRequest.current = controller;
    setSnapshotKey(null);
    setError("");
    if (!selectedClass) { setStudents([]); setRecords({}); setLoading(false); return; }
    setLoading(true);
    try {
      const [roster, history] = await Promise.all([
        allPages("/students", { class_id: selectedClass }, controller.signal),
        allPages("/attendance", { class_id: selectedClass, attendance_date: selectedDate }, controller.signal),
      ]);
      if (controller.signal.aborted) return;
      const pupils = new Map(roster.map((row) => [row.id, row]));
      const loaded: Record<string, EditRow> = Object.fromEntries(roster.map((row) => [row.id, { status: "PRESENT", notes: null, version: null }]));
      for (const row of history) {
        const studentId = String(row.student_id);
        if (typeof row.version !== "string" || !/^[0-9a-f]{64}$/.test(row.version) || !statuses.some((item) => item.value === row.status)) {
          throw new Error("Yoklama durum veya sürüm bilgisi okunamadı");
        }
        if (!pupils.has(studentId)) pupils.set(studentId, { id: studentId, first_name: row.first_name || "Öğrenci", last_name: row.last_name || "" });
        loaded[studentId] = { status: String(row.status), notes: row.notes == null ? null : String(row.notes), version: row.version };
      }
      setStudents([...pupils.values()]);
      setRecords(loaded);
      pendingSave.current = null;
      setRetryPending(false);
      setSnapshotKey(`${selectedClass}|${selectedDate}`);
    } catch (e) {
      if (!controller.signal.aborted) setError(apiMessage(e));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  useEffect(() => {
    void loadRoster();
    return () => rosterRequest.current?.abort();
  }, [classId, date]);

  async function loadAnalysis() {
    analysisRequest.current?.abort();
    const controller = new AbortController();
    analysisRequest.current = controller;
    setAiAnalysis(null);
    setAnalysisError("");
    if (!canViewAnalysis) return;
    try {
      const response = await getAnalysis("/ai/attendance-analysis", { signal: controller.signal });
      if (!controller.signal.aborted && response.data.success && response.data.data) setAiAnalysis(response.data.data);
    } catch (e) {
      if (!controller.signal.aborted) setAnalysisError(apiMessage(e));
    }
  }
  useEffect(() => {
    loadAnalysis();
    return () => analysisRequest.current?.abort();
  }, [canViewAnalysis]);

  const counts = useMemo(() => statuses.map((status) => ({ ...status, count: Object.values(records).filter((value) => value.status === status.value).length })), [records]);

  async function save() {
    if (!canWrite || saving || loading || snapshotKey !== scopeKey || !students.length) return;
    const body = pendingSave.current ?? {
      request_id: crypto.randomUUID(), class_id: classId, attendance_date: date,
      records: students.map((student) => ({ student_id: student.id, status: records[student.id].status,
        notes: records[student.id].notes, expected_version: records[student.id].version })),
    };
    pendingSave.current = body;
    setSaving(true);
    try {
      const response = await api.put<ApiResponse<{ created: number; updated: number; unchanged: number }>>("/attendance/bulk", body);
      const result = response.data.data;
      pendingSave.current = null;
      setRetryPending(false);
      showToast("Yoklama kaydedildi", `${result.created} yeni, ${result.updated} güncellenen, ${result.unchanged} değişmeyen kayıt.`);
      await loadRoster(body.class_id, body.attendance_date);
      void loadAnalysis();
    } catch (e) {
      const status = (e as { response?: { status?: number } }).response?.status;
      if (status && status >= 400 && status < 500) {
        pendingSave.current = null;
        setRetryPending(false);
        setSnapshotKey(null);
        setError(apiMessage(e));
      } else {
        setRetryPending(true);
      }
      showToast("Yoklama kaydedilemedi", apiMessage(e), "error");
    } finally { setSaving(false); }
  }
  const fieldsLocked = !canWrite || saving || loading || retryPending || snapshotKey !== scopeKey;

  return (
    <>
      <PageHeader eyebrow="Günlük akış" title="Yoklama" description="Sınıfı ve tarihi seçin, öğrenci durumlarını tek ekrandan kaydedin.">
        {canWrite && (
          <button className="btn btn-primary" onClick={save} disabled={!students.length || saving || loading || snapshotKey !== scopeKey}>
            <Save size={16} />
            {saving ? "Kaydediliyor…" : retryPending ? "Kaydı tekrar dene" : "Yoklamayı kaydet"}
          </button>
        )}
      </PageHeader>
      {analysisError && <div role="alert"><ErrorState message={analysisError} retry={loadAnalysis} /></div>}
      {aiAnalysis && <RecordedAttendancePanel summary={aiAnalysis} />}
      <div className="card">
        <div className="toolbar">
          <select className="filter-select" disabled={saving || retryPending} value={classId} onChange={(e) => setClassId(e.target.value)} aria-label="Sınıf seç">
            <option value="">Sınıf seçin</option>
            {classes.map((item) => (
              <option value={item.id} key={item.id}>
                {String(item.name)}
              </option>
            ))}
          </select>
          <div className="search" style={{ maxWidth: 180 }}>
            <CalendarDays size={16} />
            <input type="date" disabled={saving || retryPending} value={date} onChange={(e) => setDate(e.target.value)} aria-label="Yoklama tarihi" />
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
            {counts.map((status) => (
              <span className="badge badge-neutral" key={status.value}>
                {status.label}: {status.count}
              </span>
            ))}
          </div>
        </div>
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} retry={() => void (classId ? loadRoster() : loadClasses())} />
        ) : !classId ? (
          <EmptyState title="Önce bir sınıf seçin" />
        ) : students.length === 0 ? (
          <EmptyState title="Bu sınıfta öğrenci yok" description="Sınıfa öğrenci atadıktan sonra yoklama alabilirsiniz." />
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
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {statuses.map((status) => (
                          <button
                            key={status.value}
                            type="button"
                            aria-pressed={records[student.id]?.status === status.value}
                            disabled={fieldsLocked}
                            className={`btn ${records[student.id]?.status === status.value ? "btn-primary" : "btn-secondary"}`}
                            style={{ minHeight: 34, padding: "0 10px" }}
                            onClick={() =>
                              setRecords((current) => ({ ...current, [student.id]: { ...current[student.id], status: status.value } }))
                            }
                          >
                            {records[student.id]?.status === status.value && <Check size={13} />}
                            {status.label}
                          </button>
                        ))}
                      </div>
                    </td>
                    <td>
                      <input
                        className="filter-select"
                        style={{ width: "100%" }}
                        placeholder="İsteğe bağlı not"
                        aria-label={`${String(student.first_name)} ${String(student.last_name)} için yoklama notu`}
                        disabled={fieldsLocked}
                        value={records[student.id]?.notes || ""}
                        onChange={(event) =>
                          setRecords((current) => ({ ...current, [student.id]: { ...current[student.id], notes: event.target.value } }))
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

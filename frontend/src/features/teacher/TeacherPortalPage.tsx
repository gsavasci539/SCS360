import { useState, useEffect } from "react";
import { BookOpen, Calendar, Users, FileText, CheckCircle, Clock, Pill } from "lucide-react";
import { api, apiMessage, unwrap } from "../../lib/api";
import { PageHeader, LoadingState, ErrorState, Badge, Tabs } from "../../components/ui";
import { StaffStudentChat } from "../parent/StaffStudentChat";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse } from "../../types/api";

interface ClassInfo {
  id: string;
  name: string;
  student_count: number;
}

interface ScheduleItem {
  id: string;
  subject: string;
  class_name: string;
  room: string;
  time: string;
  day: string;
}

interface Task {
  id: string;
  type: 'attendance' | 'daily_report' | 'grading' | 'material' | 'message' | 'medicine';
  title: string;
  description: string;
  due_date: string;
  priority: 'high' | 'medium' | 'low';
}

interface ScheduleRow {
  timetable_id: string;
  subject: string;
  class_name: string;
  room_number: string | null;
  start_time: string;
  end_time: string;
  day: string;
}

interface TaskRow {
  task_id: string;
  task_type: "attendance" | "daily_report";
  class_name: string;
  remaining_count: number;
  due_date: string;
  priority: Task["priority"];
}

interface MedicineRequest {
  id: string;
  student_name: string;
  class_name: string;
  medicine_name: string;
  dosage: string;
  time_to_give: string;
  instructions?: string;
  status: string;
  created_at?: string;
}

export default function TeacherPortalPage() {
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const canReadSchedule = hasPermission(user, "teacher.view_schedule");
  const canReadTasks = hasPermission(user, "teacher.manage_tasks");
  const canReadMedicine = hasPermission(user, "health.read") || hasPermission(user, "teacher.view_medicine_requests");
  return <TeacherPortal key={JSON.stringify([session, user?.id, user?.organization_id, user?.branch_ids, user?.permissions, workspace?.id])}
    canReadSchedule={canReadSchedule} canReadTasks={canReadTasks} canReadMedicine={canReadMedicine} />;
}

function TeacherPortal({ canReadSchedule, canReadTasks, canReadMedicine }: {
  canReadSchedule: boolean; canReadTasks: boolean; canReadMedicine: boolean;
}) {
  const [activeTab, setActiveTab] = useState("classes");
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [medicineRequests, setMedicineRequests] = useState<MedicineRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const request = { signal: controller.signal };
    Promise.all([
      api.get<ApiResponse<ClassInfo[]>>("/teacher/my-classes", request).then(unwrap),
      canReadSchedule ? api.get<ApiResponse<ScheduleRow[]>>("/teacher/today-schedule", request).then(unwrap) : [],
      canReadTasks ? api.get<ApiResponse<{ tasks: TaskRow[] }>>("/teacher/pending-tasks", request).then(unwrap) : { tasks: [] },
      canReadMedicine ? api.get<ApiResponse<MedicineRequest[]>>("/teacher/medicine-requests", request).then(unwrap) : [],
    ]).then(([classRows, scheduleRows, taskResponse, medicineRows]) => {
      if (controller.signal.aborted) return;
      setClasses(classRows);
      setSchedule(scheduleRows.map((item) => ({
        id: item.timetable_id,
        subject: item.subject,
        class_name: item.class_name,
        room: item.room_number || "Belirtilmedi",
        time: item.end_time ? `${item.start_time} - ${item.end_time}` : item.start_time,
        day: item.day,
      })));
      setTasks(taskResponse.tasks.map((task) => ({
        id: task.task_id,
        type: task.task_type,
        title: task.class_name,
        description: task.task_type === "attendance" ? `Yoklama bekleyen öğrenci sayısı ${task.remaining_count}` :
          `Günlük raporu bekleyen öğrenci sayısı ${task.remaining_count}`,
        due_date: task.due_date,
        priority: task.priority,
      })));
      setMedicineRequests(medicineRows);
    }).catch((err) => {
      if (!controller.signal.aborted) setError(apiMessage(err));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [attempt, canReadSchedule, canReadTasks, canReadMedicine]);

  if (loading) return <LoadingState label="Yükleniyor..." />;
  if (error) return <ErrorState message={error} retry={() => {
    setError("");
    setLoading(true);
    setAttempt((value) => value + 1);
  }} />;

  const taskIcons = {
    attendance: <CheckCircle size={16} />,
    daily_report: <FileText size={16} />,
    grading: <FileText size={16} />,
    material: <BookOpen size={16} />,
    message: <Clock size={16} />,
    medicine: <Pill size={16} />
  };

  return (
    <>
      <PageHeader
        eyebrow="Öğretmen Portalı"
        title="Hoş Geldiniz"
        description="Ders programınız, sınıflarınız ve bekleyen görevleriniz"
      />

      <div className="card">
        <Tabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          tabs={[
            { id: "overview", label: "Genel Bakış" },
            { id: "classes", label: "Sınıflarım" },
            ...(canReadSchedule ? [{ id: "schedule", label: "Bugünkü Program" }] : []),
            ...(canReadTasks ? [{ id: "tasks", label: "Görevler" }] : []),
            ...(canReadMedicine ? [{ id: "medicine", label: "İlaç Talepleri" }] : []),
            { id: "chat", label: "Mesajlar" }
          ]}
        />

        {activeTab === "overview" && (
          <div className="tab-content">
            <div className="grid stats-grid">
              <div className="card stat-card">
                <div className="stat-top">
                  <div className="stat-icon"><Users size={20} /></div>
                </div>
                <div className="stat-label">Toplam Sınıf</div>
                <div className="stat-value">{classes.length}</div>
              </div>
              {canReadSchedule && <div className="card stat-card">
                <div className="stat-top">
                  <div className="stat-icon"><Calendar size={20} /></div>
                </div>
                <div className="stat-label">Bugünkü Ders</div>
                <div className="stat-value">{schedule.length}</div>
              </div>}
              {canReadTasks && <div className="card stat-card">
                <div className="stat-top">
                  <div className="stat-icon"><CheckCircle size={20} /></div>
                </div>
                <div className="stat-label">Bekleyen Görev</div>
                <div className="stat-value">{tasks.length}</div>
              </div>}
            </div>

            {canReadSchedule && <div className="mt-6">
              <h3>Bugünkü Ders Programı</h3>
              {schedule.length > 0 ? (
                <table className="data-table mt-4">
                  <thead>
                    <tr>
                      <th>Saat</th>
                      <th>Ders</th>
                      <th>Sınıf</th>
                      <th>Oda</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.map((item) => (
                      <tr key={item.id}>
                        <td>{item.time}</td>
                        <td>{item.subject}</td>
                        <td>{item.class_name}</td>
                        <td>{item.room}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-gray-500 mt-4">Bugün ders programınız yok.</p>
              )}
            </div>}
          </div>
        )}

        {activeTab === "classes" && (
          <div className="tab-content">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sınıf Adı</th>
                  <th>Öğrenci Sayısı</th>
                </tr>
              </thead>
              <tbody>
                {classes.map((cls) => (
                  <tr key={cls.id}>
                    <td>{cls.name}</td>
                    <td>{cls.student_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {classes.length === 0 && <p className="text-gray-500 mt-4">Henüz sınıf atanmamış.</p>}
          </div>
        )}

        {activeTab === "schedule" && canReadSchedule && (
          <div className="tab-content">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Gün</th>
                  <th>Saat</th>
                  <th>Ders</th>
                  <th>Sınıf</th>
                  <th>Oda</th>
                </tr>
              </thead>
              <tbody>
                {schedule.map((item) => (
                  <tr key={item.id}>
                    <td>{item.day}</td>
                    <td>{item.time}</td>
                    <td>{item.subject}</td>
                    <td>{item.class_name}</td>
                    <td>{item.room}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {schedule.length === 0 && <p className="text-gray-500 mt-4">Bugün ders programınız yok.</p>}
          </div>
        )}

        {activeTab === "tasks" && canReadTasks && (
          <div className="tab-content">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tip</th>
                  <th>Başlık</th>
                  <th>Açıklama</th>
                  <th>Son Tarih</th>
                  <th>Öncelik</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        {taskIcons[task.type]}
                        <Badge value={task.type.toUpperCase()} />
                      </div>
                    </td>
                    <td>{task.title}</td>
                    <td>{task.description}</td>
                    <td>{new Date(task.due_date).toLocaleDateString("tr-TR")}</td>
                    <td><Badge value={task.priority.toUpperCase()} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {tasks.length === 0 && <p className="text-gray-500 mt-4">Bekleyen göreviniz yok.</p>}
          </div>
        )}
        {activeTab === "medicine" && canReadMedicine && (
          <div className="tab-content">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Sınıf</th>
                  <th>İlaç</th>
                  <th>Doz</th>
                  <th>Saat</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {medicineRequests.map((request) => (
                  <tr key={request.id}>
                    <td>{request.student_name}</td>
                    <td>{request.class_name}</td>
                    <td>{request.medicine_name}</td>
                    <td>{request.dosage}</td>
                    <td>{request.time_to_give}</td>
                    <td><Badge value={request.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {medicineRequests.length === 0 && <p className="text-gray-500 mt-4">Sınıflarınız için ilaç talebi yok.</p>}
          </div>
        )}
        {activeTab === "chat" && (
          <div className="tab-content"><StaffStudentChat area="/teacher" /></div>
        )}
      </div>
    </>
  );
}

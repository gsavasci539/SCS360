import { useState, useEffect } from "react";
import { BookOpen, Calendar, Users, FileText, CheckCircle, Clock, MessageCircle } from "lucide-react";
import { api, apiMessage } from "../../lib/api";
import { PageHeader, LoadingState, ErrorState, Badge, Tabs } from "../../components/ui";
import { ChatInterface } from "../parent/ChatInterface";

interface ClassInfo {
  id: string;
  name: string;
  grade: string;
  section: string;
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
  type: 'attendance' | 'grading' | 'material' | 'message';
  title: string;
  description: string;
  due_date: string;
  priority: 'high' | 'medium' | 'low';
}

interface StudentWithParent {
  student_id: string;
  student_name: string;
  parent_id: string;
  parent_name: string;
  is_primary: boolean;
}

export default function TeacherPortalPage() {
  const [activeTab, setActiveTab] = useState("classes");
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  // Chat state
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [students, setStudents] = useState<StudentWithParent[]>([]);
  const [chatStudentId, setChatStudentId] = useState<string>("");
  const [chatParentName, setChatParentName] = useState<string>("");

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    console.log("Loading data, activeTab:", activeTab);
    setLoading(true);
    setError("");
    try {
      const [classesResult, scheduleResult, tasksResult] = await Promise.allSettled([
        api.get("/teacher/my-classes"),
        api.get("/teacher/today-schedule"),
        api.get("/teacher/pending-tasks")
      ]);
      if (classesResult.status === "fulfilled") {
        console.log("Classes full response:", classesResult.value);
        const classesData = classesResult.value.data.data || [];
        console.log("Classes data:", classesData);
        setClasses(classesData);
      } else {
        console.error("Classes error:", classesResult.reason);
        setError(apiMessage(classesResult.reason));
      }
      if (scheduleResult.status === "fulfilled") {
        console.log("Schedule full response:", scheduleResult.value);
        const scheduleData = scheduleResult.value.data.data || [];
        console.log("Schedule data:", scheduleData);
        setSchedule(scheduleData.map((item: any) => ({
          id: item.timetable_id,
          subject: item.subject_id || "Ders",
          class_name: item.class_name,
          room: item.room_number || "Belirtilmedi",
          time: `${item.start_time} - ${item.end_time}`,
          day: item.day
        })));
      } else {
        console.error("Schedule error:", scheduleResult.reason);
      }
      if (tasksResult.status === "fulfilled") {
        const tasksData = tasksResult.value.data.data;
        setTasks((tasksData?.tasks || []).map((task: any) => ({
          id: task.task_id || Math.random().toString(),
          type: task.task_type,
          title: task.class_name || "Görev",
          description: task.task_type === "attendance" ? "Yoklama almayı bekliyor" : task.task_type === "daily_report" ? "Günlük rapor girişi" : "Diğer",
          due_date: task.due_date,
          priority: task.priority
        })));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const loadClassStudents = async (classId: string) => {
    try {
      const result = await api.get(`/teacher/class/${classId}/students`);
      setStudents(result.data.data || []);
      setSelectedClass(classId);
    } catch (err) {
      setError(apiMessage(err));
    }
  };

  const openChat = (studentId: string, parentName: string) => {
    setChatStudentId(studentId);
    setChatParentName(parentName);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    load();
  }, [activeTab]);

  if (loading) return <LoadingState label="Yükleniyor..." />;
  if (error) return <ErrorState message={error} retry={load} />;

  const taskIcons = {
    attendance: <CheckCircle size={16} />,
    grading: <FileText size={16} />,
    material: <BookOpen size={16} />,
    message: <Clock size={16} />
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
            { id: "schedule", label: "Bugünkü Program" },
            { id: "tasks", label: "Görevler" },
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
              <div className="card stat-card">
                <div className="stat-top">
                  <div className="stat-icon"><Calendar size={20} /></div>
                </div>
                <div className="stat-label">Bugünkü Ders</div>
                <div className="stat-value">{schedule.length}</div>
              </div>
              <div className="card stat-card">
                <div className="stat-top">
                  <div className="stat-icon"><CheckCircle size={20} /></div>
                </div>
                <div className="stat-label">Bekleyen Görev</div>
                <div className="stat-value">{tasks.length}</div>
              </div>
            </div>

            <div className="mt-6">
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
            </div>
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

        {activeTab === "schedule" && (
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

        {activeTab === "tasks" && (
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
        {activeTab === "chat" && (
          <div className="tab-content">
            {chatStudentId ? (
              <ChatInterface
                studentId={chatStudentId}
                teacherName={chatParentName}
                onBack={() => {
                  setChatStudentId("");
                  setChatParentName("");
                }}
                apiBase="/teacher"
              />
            ) : (
              <div>
                <h3 style={{ marginBottom: 16 }}>Sınıf Seçin</h3>
                <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 24 }}>
                  {classes.map((cls) => (
                    <div
                      key={cls.id}
                      className="card"
                      style={{ padding: 16, cursor: "pointer", textAlign: "center" }}
                      onClick={() => loadClassStudents(cls.id)}
                    >
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>{cls.name}</div>
                      <div style={{ fontSize: 12, color: "#666" }}>{cls.student_count} öğrenci</div>
                    </div>
                  ))}
                </div>

                {selectedClass && students.length > 0 && (
                  <>
                    <h3 style={{ marginBottom: 16 }}>Öğrenciler ve Veliler</h3>
                    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
                      {students.map((student) => (
                        <div
                          key={student.student_id}
                          className="card"
                          style={{ padding: 16, cursor: "pointer" }}
                          onClick={() => openChat(student.student_id, student.parent_name)}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                            <div style={{
                              width: 40,
                              height: 40,
                              borderRadius: "50%",
                              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "white",
                              fontWeight: 600
                            }}>
                              {student.student_name[0]}
                            </div>
                            <div>
                              <div style={{ fontWeight: 600 }}>{student.student_name}</div>
                              <div style={{ fontSize: 12, color: "#666" }}>{student.parent_name}</div>
                            </div>
                          </div>
                          <button
                            className="btn btn-primary"
                            style={{ width: "100%", padding: 8, fontSize: 14 }}
                          >
                            <MessageCircle size={16} style={{ marginRight: 8 }} />
                            Mesaj Gönder
                          </button>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {selectedClass && students.length === 0 && (
                  <div style={{ textAlign: "center", padding: 40, color: "#666" }}>
                    Bu sınıfta öğrenci bulunamadı
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

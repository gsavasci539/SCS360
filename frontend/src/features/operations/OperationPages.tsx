import {
  Coins,
  CheckCircle2,
  Plus,
  Trash2,
  Video,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader, StatCard } from "../../components/ui";
import { api } from "../../lib/api";

// ==================== 1. RANDEVU VE PTC GÖRÜŞMELERİ ====================
export function AppointmentsPage() {
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModal, setCreateModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState("ALL");
  const { showToast } = useToast();

  const [formData, setFormData] = useState({
    teacher_id: "usr-teacher-1",
    teacher_name: "Ayşe Yılmaz",
    subject: "Matematik",
    date: new Date().toISOString().slice(0, 10),
    time_slot: "14:30 - 15:00",
    type: "IN_PERSON",
    notes: "",
  });

  async function loadData() {
    try {
      setLoading(true);
      const res: any = await api.get("/appointments");
      setAppointments(res.data?.data || res.data || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Randevular yüklenemedi");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleCreate() {
    try {
      await api.post("/appointments", formData);
      showToast("Randevu Oluşturuldu", "Veli-Öğretmen randevusu takvime işlendi.");
      setCreateModal(false);
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message || "Randevu oluşturulamadı", "error");
    }
  }

  async function handleStatus(id: string, status: string) {
    try {
      await api.patch(`/appointments/${id}/status`, { status });
      showToast("Durum Güncellendi", `Randevu '${status}' olarak güncellendi.`);
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  const filtered = appointments.filter((a) => filterStatus === "ALL" || a.status === filterStatus);

  if (loading) return <LoadingState label="Randevular yükleniyor..." />;
  if (error) return <ErrorState message={error} retry={loadData} />;

  return (
    <div>
      <PageHeader
        eyebrow="İletişim & Rehberlik"
        title="Veli - Öğretmen Randevuları (PTC)"
        description="Birebir veli görüşmeleri, online Meet toplantıları ve randevu takvimini yönetin."
      >
        <button className="btn btn-primary" onClick={() => setCreateModal(true)}>
          <Plus size={16} /> Yeni Randevu Talebi
        </button>
      </PageHeader>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <button className={`btn ${filterStatus === "ALL" ? "btn-primary" : "btn-secondary"}`} onClick={() => setFilterStatus("ALL")}>
          Tümü ({appointments.length})
        </button>
        <button className={`btn ${filterStatus === "CONFIRMED" ? "btn-primary" : "btn-secondary"}`} onClick={() => setFilterStatus("CONFIRMED")}>
          Onaylananlar
        </button>
        <button className={`btn ${filterStatus === "COMPLETED" ? "btn-primary" : "btn-secondary"}`} onClick={() => setFilterStatus("COMPLETED")}>
          Tamamlananlar
        </button>
        <button className={`btn ${filterStatus === "CANCELLED" ? "btn-primary" : "btn-secondary"}`} onClick={() => setFilterStatus("CANCELLED")}>
          İptal Edilenler
        </button>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="Randevu Bulunamadı" description="Seçili filtrede henüz kayıtlı randevu yok." />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 16 }}>
          {filtered.map((apt) => (
            <div key={apt.id} className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{apt.teacher_name}</h3>
                  <div style={{ fontSize: 13, color: "#64748b" }}>{apt.subject}</div>
                </div>
                <span className={`badge badge-${apt.status === "CONFIRMED" ? "success" : apt.status === "COMPLETED" ? "neutral" : "danger"}`}>
                  {apt.status === "CONFIRMED" ? "Onaylandı" : apt.status === "COMPLETED" ? "Tamamlandı" : "İptal"}
                </span>
              </div>

              <div style={{ background: "#f8fafc", padding: 12, borderRadius: 8, fontSize: 13 }}>
                <div><strong>Veli:</strong> {apt.parent_name} ({apt.student_name})</div>
                <div style={{ marginTop: 4 }}><strong>Tarih & Saat:</strong> {apt.date} • {apt.time_slot}</div>
                <div style={{ marginTop: 4 }}>
                  <strong>Tür:</strong> {apt.type === "ONLINE_MEET" ? "🎥 Google Meet Online" : apt.type === "PHONE" ? "📞 Telefon" : "🏫 Yüz Yüze Okulda"}
                </div>
                {apt.notes && <div style={{ marginTop: 4, color: "#475569" }}><em>"{apt.notes}"</em></div>}
              </div>

              {apt.meeting_link && apt.type === "ONLINE_MEET" && (
                <a href={apt.meeting_link} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ justifyContent: "center" }}>
                  <Video size={16} /> Meet Görüşmesine Katıl
                </a>
              )}

              <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                {apt.status === "CONFIRMED" && (
                  <>
                    <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => handleStatus(apt.id, "COMPLETED")}>
                      <CheckCircle2 size={15} /> Tamamla
                    </button>
                    <button className="btn btn-ghost" style={{ color: "#ef4444" }} onClick={() => handleStatus(apt.id, "CANCELLED")}>
                      <XCircle size={15} /> İptal
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={createModal} title="Yeni Görüşme Randevusu" onClose={() => setCreateModal(false)}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Field label="Öğretmen Adı">
            <input className="input" value={formData.teacher_name} onChange={(e) => setFormData({ ...formData, teacher_name: e.target.value })} />
          </Field>
          <Field label="Branş / Alan">
            <input className="input" value={formData.subject} onChange={(e) => setFormData({ ...formData, subject: e.target.value })} />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Tarih">
              <input type="date" className="input" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} />
            </Field>
            <Field label="Saat Aralığı">
              <input className="input" value={formData.time_slot} onChange={(e) => setFormData({ ...formData, time_slot: e.target.value })} />
            </Field>
          </div>
          <Field label="Görüşme Türü">
            <select className="input" value={formData.type} onChange={(e) => setFormData({ ...formData, type: e.target.value })}>
              <option value="IN_PERSON">Yüz Yüze (Okulda)</option>
              <option value="ONLINE_MEET">Online (Google Meet)</option>
              <option value="PHONE">Telefon Görüşmesi</option>
            </select>
          </Field>
          <Field label="Görüşme Konusu & Notlar">
            <textarea className="input" rows={3} value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} />
          </Field>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
            <button className="btn btn-secondary" onClick={() => setCreateModal(false)}>İptal</button>
            <button className="btn btn-primary" onClick={handleCreate}>Randevuyu Kaydet</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}


// ==================== 2. ÖDEV VE NOTLANDIRMA ====================
export function HomeworkPage() {
  const [homeworkList, setHomeworkList] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [gradeModal, setGradeModal] = useState<any>(null);
  const [score, setScore] = useState("90");
  const [feedback, setFeedback] = useState("");
  const { showToast } = useToast();

  async function loadData() {
    const [hRes, sRes]: any = await Promise.all([
      api.get("/homework"),
      api.get("/homework/submissions"),
    ]);
    setHomeworkList(hRes.data?.data || hRes.data || []);
    setSubmissions(sRes.data?.data || sRes.data || []);
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleGrade() {
    if (!gradeModal) return;
    try {
      await api.put(`/homework/submissions/${gradeModal.id}/grade`, {
        score: parseInt(score),
        teacher_feedback: feedback,
      });
      showToast("Ödev Puanlandı", "Öğrenci ve veliye not bildirimi iletildi.");
      setGradeModal(null);
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Akademik & Eğitim"
        title="Ödev & Notlandırma Paneli"
        description="Öğretmen ödev tanımları, öğrenci dijital teslimleri ve 100 üzerinden puanlama."
      />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 20 }}>
        {/* Ödevler */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Aktif Ödevler</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {homeworkList.map((hw) => (
              <div key={hw.id} className="card" style={{ padding: 18 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span className="badge badge-neutral">{hw.subject} • {hw.class_name}</span>
                  <small style={{ color: "#ef4444", fontWeight: 600 }}>Son Teslim: {hw.due_date}</small>
                </div>
                <h4 style={{ margin: "8px 0 4px 0", fontSize: 15 }}>{hw.title}</h4>
                <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>{hw.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Teslimler & Notlandırma */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Öğrenci Teslimleri</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {submissions.map((sub) => (
              <div key={sub.id} className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong>{sub.student_name}</strong> <small style={{ color: "#64748b" }}>({sub.student_number})</small>
                  </div>
                  {sub.status === "GRADED" ? (
                    <span className="badge badge-success">Not: {sub.score} / 100</span>
                  ) : (
                    <span className="badge badge-warning">Değerlendirme Bekliyor</span>
                  )}
                </div>

                <div style={{ background: "#f8fafc", padding: 10, borderRadius: 6, fontSize: 13 }}>
                  <div>📎 <strong>Ekli Dosya:</strong> {sub.attachment_file_name} ({sub.attachment_file_size_mb} MB)</div>
                  {sub.teacher_feedback && <div style={{ marginTop: 6, color: "#166534" }}>💬 Öğretmen Geri Bildirimi: <em>{sub.teacher_feedback}</em></div>}
                </div>

                <button className="btn btn-secondary btn-sm" style={{ alignSelf: "flex-end" }} onClick={() => { setGradeModal(sub); setScore(sub.score ? String(sub.score) : "95"); setFeedback(sub.teacher_feedback || ""); }}>
                  {sub.status === "GRADED" ? "Notu Düzenle" : "Not Ver"}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal open={Boolean(gradeModal)} title="Ödev Notlandırma" onClose={() => setGradeModal(null)}>
        {gradeModal && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><strong>Öğrenci:</strong> {gradeModal.student_name}</div>
            <Field label="Puan (0 - 100)">
              <input type="number" className="input" min={0} max={100} value={score} onChange={(e) => setScore(e.target.value)} />
            </Field>
            <Field label="Geri Bildirim & Öğretmen Notu">
              <textarea className="input" rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
            </Field>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button className="btn btn-secondary" onClick={() => setGradeModal(null)}>İptal</button>
              <button className="btn btn-primary" onClick={handleGrade}>Puanı Kaydet</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}


// ==================== 5. KÜTÜPHANE VE KİTAP ZİMMET ====================
export function LibraryPage() {
  const [books, setBooks] = useState<any[]>([]);
  const [loans, setLoans] = useState<any[]>([]);
  const { showToast } = useToast();

  async function loadData() {
    const [bRes, lRes]: any = await Promise.all([
      api.get("/library/books"),
      api.get("/library/loans"),
    ]);
    setBooks(bRes.data?.data || bRes.data || []);
    setLoans(lRes.data?.data || lRes.data || []);
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleReturn(loanId: string) {
    try {
      await api.put(`/library/loans/${loanId}/return`, {});
      showToast("Kitap İade Alındı", "Kitap envantere geri döndü.");
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  async function handleRemind(loanId: string) {
    try {
      await api.post(`/library/loans/${loanId}/remind`, {});
      showToast("Hatırlatma Gönderildi", "Veliye SMS ve push bildirimi iletildi.");
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Kaynak & Envanter"
        title="Kütüphane & Kitap Zimmet Takibi"
        description="Barkodlu kitap kataloğu, öğrenciye ödünç verme, gecikme hatırlatmaları ve iade."
      />

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
        {/* Kitap Kataloğu */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Kitap Kataloğu</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 10 }}>
            {books.map((b) => (
              <div key={b.id} className="card" style={{ padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h4 style={{ margin: 0, fontSize: 15 }}>{b.title}</h4>
                  <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>{b.author} • <small>{b.category}</small></div>
                  <small style={{ color: "#94a3b8" }}>ISBN: {b.isbn}</small>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span className={`badge badge-${b.available_copies > 0 ? "success" : "danger"}`}>
                    {b.available_copies} / {b.total_copies} Mevcut
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Zimmet & Ödünç Listesi */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Ödünç Verilen Kitaplar</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {loans.map((l) => (
              <div key={l.id} className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{l.book_title}</strong>
                  <span className={`badge badge-${l.status === "RETURNED" ? "neutral" : "warning"}`}>
                    {l.status === "RETURNED" ? "Teslim Edildi" : "Ödünçte"}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#475569" }}>
                  <div><strong>Öğrenci:</strong> {l.student_name} ({l.class_name})</div>
                  <div><strong>Son Teslim:</strong> {l.due_date}</div>
                </div>
                {l.status === "BORROWED" && (
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => handleReturn(l.id)}>İade Al</button>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleRemind(l.id)}>Veliye Hatırlat</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}


// ==================== 6. PERSONEL VE NÖBET ÇİZELGESİ ====================
export function StaffPage() {
  const [rosters, setRosters] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any[]>([]);
  const { showToast } = useToast();

  async function loadData() {
    const [rRes, lRes]: any = await Promise.all([
      api.get("/staff/duty-rosters"),
      api.get("/staff/leave-requests"),
    ]);
    setRosters(rRes.data?.data || rRes.data || []);
    setLeaves(lRes.data?.data || lRes.data || []);
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleReviewLeave(id: string, status: string) {
    try {
      await api.put(`/staff/leave-requests/${id}/review`, { status });
      showToast("İzin Değerlendirildi", `Talep '${status}' olarak güncellendi.`);
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="İnsan Kaynakları & İdare"
        title="Personel İK & Nöbet Çizelgesi"
        description="Haftalık nöbetçi öğretmen görev dağılımı, izin talepleri ve idari onay akışı."
      />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Nöbet Çizelgesi */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Haftalık Nöbet Çizelgesi</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {rosters.map((r) => (
              <div key={r.id} className="card" style={{ padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="badge badge-neutral">{r.day_of_week}</span>
                  <h4 style={{ margin: "6px 0 2px 0", fontSize: 15 }}>{r.teacher_name}</h4>
                  <div style={{ fontSize: 13, color: "#64748b" }}>📍 {r.duty_location}</div>
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#0284c7" }}>
                  {r.start_time} - {r.end_time}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* İzin Talepleri */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Personel İzin Talepleri</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {leaves.map((lv) => (
              <div key={lv.id} className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{lv.staff_name}</strong>
                  <span className={`badge badge-${lv.status === "APPROVED" ? "success" : lv.status === "PENDING" ? "warning" : "danger"}`}>
                    {lv.status === "APPROVED" ? "Onaylandı" : lv.status === "PENDING" ? "Bekliyor" : "Reddedildi"}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#475569" }}>
                  <div><strong>Tür & Süre:</strong> {lv.leave_type} ({lv.days_count} gün)</div>
                  <div><strong>Tarih:</strong> {lv.start_date} - {lv.end_date}</div>
                  <div><strong>Gerekçe:</strong> {lv.reason}</div>
                </div>
                {lv.status === "PENDING" && (
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <button className="btn btn-primary btn-sm" onClick={() => handleReviewLeave(lv.id, "APPROVED")}>Onayla</button>
                    <button className="btn btn-ghost btn-sm" style={{ color: "#ef4444" }} onClick={() => handleReviewLeave(lv.id, "REJECTED")}>Reddet</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}


// ==================== 7. GİDERLER VE HARCAMALAR ====================
export function ExpensesPage() {
  const [expenses, setExpenses] = useState<any[]>([]);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ category: "Mutfak", title: "", amount: "", date: new Date().toISOString().slice(0, 10), branch_id: "branch-001" });
  const { showToast } = useToast();

  async function loadExpenses() {
    try {
      const res: any = await api.get("/expenses");
      setExpenses(res.data?.data || res.data || []);
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  useEffect(() => {
    loadExpenses();
  }, []);

  async function handleCreate() {
    try {
      await api.post("/expenses", form);
      showToast("Gider Kaydedildi", "Harcama kalemi muhasebeye işlendi.");
      setModal(false);
      loadExpenses();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.delete(`/expenses/${id}`);
      showToast("Silindi", "Gider kaydı kaldırıldı.");
      loadExpenses();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  const total = expenses.reduce((sum, e) => sum + parseFloat(e.amount || 0), 0);

  return (
    <div>
      <PageHeader
        eyebrow="Finans & Muhasebe"
        title="Giderler & Harcama Takibi"
        description="Kira, mutfak, kırtasiye, fatura ve operasyonel harcama kalemleri."
      >
        <button className="btn btn-primary" onClick={() => setModal(true)}>
          <Plus size={16} /> Yeni Gider Ekle
        </button>
      </PageHeader>

      <div style={{ marginBottom: 20 }}>
        <StatCard icon={<Coins size={22} />} label="Toplam Harcama" value={`₺${total.toLocaleString("tr-TR")}`} color="red" />
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <table className="table">
          <thead>
            <tr>
              <th>Kategori</th>
              <th>Açıklama / Başlık</th>
              <th>Tarih</th>
              <th>Tutar</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr key={e.id}>
                <td><span className="badge badge-neutral">{e.category}</span></td>
                <td><strong>{e.title}</strong></td>
                <td>{e.date}</td>
                <td style={{ fontWeight: 700, color: "#dc2626" }}>₺{parseFloat(e.amount).toLocaleString("tr-TR")}</td>
                <td>
                  <button className="btn btn-ghost btn-sm" style={{ color: "#ef4444" }} onClick={() => handleDelete(e.id)}>
                    <Trash2 size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={modal} title="Yeni Gider Kalemi Ekle" onClose={() => setModal(false)}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Field label="Kategori">
            <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="Kira">Kira</option>
              <option value="Mutfak">Mutfak & Yemek</option>
              <option value="Kırtasiye">Kırtasiye & Materyal</option>
              <option value="Fatura">Fatura (Elektrik/Su/Doğalgaz)</option>
              <option value="Maaş">Personel & Maaş</option>
              <option value="Diğer">Diğer</option>
            </select>
          </Field>
          <Field label="Gider Başlığı">
            <input className="input" placeholder="Örn: Kırtasiye Alımı" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </Field>
          <Field label="Tutar (TL)">
            <input type="number" className="input" placeholder="0.00" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </Field>
          <Field label="Tarih">
            <input type="date" className="input" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </Field>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
            <button className="btn btn-secondary" onClick={() => setModal(false)}>İptal</button>
            <button className="btn btn-primary" onClick={handleCreate}>Kaydet</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}


// ==================== 8. GÜNLÜK KARNE (DAILY REPORTS) ====================
export function DailyReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const { showToast } = useToast();

  async function loadData() {
    try {
      const res: any = await api.get("/daily-reports");
      setReports(res.data?.data || res.data || []);
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div>
      <PageHeader
        eyebrow="Kreş & Anaokulu"
        title="Günlük Karne & Gelişim Raporu"
        description="Öğrencilerin yemek, uyku, duygu durumu ve günlük etkinlik geri bildirimleri."
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 16 }}>
        {reports.map((r) => (
          <div key={r.id} className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Zeynep Demir</h3>
              <span className="badge badge-neutral">{r.date}</span>
            </div>
            <div style={{ background: "#f8fafc", padding: 12, borderRadius: 8, fontSize: 13 }}>
              <div>🍽️ <strong>Yemek:</strong> Sabah: {r.meal_breakfast} • Öğle: {r.meal_lunch} • İkindi: {r.meal_snack}</div>
              <div style={{ marginTop: 4 }}>😴 <strong>Uyku:</strong> {r.sleep_status}</div>
              <div style={{ marginTop: 4 }}>😊 <strong>Duygu Durumu:</strong> {r.mood}</div>
              {r.activities && <div style={{ marginTop: 6, color: "#0369a1" }}>🎨 <strong>Etkinlikler:</strong> {r.activities}</div>}
              {r.teacher_notes && <div style={{ marginTop: 6, color: "#475569" }}>💬 <em>"{r.teacher_notes}"</em></div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


// ==================== 9. VELİ TALEPLERİ (PARENT NOTICES) ====================
export function ParentNoticesPage() {
  const [notices, setNotices] = useState<any[]>([]);
  const { showToast } = useToast();

  async function loadData() {
    try {
      const res: any = await api.get("/parent/notices");
      setNotices(res.data?.data || res.data || []);
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleStatus(id: string, status: string) {
    try {
      await api.patch(`/parent/notices/${id}/status`, { status });
      showToast("Güncellendi", `Talep durumu '${status}' olarak güncellendi.`);
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="İletişim & Güvenlik"
        title="Veli Talepleri (İlaç, İzin, Teslimat)"
        description="Velilerden gelen anlık ilaç verme saatleri, izin bildirimleri ve teslim alacak kişi kayıtları."
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 16 }}>
        {notices.map((n) => (
          <div key={n.id} className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span className={`badge badge-${n.type === "MEDICINE" ? "warning" : n.type === "PICKUP" ? "primary" : "neutral"}`}>
                {n.type === "MEDICINE" ? "💊 İlaç Bildirimi" : n.type === "PICKUP" ? "🚗 Teslimat" : "📝 İzin"}
              </span>
              <span className={`badge badge-${n.status === "GIVEN" || n.status === "APPROVED" ? "success" : "neutral"}`}>
                {n.status === "GIVEN" ? "Verildi" : n.status === "APPROVED" ? "Onaylandı" : "Alındı"}
              </span>
            </div>
            <h4 style={{ margin: 0, fontSize: 16 }}>{n.title}</h4>
            <p style={{ margin: 0, fontSize: 13, color: "#475569" }}>{n.content}</p>
            {n.response_notes && <div style={{ fontSize: 12, color: "#166534" }}>✅ {n.response_notes}</div>}
            {n.status === "RECEIVED" && (
              <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                <button className="btn btn-primary btn-sm" onClick={() => handleStatus(n.id, "GIVEN")}>
                  <CheckCircle2 size={14} /> İlaç Verildi
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}


// ==================== 10. GİDEN KUTUSU & İLETİŞİM LOGLARI (OUTBOX) ====================
export function OutboxLogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const { showToast } = useToast();

  async function loadData() {
    try {
      const res: any = await api.get("/outbox");
      setLogs(res.data?.data || res.data || []);
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleRetry(id: string) {
    try {
      await api.post(`/outbox/retry/${id}`, {});
      showToast("Yeniden Gönderildi", "Mesaj operatöre tekrar iletildi.");
      loadData();
    } catch (e: any) {
      showToast("Hata", e.message, "error");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="İletişim Altyapısı"
        title="Giden Kutusu & Bildirim Logları (Outbox)"
        description="SMS, WhatsApp ve Push bildirimlerinin iletim durumu, DLR raporları ve yeniden deneme."
      />

      <div className="card" style={{ overflow: "hidden" }}>
        <table className="table">
          <thead>
            <tr>
              <th>Kanal</th>
              <th>Alıcı</th>
              <th>Mesaj İçeriği</th>
              <th>Gönderim Zamanı</th>
              <th>Durum</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>
                  <span className={`badge badge-${log.channel === "SMS" ? "primary" : log.channel === "WHATSAPP" ? "success" : "neutral"}`}>
                    {log.channel}
                  </span>
                </td>
                <td>
                  <strong>{log.recipient_name}</strong>
                  <div style={{ fontSize: 12, color: "#64748b" }}>{log.recipient}</div>
                </td>
                <td style={{ maxWidth: 300, fontSize: 13 }}>{log.message}</td>
                <td style={{ fontSize: 12 }}>{new Date(log.sent_at).toLocaleString("tr-TR")}</td>
                <td>
                  <span className={`badge badge-${log.status === "DELIVERED" ? "success" : "warning"}`}>
                    {log.status === "DELIVERED" ? "İletildi (DLR)" : "Bekliyor"}
                  </span>
                </td>
                <td>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleRetry(log.id)}>
                    Yeniden Gönder
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

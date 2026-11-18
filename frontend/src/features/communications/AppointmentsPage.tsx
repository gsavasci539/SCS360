import { Plus, ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { useParams, Link } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { AppointmentCreateModal } from "./AppointmentCreateModal";
import { AppointmentSlotsModal } from "./AppointmentSlotsModal";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

type StatusEdit = { status: string; feedback_notes?: string | null };
const statusLabels: Record<string, string> = {
  PENDING: "Onay bekliyor", APPROVED: "Onaylandı", CONFIRMED: "Onaylandı",
  REJECTED: "Reddedildi", COMPLETED: "Tamamlandı", CANCELLED: "İptal edildi",
};

export function AppointmentsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const session = useAuthStore((s) => s.sessionVersion);
  const workspace = usePlatformWorkspace((s) => s.workspace?.id);
  return <ScopedAppointmentsPage key={JSON.stringify([id, session, user?.id, workspace, user?.organization_id, user?.branch_ids, user?.roles, user?.permissions])} />;
}

function ScopedAppointmentsPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [detail, setDetail] = useState<DataRecord | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [slotsOpen, setSlotsOpen] = useState(false);
  const [feedbackDraft, setFeedbackDraft] = useState<string | null>(null);
  const [statusBusy, setStatusBusy] = useState(false);
  const [statusError, setStatusError] = useState("");
  const [pendingStatus, setPendingStatus] = useState<StatusEdit | null>(null);
  const statusRequest = useRef<AbortController | null>(null);
  const { showToast } = useToast();
  const can = useAuthStore((s) => s.can);
  const user = useAuthStore((s) => s.user);
  const roles = user?.roles.map((role) => role.slug) ?? [];
  const parent = roles.includes("parent");
  const parentOnly = parent && !user?.is_super_admin && !roles.some((role) =>
    ["owner", "admin", "administrator", "school_admin", "manager", "principal", "org_admin", "branch_manager"].includes(role));
  const canWrite = can("appointments.write");

  async function load(page = data.page) {
    setLoading(true);
    try {
      const r = await api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/appointments", {
        params: { page, page_size: 20, limit: 20, skip: (page - 1) * 20 }
      });
      setData(normalize(r.data.data));
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(appointmentId: string) {
    setLoading(true);
    setError("");
    try {
      const r = await api.get<ApiResponse<DataRecord>>(`/appointments/${appointmentId}`);
      setDetail(r.data.data);
    } catch (e) {
      setError(apiMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) {
      loadDetail(id);
    } else {
      load(1);
    }
  }, [id]);
  useEffect(() => () => statusRequest.current?.abort(), []);

  const filtered = useMemo(() => 
    data.items.filter((r) => JSON.stringify(r).toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))),
    [data.items, search]
  );

  async function handleDelete(row: DataRecord) {
    try {
      await api.delete(`/appointments/${row.id}`);
      showToast("Randevu silindi", "Randevu başarıyla silindi.");
      await load();
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    }
  }

  async function handleUpdateStatus(edit: StatusEdit, verifyOnly = false) {
    if (!detail || !canWrite || statusRequest.current ||
        (parentOnly && (edit.status !== "CANCELLED" || edit.feedback_notes !== undefined))) return;
    const controller = new AbortController();
    statusRequest.current = controller;
    const config = { signal: controller.signal };
    const url = `/appointments/${detail.id}`;
    setStatusBusy(true);
    setStatusError("");
    let received = false;
    try {
      if (!verifyOnly) {
        const { data } = await api.patch<ApiResponse<DataRecord>>(`${url}/status`, edit, config);
        received = true;
        if (!data.success || data.data.id !== detail.id || data.data.status !== edit.status) {
          throw new Error("Randevu yanıtı doğrulanamadı.");
        }
      }
      const { data } = await api.get<ApiResponse<DataRecord>>(url, config);
      if (controller.signal.aborted) return;
      const row = data.data;
      if (!data.success || row.id !== detail.id) throw new Error("Randevu kaydı doğrulanamadı.");
      setDetail(row);
      if (row.status !== edit.status || (edit.feedback_notes !== undefined && (row.feedback_notes ?? null) !== edit.feedback_notes)) {
        throw new Error("Randevu sonucu doğrulanamadı.");
      }
      setPendingStatus(null);
      setFeedbackDraft(null);
      showToast("Randevu güncellendi", "Değişiklik sunucuda doğrulandı.");
    } catch (e) {
      if (controller.signal.aborted) return;
      if (!verifyOnly && !received && isAxiosError(e) && [401, 403, 404, 422].includes(e.response?.status ?? 0)) {
        setStatusError(apiMessage(e));
      } else {
        setPendingStatus(edit);
        setStatusError("Değişiklik doğrulanamadı. Sonucu sunucudan tekrar kontrol edebilirsiniz.");
      }
    } finally {
      statusRequest.current = null;
      if (!controller.signal.aborted) setStatusBusy(false);
    }
  }
  const status = String(detail?.status ?? "");
  const approved = status === "APPROVED" || status === "CONFIRMED";
  const statusEditable = canWrite && !statusBusy && !pendingStatus;

  if (id) {
    return (
      <>
        <PageHeader
          eyebrow="İletişim"
          title="Randevu Detayı"
          description="Randevu bilgilerini görüntüleyin ve yönetin."
        >
          <Link to="/appointments" className="btn btn-secondary">
            <ArrowLeft size={16} />Geri dön
          </Link>
        </PageHeader>

        {loading ? (
          <div className="card"><LoadingState /></div>
        ) : error ? (
          <div className="card"><ErrorState message={error} retry={() => loadDetail(id)} /></div>
        ) : detail ? (
          <div className="card" style={{ padding: 24 }}>
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{String(detail.student_name || "-")}</h3>
              <div style={{ fontSize: 14, color: "#666" }}>{String(detail.teacher_name || "-")}</div>
            </div>
            
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Tarih ve Saat</label>
              <div style={{ padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14 }}>
                {String(detail.appointment_date || "-")} {String(detail.appointment_time || "-")}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Veli notu</label>
              <div style={{ padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14 }}>
                {String(detail.notes || "-")}
              </div>
            </div>
            {typeof detail.feedback_notes === "string" && detail.feedback_notes && <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              <strong>Öğretmen notu</strong><br />{String(detail.feedback_notes)}
            </p>}

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#666", display: "block", marginBottom: 4 }}>Durum</label>
              <p>{statusLabels[status] ?? status}</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {canWrite && !parentOnly && status === "PENDING" && <>
                  <button className="btn btn-primary" disabled={!statusEditable} onClick={() => void handleUpdateStatus({ status: "APPROVED" })}>Onayla</button>
                  <button className="btn btn-secondary" disabled={!statusEditable} onClick={() => void handleUpdateStatus({ status: "REJECTED" })}>Reddet</button>
                </>}
                {canWrite && !parentOnly && approved && <>
                  <button className="btn btn-primary" disabled={!statusEditable || feedbackDraft !== null} onClick={() => void handleUpdateStatus({ status: "COMPLETED" })}>Tamamlandı</button>
                  <button className="btn btn-secondary" disabled={!statusEditable || feedbackDraft !== null} onClick={() => setFeedbackDraft(String(detail.feedback_notes ?? ""))}>Notu düzenle</button>
                </>}
                {canWrite && parentOnly && (status === "PENDING" || approved) &&
                  <button className="btn btn-secondary" disabled={!statusEditable} onClick={() => void handleUpdateStatus({ status: "CANCELLED" })}>İptal et</button>}
              </div>
              {canWrite && !parentOnly && feedbackDraft !== null && <form onSubmit={(event) => {
                event.preventDefault();
                if (statusEditable && approved) void handleUpdateStatus({ status, feedback_notes: feedbackDraft || null });
              }}>
                <label className="field"><span>Öğretmen notu</span>
                  <textarea value={feedbackDraft} disabled={!statusEditable} onChange={(event) => setFeedbackDraft(event.target.value)} />
                </label>
                <button className="btn btn-primary" disabled={!statusEditable || !approved}>Notu kaydet</button>{" "}
                <button type="button" className="btn btn-secondary" disabled={!statusEditable} onClick={() => setFeedbackDraft(null)}>Vazgeç</button>
              </form>}
              {statusBusy && <p role="status">Randevu doğrulanıyor…</p>}
              {statusError && <p role="alert">{statusError}</p>}
              {canWrite && pendingStatus && <>
                <button className="btn btn-secondary" disabled={statusBusy} onClick={() => void handleUpdateStatus(pendingStatus, true)}>Sonucu kontrol et</button>{" "}
                <button className="btn btn-secondary" disabled={statusBusy} onClick={() => {
                  setPendingStatus(null); setStatusError(""); setFeedbackDraft(null); void loadDetail(detail.id);
                }}>Kapat ve yenile</button>
              </>}
            </div>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Randevu & PTC"
        description="Veli-öğretmen görüşme randevularını yönetin."
      >
        {canWrite && roles.includes("teacher") && (
          <button className="btn btn-secondary" onClick={() => setSlotsOpen(true)}>Uygunluk saatlerim</button>
        )}
        {canWrite && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />Yeni randevu
          </button>
        )}
      </PageHeader>

      {loading ? (
        <div className="card"><LoadingState /></div>
      ) : error ? (
        <div className="card"><ErrorState message={error} retry={() => load()} /></div>
      ) : (
        <DataTable
          rows={filtered}
          columns={[
            { key: "student_name", label: "Öğrenci" },
            { key: "teacher_name", label: "Öğretmen" },
            { key: "appointment_date", label: "Tarih", type: "date" },
            { key: "appointment_time", label: "Saat" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={search}
          onSearch={setSearch}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={load}
          detailBase="/appointments"
          canEdit={can("appointments.write")}
          onDelete={canWrite && !parentOnly ? handleDelete : undefined}
        />
      )}

      {createOpen && canWrite && <AppointmentCreateModal parent={parent} onClose={() => setCreateOpen(false)} onSuccess={() => void load()} />}
      {slotsOpen && canWrite && user && roles.includes("teacher") && (
        <AppointmentSlotsModal teacherId={user.id} onClose={() => setSlotsOpen(false)} />
      )}
    </>
  );
}

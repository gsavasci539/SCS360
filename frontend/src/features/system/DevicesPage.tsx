import { Plus, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ConfirmDialog, ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";
import { useForm } from "react-hook-form";

export function DevicesPage() {
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [filteredRows, setFilteredRows] = useState<DataRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<DataRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editDevice, setEditDevice] = useState<DataRecord | null>(null);
  const can = useAuthStore((s) => s.can);
  const write = can("settings.write");
  const { showToast } = useToast();

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<ApiResponse<DataRecord[]>>("/devices");
      setRows(response.data.data || []);
      setFilteredRows(response.data.data || []);
    } catch (err) {
      setError(apiMessage(err));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  // Search functionality
  useEffect(() => {
    if (!searchQuery) {
      setFilteredRows(rows);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredRows(
        rows.filter((row) =>
          String(row.name || "").toLowerCase().includes(query) ||
          String(row.serial_number || "").toLowerCase().includes(query) ||
          String(row.device_type || "").toLowerCase().includes(query) ||
          String(row.location || "").toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, rows]);

  function handleSearch(query: string) {
    setSearchQuery(query);
  }

  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    try {
      await api.delete(`/devices/${deleting.id}`);
      showToast("Cihaz silindi", "Cihaz başarıyla silindi.");
      setDeleting(null);
      await load();
    } catch (err) {
      showToast("İşlem tamamlanamadı", apiMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Sistem"
        title="Cihaz Yönetimi"
        description="Turnike, kart okuma cihazı ve diğer donanımları yönetin."
      />

      <div className="flex justify-end gap-2 mb-4">
        {write && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}><Plus size={16} />Cihaz Ekle</button>
        )}
      </div>

      {loading ? (
        <div className="card"><LoadingState /></div>
      ) : error ? (
        <div className="card"><ErrorState message={error} retry={load} /></div>
      ) : (
        <DataTable
          rows={filteredRows}
          columns={[
            { key: "name", label: "Cihaz Adı" },
            { key: "device_type", label: "Cihaz Tipi" },
            { key: "serial_number", label: "Seri Numarası" },
            { key: "ip_address", label: "IP Adresi" },
            { key: "location", label: "Konum" },
            { key: "status", label: "Durum", type: "status" }
          ]}
          search={searchQuery}
          onSearch={handleSearch}
          page={1}
          totalPages={1}
          total={filteredRows.length}
          onPage={() => {}}
          editBase="/devices"
          canEdit={write}
          onDelete={setDeleting}
        />
      )}

      <ConfirmDialog
        open={Boolean(deleting)}
        busy={busy}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title={`${deleting?.name} cihazını sil?`}
      />

      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} onSuccess={load} />
      <EditModal open={editDevice !== null} device={editDevice} onClose={() => setEditDevice(null)} onSuccess={load} />
    </>
  );
}

function CreateModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: {
      name: "",
      device_type: "TURNSTILE",
      serial_number: "",
      ip_address: "",
      location: "",
      notes: ""
    }
  });
  const { showToast } = useToast();

  async function submit(values: any) {
    try {
      await api.post("/devices", {
        name: values.name,
        device_type: values.device_type,
        serial_number: values.serial_number,
        ip_address: values.ip_address || undefined,
        location: values.location || undefined,
        notes: values.notes || undefined
      });
      showToast("Cihaz eklendi", "Cihaz başarıyla oluşturuldu.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal
      open={open}
      title="Cihaz Ekle"
      description="Yeni bir cihaz ekleyin."
      onClose={onClose}
      actions={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
          <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
            <Plus size={16} />Ekle
          </button>
        </>
      }
    >
      <form className="form-grid">
        <Field label="Cihaz Adı" required error={errors.name?.message as string}>
          <input {...register("name", { required: "Cihaz adı zorunludur." })} placeholder="Cihaz adını girin" />
        </Field>
        <Field label="Cihaz Tipi" required error={errors.device_type?.message as string}>
          <select {...register("device_type", { required: "Cihaz tipi zorunludur." })}>
            <option value="TURNSTILE">Turnike</option>
            <option value="CARD_READER">Kart Okuyucu</option>
            <option value="DOOR_LOCK">Kapı Kilidi</option>
            <option value="ATTENDANCE_KIOSK">Yoklama Kiosku</option>
            <option value="CANTEEN_TERMINAL">Kantin Terminali</option>
          </select>
        </Field>
        <Field label="Seri Numarası" required error={errors.serial_number?.message as string}>
          <input {...register("serial_number", { required: "Seri numarası zorunludur." })} placeholder="Seri numarasını girin" />
        </Field>
        <Field label="IP Adresi" error={errors.ip_address?.message as string}>
          <input {...register("ip_address")} placeholder="192.168.1.100" />
        </Field>
        <Field label="Konum" error={errors.location?.message as string}>
          <input {...register("location")} placeholder="Cihaz konumu" />
        </Field>
        <Field label="Notlar" error={errors.notes?.message as string}>
          <textarea {...register("notes")} rows={3} placeholder="Notlarınızı girin" />
        </Field>
      </form>
    </Modal>
  );
}

function EditModal({ open, device, onClose, onSuccess }: { open: boolean; device: DataRecord | null; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: {
      name: device?.name || "",
      device_type: device?.device_type || "TURNSTILE",
      serial_number: device?.serial_number || "",
      ip_address: device?.ip_address || "",
      location: device?.location || "",
      status: device?.status || "ACTIVE",
      notes: device?.notes || ""
    }
  });
  const { showToast } = useToast();

  async function submit(values: any) {
    if (!device) return;
    try {
      await api.put(`/devices/${device.id}`, {
        name: values.name,
        device_type: values.device_type,
        serial_number: values.serial_number,
        ip_address: values.ip_address || undefined,
        location: values.location || undefined,
        status: values.status,
        notes: values.notes || undefined
      });
      showToast("Cihaz güncellendi", "Cihaz başarıyla güncellendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  return (
    <Modal
      open={open}
      title="Cihaz Düzenle"
      description="Cihaz bilgilerini düzenleyin."
      onClose={onClose}
      actions={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
          <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
            <Settings size={16} />Kaydet
          </button>
        </>
      }
    >
      <form className="form-grid">
        <Field label="Cihaz Adı" required error={errors.name?.message as string}>
          <input {...register("name", { required: "Cihaz adı zorunludur." })} placeholder="Cihaz adını girin" />
        </Field>
        <Field label="Cihaz Tipi" required error={errors.device_type?.message as string}>
          <select {...register("device_type", { required: "Cihaz tipi zorunludur." })}>
            <option value="TURNSTILE">Turnike</option>
            <option value="CARD_READER">Kart Okuyucu</option>
            <option value="DOOR_LOCK">Kapı Kilidi</option>
            <option value="ATTENDANCE_KIOSK">Yoklama Kiosku</option>
            <option value="CANTEEN_TERMINAL">Kantin Terminali</option>
          </select>
        </Field>
        <Field label="Seri Numarası" required error={errors.serial_number?.message as string}>
          <input {...register("serial_number", { required: "Seri numarası zorunludur." })} placeholder="Seri numarasını girin" />
        </Field>
        <Field label="IP Adresi" error={errors.ip_address?.message as string}>
          <input {...register("ip_address")} placeholder="192.168.1.100" />
        </Field>
        <Field label="Konum" error={errors.location?.message as string}>
          <input {...register("location")} placeholder="Cihaz konumu" />
        </Field>
        <Field label="Durum" required error={errors.status?.message as string}>
          <select {...register("status", { required: "Durum seçilmelidir." })}>
            <option value="ACTIVE">Aktif</option>
            <option value="INACTIVE">Pasif</option>
            <option value="MAINTENANCE">Bakım</option>
            <option value="BROKEN">Bozuk</option>
          </select>
        </Field>
        <Field label="Notlar" error={errors.notes?.message as string}>
          <textarea {...register("notes")} rows={3} placeholder="Notlarınızı girin" />
        </Field>
      </form>
    </Modal>
  );
}

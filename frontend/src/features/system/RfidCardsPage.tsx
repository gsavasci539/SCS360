import { reportClientError } from "../../lib/diagnostics";
import { Plus, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ConfirmDialog, ErrorState, Field, LoadingState, Modal, PageHeader, Tabs } from "../../components/ui";
import { ExcelImport } from "../../components/ExcelImport";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { useForm } from "react-hook-form";

export function RfidCardsPage() {
  const [activeTab, setActiveTab] = useState<"cards" | "numbers" | "archived">("cards");
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [cardNumbers, setCardNumbers] = useState<DataRecord[]>([]);
  const [archivedCards, setArchivedCards] = useState<DataRecord[]>([]);
  const [filteredRows, setFilteredRows] = useState<DataRecord[]>([]);
  const [filteredCardNumbers, setFilteredCardNumbers] = useState<DataRecord[]>([]);
  const [filteredArchivedCards, setFilteredArchivedCards] = useState<DataRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<DataRecord | null>(null);
  const [deletingCardNumber, setDeletingCardNumber] = useState<DataRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [addCardNumberOpen, setAddCardNumberOpen] = useState(false);
  const [importCardNumbersOpen, setImportCardNumbersOpen] = useState(false);
  const [editCard, setEditCard] = useState<DataRecord | null>(null);
  const [searchParams] = useSearchParams();
  const holderId = searchParams.get("holder_id");
  const can = useAuthStore((s) => s.can);
  const { showToast } = useToast();
  const { id } = useParams();

  // Check if we're in edit mode
  const isEditMode = Boolean(id && window.location.pathname.includes('/edit'));

  async function load() {
    setLoading(true);
    setError("");
    try {
      if (isEditMode && id) {
        // Load single card for edit
        const response = await api.get<ApiResponse<DataRecord>>(`/rfid-cards/${id}`);
        setEditCard(response.data.data || null);
      } else if (activeTab === "cards") {
        const response = await api.get<ApiResponse<DataRecord[]>>("/rfid-cards");
        setRows(response.data.data || []);
        setFilteredRows(response.data.data || []);
      } else if (activeTab === "numbers") {
        const response = await api.get<ApiResponse<DataRecord[]>>("/card-numbers");
        setCardNumbers(response.data.data || []);
        setFilteredCardNumbers(response.data.data || []);
      } else if (activeTab === "archived") {
        const response = await api.get<ApiResponse<DataRecord[]>>("/rfid-cards?status=CANCELLED");
        setArchivedCards(response.data.data || []);
        setFilteredArchivedCards(response.data.data || []);
      }
    } catch (err) {
      setError(apiMessage(err));
      setRows([]);
      setCardNumbers([]);
      setArchivedCards([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [activeTab, id, isEditMode]);

  // Search functionality
  useEffect(() => {
    if (activeTab === "cards") {
      if (!searchQuery) {
        setFilteredRows(rows);
      } else {
        const query = searchQuery.toLowerCase();
        setFilteredRows(
          rows.filter((row) =>
            String(row.card_number || "").toLowerCase().includes(query) ||
            String(row.holder_name || "").toLowerCase().includes(query) ||
            String(row.card_type || "").toLowerCase().includes(query)
          )
        );
      }
    } else if (activeTab === "numbers") {
      if (!searchQuery) {
        setFilteredCardNumbers(cardNumbers);
      } else {
        const query = searchQuery.toLowerCase();
        setFilteredCardNumbers(
          cardNumbers.filter((row) =>
            String(row.card_number || "").toLowerCase().includes(query) ||
            String(row.supplier || "").toLowerCase().includes(query)
          )
        );
      }
    } else if (activeTab === "archived") {
      if (!searchQuery) {
        setFilteredArchivedCards(archivedCards);
      } else {
        const query = searchQuery.toLowerCase();
        setFilteredArchivedCards(
          archivedCards.filter((row) =>
            String(row.card_number || "").toLowerCase().includes(query) ||
            String(row.holder_name || "").toLowerCase().includes(query)
          )
        );
      }
    }
  }, [searchQuery, rows, cardNumbers, archivedCards, activeTab]);

  function handleSearch(query: string) {
    setSearchQuery(query);
  }

  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    try {
      await api.delete(`/rfid-cards/${deleting.id}`);
      showToast("RFID kartı silindi", "Kart başarıyla silindi.");
      setDeleting(null);
      await load();
    } catch (err) {
      showToast("İşlem tamamlanamadı", apiMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDeleteCardNumber() {
    if (!deletingCardNumber) return;
    setBusy(true);
    try {
      await api.delete(`/card-numbers/${deletingCardNumber.id}`);
      showToast("Kart numarası silindi", "Kart numarası başarıyla silindi.");
      setDeletingCardNumber(null);
      await load();
    } catch (err) {
      showToast("İşlem tamamlanamadı", apiMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  const write = can("settings.write");

  return (
    <>
      <PageHeader
        eyebrow="Sistem"
        title="RFID Kart Yönetimi"
        description="RFID kartlarını ve kart numaralarını yönetin."
      />

      <Tabs
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab as "cards" | "numbers" | "archived")}
        tabs={[
          { id: "cards", label: "RFID Kartlar" },
          { id: "numbers", label: "Kart Numaraları" },
          { id: "archived", label: "Arşivlenen Kartlar" }
        ]}
      />

      {activeTab === "cards" && (
        <>
          <div className="flex justify-end gap-2 mb-4">
            {write && (
              <>
                <button className="btn btn-primary" onClick={() => setCreateOpen(true)}><Plus size={16} />Kart Ekle</button>
                <button className="btn btn-secondary" onClick={() => setImportOpen(true)}><Upload size={16} />Toplu İçe Aktar</button>
              </>
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
                { key: "card_number", label: "Kart Numarası" },
                { key: "card_type", label: "Kart Tipi" },
                { key: "holder_name", label: "Kart Sahibi" },
                { key: "status", label: "Durum", type: "status" },
                { key: "issue_date", label: "Verme Tarihi", type: "date" },
                { key: "expiry_date", label: "Son Kullanma", type: "date" }
              ]}
              search={searchQuery}
              onSearch={handleSearch}
              page={1}
              totalPages={1}
              total={filteredRows.length}
              onPage={() => {}}
              editBase="/rfid-cards"
              canEdit={write}
              onDelete={setDeleting}
            />
          )}
        </>
      )}

      {activeTab === "numbers" && (
        <>
          <div className="flex justify-end gap-2 mb-4">
            {write && (
              <>
                <button className="btn btn-primary" onClick={() => setAddCardNumberOpen(true)}><Plus size={16} />Kart Numarası Ekle</button>
                <button className="btn btn-secondary" onClick={() => setImportCardNumbersOpen(true)}><Upload size={16} />Excel ile Yükle</button>
              </>
            )}
          </div>

          {loading ? (
            <div className="card"><LoadingState /></div>
          ) : error ? (
            <div className="card"><ErrorState message={error} retry={load} /></div>
          ) : (
            <DataTable
              rows={filteredCardNumbers}
              columns={[
                { key: "card_number", label: "Kart Numarası" },
                { key: "status", label: "Durum", type: "status" },
                { key: "supplier", label: "Tedarikçi" },
                { key: "purchased_date", label: "Satın Alma Tarihi", type: "date" },
                { key: "notes", label: "Notlar" }
              ]}
              search={searchQuery}
              onSearch={handleSearch}
              page={1}
              totalPages={1}
              total={filteredCardNumbers.length}
              onPage={() => {}}
              canEdit={false}
              onDelete={setDeletingCardNumber}
            />
          )}
        </>
      )}

      {activeTab === "archived" && (
        <>
          <div className="flex justify-end gap-2 mb-4">
            <p className="text-sm text-gray-600">İptal edilen, mezun olan veya işten ayrılan kişilerin kartları burada görüntülenir.</p>
          </div>

          {loading ? (
            <div className="card"><LoadingState /></div>
          ) : error ? (
            <div className="card"><ErrorState message={error} retry={load} /></div>
          ) : (
            <DataTable
              rows={filteredArchivedCards}
              columns={[
                { key: "card_number", label: "Kart Numarası" },
                { key: "card_type", label: "Kart Tipi" },
                { key: "holder_name", label: "Kart Sahibi" },
                { key: "status", label: "Durum", type: "status" },
                { key: "issue_date", label: "Verme Tarihi", type: "date" },
                { key: "updated_at", label: "İptal Tarihi", type: "date" }
              ]}
              search={searchQuery}
              onSearch={handleSearch}
              page={1}
              totalPages={1}
              total={filteredArchivedCards.length}
              onPage={() => {}}
              canEdit={false}
              onDelete={undefined}
            />
          )}
        </>
      )}

      <ConfirmDialog
        open={Boolean(deleting)}
        busy={busy}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title={`${deleting?.card_number} kartını sil?`}
      />

      <ConfirmDialog
        open={Boolean(deletingCardNumber)}
        busy={busy}
        onCancel={() => setDeletingCardNumber(null)}
        onConfirm={confirmDeleteCardNumber}
        title={`${deletingCardNumber?.card_number} kart numarasını sil?`}
      />

      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} onSuccess={load} holderId={holderId} />
      <EditModal open={isEditMode && editCard !== null} card={editCard} onClose={() => window.location.href = '/rfid-cards'} onSuccess={() => window.location.href = '/rfid-cards'} />
      <ExcelImport
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={load}
        endpoint="/import/rfid-cards"
        title="RFID Kart Toplu İçe Aktarma"
        description="Excel dosyasından RFID kartlarını toplu olarak içe aktarın. Kart numaraları manuel girilmelidir."
        templateColumns={[
          { key: "card_number", label: "Kart Numarası", required: true },
          { key: "holder_id", label: "Kart Sahibi ID", required: true },
          { key: "card_type", label: "Kart Tipi", required: true }
        ]}
      />

      <AddCardNumberModal open={addCardNumberOpen} onClose={() => setAddCardNumberOpen(false)} onSuccess={load} />
      <ExcelImport
        open={importCardNumbersOpen}
        onClose={() => setImportCardNumbersOpen(false)}
        onSuccess={load}
        endpoint="/import/card-numbers"
        title="Kart Numaraları Excel İçe Aktarma"
        description="Excel dosyasından kart numaralarını toplu olarak içe aktarın."
        templateColumns={[
          { key: "card_number", label: "Kart Numarası", required: true },
          { key: "notes", label: "Notlar", required: false },
          { key: "purchased_date", label: "Satın Alma Tarihi", required: false },
          { key: "supplier", label: "Tedarikçi", required: false }
        ]}
      />
    </>
  );
}

function CreateModal({ open, onClose, onSuccess, holderId }: { open: boolean; onClose: () => void; onSuccess: () => void; holderId?: string | null }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: {
      card_number_id: "",
      holder_id: holderId || ""
    }
  });
  const { showToast } = useToast();
  const [students, setStudents] = useState<DataRecord[]>([]);
  const [staff, setStaff] = useState<DataRecord[]>([]);
  const [cardNumbers, setCardNumbers] = useState<DataRecord[]>([]);
  const [selectedType, setSelectedType] = useState<"STUDENT" | "STAFF">("STUDENT");

  useEffect(() => {
    async function loadOptions() {
      try {
        const [studentsRes, staffRes, cardNumbersRes, rfidCardsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/students", { params: { page_size: 100, limit: 100 } }),
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/users", { params: { page_size: 100, limit: 100 } }),
          api.get<ApiResponse<DataRecord[]>>("/card-numbers/available"),
          api.get<ApiResponse<DataRecord[]>>("/rfid-cards")
        ]);
        
        const studentsData = studentsRes.data.data;
        const staffData = staffRes.data.data;
        const cardNumbersData = cardNumbersRes.data.data;
        const rfidCardsData = rfidCardsRes.data.data;
        
        // Get IDs of holders who have ACTIVE cards (cancelled cards can be reassigned)
        const activeHolderIds = new Set(
          Array.isArray(rfidCardsData) 
            ? rfidCardsData.filter((card: DataRecord) => card.status === "ACTIVE").map((card: DataRecord) => card.holder_id) 
            : []
        );
        
        // Filter out holders who have ACTIVE cards (allow cancelled card holders)
        const allStudents = Array.isArray(studentsData) ? studentsData : studentsData?.items || [];
        const allStaff = Array.isArray(staffData) ? staffData : staffData?.items || [];
        
        setStudents(allStudents.filter((s: DataRecord) => !activeHolderIds.has(s.id)));
        setStaff(allStaff.filter((s: DataRecord) => !activeHolderIds.has(s.id)));
        setCardNumbers(Array.isArray(cardNumbersData) ? cardNumbersData : []);
      } catch (e) {
        reportClientError("Failed to load options", e);
        showToast("Yükleme hatası", "Öğrenci, personel ve kart numaraları listesi yüklenemedi.", "error");
      }
    }
    if (open) loadOptions();
  }, [open, showToast]);

  async function submit(values: any) {
    try {
      // Find the selected holder's name
      const holders = selectedType === "STUDENT" ? students : staff;
      const selectedHolder = holders.find((h: DataRecord) => h.id === values.holder_id);
      const holderName = selectedHolder 
        ? `${String(selectedHolder.first_name || "")} ${String(selectedHolder.last_name || "")}` 
        : "Bilinmiyor";

      await api.post("/rfid-cards", {
        card_number_id: values.card_number_id,
        holder_id: values.holder_id,
        holder_name: holderName,
        card_type: selectedType
      });
      showToast("Kart oluşturuldu", "RFID kartı başarıyla eklendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  const holders = selectedType === "STUDENT" ? students : staff;

  return (
    <Modal
      open={open}
      title="RFID Kart Ekle"
      description="Kart numarasını seçin ve kart sahibini atayın."
      onClose={onClose}
      actions={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
          <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
            <Plus size={16} />Oluştur
          </button>
        </>
      }
    >
      <form className="form-grid">
        <Field label="Kart Numarası" required error={errors.card_number_id?.message as string}>
          <select {...register("card_number_id", { required: "Kart numarası seçilmelidir." })}>
            <option value="">Seçiniz</option>
            {cardNumbers.map((card) => (
              <option key={card.id} value={card.id}>
                {String(card.card_number)} {card.supplier ? `(${card.supplier})` : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Kart Tipi" required>
          <select value={selectedType} onChange={(e) => setSelectedType(e.target.value as "STUDENT" | "STAFF")}>
            <option value="STUDENT">Öğrenci</option>
            <option value="STAFF">Personel</option>
          </select>
        </Field>
        <Field label="Kart Sahibi" required error={errors.holder_id?.message as string}>
          <select {...register("holder_id", { required: "Kart sahibi seçilmelidir." })}>
            <option value="">Seçiniz</option>
            {holders.map((holder) => (
              <option key={holder.id} value={holder.id}>
                {String(holder.first_name || "")} {String(holder.last_name || "")} ({String(holder.student_number || holder.email || holder.id)})
              </option>
            ))}
          </select>
        </Field>
      </form>
    </Modal>
  );
}

function AddCardNumberModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: {
      card_number: "",
      notes: "",
      purchased_date: "",
      supplier: ""
    }
  });
  const { showToast } = useToast();

  async function submit(values: any) {
    try {
      await api.post("/card-numbers", {
        card_number: values.card_number,
        notes: values.notes || undefined,
        purchased_date: values.purchased_date || undefined,
        supplier: values.supplier || undefined
      });
      showToast("Kart numarası eklendi", "Kart numarası başarıyla oluşturuldu.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Oluşturulamadı", apiMessage(e), "error");
    }
  }

  return (
    <Modal
      open={open}
      title="Kart Numarası Ekle"
      description="Yeni bir kart numarası ekleyin."
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
        <Field label="Kart Numarası" required error={errors.card_number?.message as string}>
          <input {...register("card_number", { required: "Kart numarası zorunludur." })} placeholder="RFID kart numarasını girin" />
        </Field>
        <Field label="Tedarikçi" error={errors.supplier?.message as string}>
          <input {...register("supplier")} placeholder="Tedarikçi adı" />
        </Field>
        <Field label="Satın Alma Tarihi" error={errors.purchased_date?.message as string}>
          <input {...register("purchased_date")} type="date" />
        </Field>
        <Field label="Notlar" error={errors.notes?.message as string}>
          <textarea {...register("notes")} rows={3} placeholder="Notlarınızı girin" />
        </Field>
      </form>
    </Modal>
  );
}

function EditModal({ open, card, onClose, onSuccess }: { open: boolean; card: DataRecord | null; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: {
      status: card?.status || "ACTIVE",
      expiry_date: card?.expiry_date || ""
    }
  });
  const { showToast } = useToast();

  async function submit(values: any) {
    if (!card) return;
    try {
      await api.put(`/rfid-cards/${card.id}`, {
        status: values.status,
        expiry_date: values.expiry_date || undefined
      });
      showToast("Kart güncellendi", "RFID kartı başarıyla güncellendi.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("Güncellenemedi", apiMessage(e), "error");
    }
  }

  return (
    <Modal
      open={open}
      title="RFID Kart Düzenle"
      description="RFID kart durumunu ve son kullanma tarihini düzenleyin."
      onClose={onClose}
      actions={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Vazgeç</button>
          <button className="btn btn-primary" disabled={isSubmitting} onClick={handleSubmit(submit)}>
            Kaydet
          </button>
        </>
      }
    >
      <form className="form-grid">
        <Field label="Kart Numarası">
          <input value={String(card?.card_number || "")} disabled />
        </Field>
        <Field label="Kart Sahibi">
          <input value={String(card?.holder_name || "")} disabled />
        </Field>
        <Field label="Durum" required error={errors.status?.message as string}>
          <select {...register("status", { required: "Durum seçilmelidir." })}>
            <option value="ACTIVE">Aktif</option>
            <option value="INACTIVE">Pasif</option>
            <option value="BLOCKED">Engelli</option>
            <option value="CANCELLED">İptal</option>
          </select>
        </Field>
        <Field label="Son Kullanma Tarihi" error={errors.expiry_date?.message as string}>
          <input {...register("expiry_date")} type="date" />
        </Field>
      </form>
    </Modal>
  );
}

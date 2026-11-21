import { useEffect, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { deleteOutboxRecord, outboxStatuses } from "./outboxRecords";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => 
  Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export function OutboxPage() {
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 });
  const [search, setSearch] = useState("");
  const [channel, setChannel] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [deleting, setDeleting] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { showToast } = useToast();
  const can = useAuthStore((state) => state.can);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const timer = window.setTimeout(() => {
      api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/outbox", {
        params: { page, page_size: 20, search: search.trim() || undefined, channel: channel || undefined, status: status || undefined },
        signal: controller.signal,
      }).then((response) => { if (!controller.signal.aborted) setData(normalize(response.data.data)); })
        .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, search ? 250 : 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [page, search, channel, status, revision]);

  async function handleDelete(row: DataRecord) {
    if (!can("notification.write") || deleting || !window.confirm("Gönderim kaydı kaldırılsın mı?")) return;
    setDeleting(row.id);
    try {
      await deleteOutboxRecord(row);
      showToast("Gönderim kaydı kaldırıldı");
      if (data.items.length === 1 && page > 1) setPage((previous) => previous - 1);
      else setRevision((previous) => previous + 1);
    } catch (e) {
      showToast("Silinemedi", apiMessage(e), "error");
    } finally { setDeleting(""); }
  }

  return (
    <>
      <PageHeader
        eyebrow="İletişim"
        title="Giden Kutusu (Outbox)"
        description="Kuyruğa alınan iletilerin durumunu inceleyin."
      />

        <DataTable
          rows={data.items.map((row) => ({ ...row, status: outboxStatuses[String(row.status)] || row.status }))}
          columns={[
            { key: "recipient", label: "Alıcı" },
            { key: "subject", label: "Konu" },
            { key: "type", label: "Tür" },
            { key: "sent_at", label: "Gönderim Tarihi", type: "date" },
            { key: "status", label: "Durum" }
          ]}
          search={search}
          onSearch={(value) => { setSearch(value.slice(0, 100)); setPage(1); }}
          status={loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((previous) => previous + 1)} /> : undefined}
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={setPage}
          detailBase="/outbox"
          canEdit={can("notification.write") && !deleting}
          onDelete={can("notification.write") ? handleDelete : undefined}
          filters={<>
            <select className="filter-select" aria-label="Kanal" value={channel} onChange={(event) => { setChannel(event.target.value); setPage(1); }}>
              <option value="">Tüm kanallar</option><option value="EMAIL">E-posta</option><option value="SMS">SMS</option><option value="WHATSAPP">WhatsApp</option>
            </select>
            <select className="filter-select" aria-label="Durum" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
              <option value="">Tüm durumlar</option>{Object.entries(outboxStatuses).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
          </>}
        />
    </>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ReceiptText } from "lucide-react";
import { DataTable } from "../../components/DataTable";
import { ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { getAnalysis } from "../../lib/analysis";
import { money } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { PaymentForecastCard } from "./PaymentForecastCard";

export function PaymentListPage() {
  const can = useAuthStore((state) => state.can), { showToast } = useToast();
  const [data, setData] = useState<Paginated<DataRecord>>({ items: [], total: 0, total_pages: 0, page: 1, page_size: 20 });
  const [page, setPage] = useState(1), [search, setSearch] = useState(""), [status, setStatus] = useState("ALL");
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [revision, setRevision] = useState(0);
  const [ready, setReady] = useState(false);
  const [selected, setSelected] = useState<DataRecord | null>(null), [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false), [cancelError, setCancelError] = useState("");
  const [summary, setSummary] = useState<DataRecord | null>(null), [summaryError, setSummaryError] = useState("");
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get<ApiResponse<Paginated<DataRecord>>>("/payments", { params: { page, page_size: 20, search: search || undefined, status }, signal: controller.signal })
      .then((reply) => { if (!controller.signal.aborted) { setData(reply.data.data); setReady(true); if (reply.data.data.total_pages > 0 && page > reply.data.data.total_pages) setPage(reply.data.data.total_pages); } })
      .catch((failure) => { if (!controller.signal.aborted) setError(apiMessage(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, search, status, revision]);
  useEffect(() => {
    const controller = new AbortController(); setSummary(null); setSummaryError("");
    getAnalysis("/ai/payment-forecast", { signal: controller.signal }).then((reply) => { if (!controller.signal.aborted) setSummary(reply.data.data); })
      .catch(() => { if (!controller.signal.aborted) setSummaryError("Tahsilat özeti alınamadı."); });
    return () => controller.abort();
  }, [revision]);
  async function cancel() {
    if (!selected || busy) return; setBusy(true); setCancelError("");
    try {
      await api.post(`/payments/${selected.id}/cancel`, { cancel_reason: reason.trim() || null });
      showToast("Ödeme iptal edildi", "Borç bakiyesi yeniden hesaplandı."); setSelected(null); setRevision((value) => value + 1);
    } catch (failure) { setCancelError(apiMessage(failure)); } finally { setBusy(false); }
  }
  return <>
    <PageHeader eyebrow="Finans" title="Tahsilatlar" description="Ödeme geçmişini arayın, makbuzları inceleyin ve seçilen işlemi yönetin.">
      {(can("finance.read") || can("finance.write")) && <Link className="btn btn-secondary" to="/finance/online-payments">Online ödeme incelemesi</Link>}
      {(can("finance.write") || can("finance.collect_payment")) && <Link className="btn btn-primary" to="/finance/payments/new"><ReceiptText size={16} />Tahsilat al</Link>}
    </PageHeader>
    {summary && <PaymentForecastCard summary={summary} />}
    {summaryError && <p>{summaryError} <button className="btn btn-secondary" onClick={() => setRevision((value) => value + 1)}>Özeti tekrar dene</button></p>}
    {error && <div className="card"><ErrorState message={error} retry={() => setRevision((value) => value + 1)} /></div>}
    {loading && !ready ? <div className="card"><LoadingState /></div> : ready && <>
      {loading && <p role="status">Filtre uygulanıyor…</p>}
      <DataTable rows={error ? [] : data.items} columns={[{ key: "student_name", label: "Öğrenci", subKey: "student_id" }, { key: "amount", label: "Tutar", type: "money" },
        { key: "payment_method", label: "Yöntem" }, { key: "payment_date", label: "Tarih", type: "date" }, { key: "status", label: "Durum", type: "status" }]}
        search={search} onSearch={(value) => { setSearch(value); setPage(1); }} page={page} totalPages={data.total_pages} total={data.total} onPage={setPage}
        detailBase="/finance/payments" canEdit={false}
        filters={<Field label="Tahsilat durumu"><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
          <option value="ALL">Tümü</option><option value="ACTIVE">İptal edilmeyen</option><option value="CANCELLED">İptal</option>
        </select></Field>}
        rowActions={(row) => row.requires_provider_refund && !row.cancelled ? <span>Sağlayıcı mutabakatı</span> : row.requires_review ? <span>Eski tutar incelenmeli</span> :
          can("finance.write") && !row.cancelled && row.status === "COMPLETED" ? <button className="btn btn-danger" disabled={busy || loading} onClick={() => { setSelected(row); setReason(""); setCancelError(""); }}>İptal et</button> : null}
      /></>}
    <Modal open={Boolean(selected)} title="Tahsilat iptali" description="Seçilen işlem ters kayıtla iptal edilir; geçmişi korunur." onClose={() => { if (!busy) setSelected(null); }}
      actions={<><button className="btn btn-secondary" disabled={busy} onClick={() => setSelected(null)}>Vazgeç</button><button className="btn btn-danger" disabled={busy} onClick={cancel}>{busy ? "İptal ediliyor…" : "İptal et"}</button></>}>
      <p><strong>{String(selected?.student_name ?? selected?.student_id ?? "")}</strong> · {money(selected?.amount)}</p>
      {cancelError && <p role="alert">{cancelError}</p>}
      <Field label="İptal nedeni"><textarea value={reason} maxLength={2000} disabled={busy} onChange={(event) => setReason(event.target.value)} /></Field>
    </Modal>
  </>;
}

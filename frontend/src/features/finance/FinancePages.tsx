import { PaymentForecastCard } from "./PaymentForecastCard";
import { getAnalysis } from "../../lib/analysis";
import { ArrowLeft, Download, Eye, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { BrandMark } from "../../components/Brand";
import { useToast } from "../../components/Toast";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { money, shortDate } from "../../lib/format";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

const normalize = (data: DataRecord[] | Paginated<DataRecord>): Paginated<DataRecord> => Array.isArray(data) ? { items: data, total: data.length, page: 1, page_size: data.length, total_pages: 1 } : data;

export { PaymentListPage as PaymentsPage } from "./PaymentListPage";


export { CashCollectionPage as PaymentFormPage } from "./CashCollectionPage";

export function ReceiptsPage() {
  const [rows, setRows] = useState<DataRecord[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [search, setSearch] = useState(""); const [aiInsights, setAiInsights] = useState<any>(null);
  useEffect(() => { api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/receipts", { params: { page_size: 100 } }).then((r) => setRows(normalize(r.data.data).items)).catch((e) => setError(apiMessage(e))).finally(() => setLoading(false)); getAnalysis("/ai/payment-forecast").then((r) => setAiInsights(r.data.data)).catch(() => {}); }, []);
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(search.toLowerCase()));
  return <><PageHeader eyebrow="Finans" title="Makbuzlar" description="Tahsilatların resmi belgelerini görüntüleyin, indirin veya yazdırın." />{aiInsights && <PaymentForecastCard summary={aiInsights} />}{loading ? <div className="card"><LoadingState /></div> : error ? <div className="card"><ErrorState message={error} /></div> : <DataTable rows={filtered} columns={[{ key: "receipt_number", label: "Makbuz no" }, { key: "issued_at", label: "Düzenlenme", type: "date" }, { key: "remaining_debt", label: "Kalan borç", type: "money" }, { key: "status", label: "Durum", type: "status" }]} search={search} onSearch={setSearch} page={1} totalPages={1} total={filtered.length} onPage={() => {}} detailBase="/finance/receipts" />}</>;
}

export function ReceiptDetailPage() {
  const { id } = useParams(); const [record, setRecord] = useState<DataRecord | null>(null); const [error, setError] = useState(""); const [aiInsights, setAiInsights] = useState<any>(null); const { showToast } = useToast();
  useEffect(() => { api.get<ApiResponse<DataRecord>>(`/receipts/${id}`).then((r) => setRecord(r.data.data)).catch((e) => setError(apiMessage(e))); getAnalysis("/ai/payment-forecast").then((r) => setAiInsights(r.data.data)).catch(() => {}); }, [id]);
  async function download(path: string) { try { const response = await api.get(path, { responseType: "blob" }); const url = URL.createObjectURL(response.data); try { const a = document.createElement("a"); a.href = url; a.download = `${record?.receipt_number || "makbuz"}.pdf`; a.click(); } finally { URL.revokeObjectURL(url); } } catch (e) { showToast("Makbuz indirilemedi", apiMessage(e), "error"); } }
  if (error) return <div className="card"><ErrorState message={error} /></div>; if (!record) return <div className="card"><LoadingState /></div>;
  return <><PageHeader eyebrow="Makbuz" title={String(record.receipt_number)} description="Tahsilata ait doğrulanmış belge bilgileri."><Link className="btn btn-secondary" to="/finance/receipts"><ArrowLeft size={16} />Listeye dön</Link><button className="btn btn-secondary" onClick={() => download(`/receipts/${id}/pdf`)}><Download size={16} />PDF indir</button><Link className="btn btn-primary" to={`/finance/receipts/${id}/print`}><Printer size={16} />Yazdır</Link></PageHeader>{aiInsights && <PaymentForecastCard summary={aiInsights} />}<div className="card form-card"><div style={{ display: "flex", alignItems: "center", gap: 13, paddingBottom: 20, borderBottom: "1px solid var(--line)" }}><BrandMark /><div><strong style={{ font: "800 18px Manrope" }}>SCS360 Tahsilat Makbuzu</strong><div className="cell-sub">Belge no: {String(record.receipt_number)}</div></div></div><div className="detail-list" style={{ marginTop: 24 }}><div className="detail-item"><small>Düzenlenme tarihi</small><strong>{shortDate(record.issued_at)}</strong></div><div className="detail-item"><small>Durum</small><strong>{String(record.status)}</strong></div><div className="detail-item"><small>Ödeme kaydı</small><strong>{String(record.payment_id)}</strong></div><div className="detail-item"><small>Kalan borç</small><strong>{money(record.remaining_debt)}</strong></div></div></div></>;
}

export function PaymentDetailPage() {
  const { id } = useParams(); const [record, setRecord] = useState<DataRecord | null>(null); const [error, setError] = useState(""); const [aiInsights, setAiInsights] = useState<any>(null);
  useEffect(() => { api.get<ApiResponse<DataRecord>>(`/payments/${id}`).then((r) => setRecord(r.data.data)).catch((e) => setError(apiMessage(e))); getAnalysis("/ai/payment-forecast").then((r) => setAiInsights(r.data.data)).catch(() => {}); }, [id]);
  if (error) return <ErrorState message={error} />; if (!record) return <LoadingState />;
  return <><PageHeader eyebrow="Tahsilat" title={money(record.amount)} description={`${shortDate(record.payment_date)} tarihli ödeme kaydı.`}><Link className="btn btn-secondary" to="/finance/payments"><ArrowLeft size={16} />Listeye dön</Link>{record.receipt_id && <Link className="btn btn-primary" to={`/finance/receipts/${record.receipt_id}`}><Eye size={16} />Makbuzu aç</Link>}</PageHeader>{aiInsights && <PaymentForecastCard summary={aiInsights} />}<div className="card form-card detail-list">{Object.entries(record).filter(([key]) => !key.includes("id")).map(([key, value]) => <div className="detail-item" key={key}><small>{key.replaceAll("_", " ")}</small><strong>{String(value ?? "—")}</strong></div>)}</div></>;
}

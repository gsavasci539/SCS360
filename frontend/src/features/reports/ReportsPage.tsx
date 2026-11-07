import { getAnalysis } from "../../lib/analysis";
import { reportClientError } from "../../lib/diagnostics";
import { Download, FileSpreadsheet, Printer, TrendingUp, AlertTriangle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { money } from "../../lib/format";
import { printReport, type PrintColumn } from "../../lib/print";
import type { ApiResponse, Paginated } from "../../types/api";

type ReportRow = Record<string, unknown>;

interface ReportDefinition {
  key: string;
  label: string;
  columns: PrintColumn[];
}

const moneyColumn = (key: string, label: string): PrintColumn => ({ key, label, format: (value) => money(Number(value || 0)) });
const tabs: ReportDefinition[] = [
  { key: "monthly-payments", label: "Aylık tahsilat", columns: [{ key: "month", label: "Dönem" }, { key: "branch_name", label: "Şube" }, moneyColumn("total_amount", "Tahsilat"), { key: "payment_count", label: "İşlem" }] },
  { key: "debts", label: "Borçlar", columns: [{ key: "student_name", label: "Öğrenci" }, { key: "debt_type", label: "Tür" }, moneyColumn("amount", "Toplam"), moneyColumn("paid_amount", "Ödenen"), moneyColumn("remaining_amount", "Kalan"), { key: "status", label: "Durum" }] },
  { key: "overdue-debts", label: "Geciken borçlar", columns: [{ key: "student_name", label: "Öğrenci" }, { key: "branch_name", label: "Şube" }, moneyColumn("remaining_amount", "Kalan"), { key: "due_date", label: "Vade" }, { key: "days_overdue", label: "Gecikme (gün)" }] },
  { key: "attendance", label: "Devamsızlık", columns: [{ key: "date", label: "Tarih" }, { key: "student_name", label: "Öğrenci" }, { key: "class_name", label: "Sınıf" }, { key: "status", label: "Durum" }] },
  { key: "class-occupancy", label: "Sınıf doluluğu", columns: [{ key: "class_name", label: "Sınıf" }, { key: "branch_name", label: "Şube" }, { key: "student_count", label: "Öğrenci" }, { key: "capacity", label: "Kapasite" }, { key: "occupancy_rate", label: "Doluluk (%)" }] },
  { key: "branch-performance", label: "Şube performansı", columns: [{ key: "branch_name", label: "Şube" }, { key: "total_students", label: "Öğrenci" }, { key: "new_students", label: "Yeni kayıt" }, moneyColumn("total_revenue", "Tahsilat"), { key: "attendance_rate", label: "Katılım (%)" }] },
];

function reportRows(data: unknown, type: string): ReportRow[] {
  const rows = toArray(data as ReportRow[] | Paginated<ReportRow>);
  if (rows.length) return rows;
  if (!data || typeof data !== "object") return [];
  const record = data as ReportRow;
  if (type === "monthly-payments" && (record.total !== undefined || record.count !== undefined)) {
    return [{ month: `${record.year ?? ""}-${String(record.month ?? "").padStart(2, "0")}`, total_amount: record.total ?? 0, payment_count: record.count ?? 0 }];
  }
  if (type === "debts" && record.by_status && typeof record.by_status === "object") {
    return Object.entries(record.by_status as Record<string, unknown>).map(([status, count]) => ({ status, count }));
  }
  return [];
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportsPage() {
  const [tab, setTab] = useState(tabs[0].key);
  const [data, setData] = useState<unknown>({});
  const [branches, setBranches] = useState<ReportRow[]>([]);
  const [branchId, setBranchId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const now = useMemo(() => new Date(), []);
  const definition = tabs.find((item) => item.key === tab) || tabs[0];

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<ApiResponse<unknown>>(`/reports/${tab}`, {
        params: { year: now.getFullYear(), month: now.getMonth() + 1, branch_id: branchId || undefined },
      });
      setData(response.data.data ?? {});
    } catch (err) {
      setData({});
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const loadAiAnalysis = async () => {
    try {
      const response = await getAnalysis<any>("/ai/insights-report");
      if (response.data.success) {
        setAiAnalysis(response.data.data);
      }
    } catch (err) {
      reportClientError("Failed to load AI analysis:", err);
    }
  };

  useEffect(() => { load(); loadAiAnalysis(); }, [tab, branchId]);
  useEffect(() => {
    api.get<ApiResponse<ReportRow[] | Paginated<ReportRow>>>("/branches", { params: { page_size: 100, limit: 100 } })
      .then((response) => setBranches(toArray(response.data.data)))
      .catch(() => setBranches([]));
  }, []);

  const rows = reportRows(data, tab);
  const scalarSummary = data && typeof data === "object" && !Array.isArray(data)
    ? Object.entries(data as ReportRow).filter(([, value]) => ["string", "number"].includes(typeof value)).slice(0, 6)
    : [];
  const chartRows = rows.length
    ? rows.slice(0, 12).map((row, index) => ({
      name: String(row.name || row.month || row.branch_name || row.class_name || row.student_name || index + 1),
      tahsilat: Number(row.total_amount || row.total_revenue || row.collection || row.amount || row.total || 0),
      borc: Number(row.remaining_amount || row.debt || row.remaining || row.overdue || 0),
    }))
    : [{ name: "Veri yok", tahsilat: 0, borc: 0 }];

  function handlePrint() {
    setError("");
    try {
      printReport({
        title: definition.label,
        subtitle: `${now.toLocaleDateString("tr-TR", { month: "long", year: "numeric" })} dönemi`,
        columns: definition.columns,
        rows,
        summary: scalarSummary.map(([key, value]) => ({ label: key.replaceAll("_", " "), value: String(value) })),
      });
    } catch (err) {
      setError(apiMessage(err));
    }
  }

  async function exportReport(format: "csv" | "excel") {
    setError("");
    try {
      const response = await api.get<Blob>(`/reports/export/${format}`, {
        params: { report_type: tab, year: now.getFullYear(), month: now.getMonth() + 1, branch_id: branchId || undefined },
        responseType: "blob",
      });
      const contentType = String(response.headers["content-type"] || "");
      if (contentType.includes("application/json")) {
        const payload = JSON.parse(await response.data.text()) as ApiResponse<{ content: string; filename?: string; encoding?: string }>;
        const result = payload.data;
        if (!result?.content) throw new Error("Dışa aktarılacak veri bulunamadı.");
        const bytes = result.encoding === "base64"
          ? Uint8Array.from(atob(result.content), (char) => char.charCodeAt(0))
          : result.content;
        downloadBlob(new Blob([bytes]), result.filename || `${tab}.${format === "excel" ? "xlsx" : "csv"}`);
      } else {
        downloadBlob(response.data, `${tab}.${format === "excel" ? "xlsx" : "csv"}`);
      }
    } catch (err) {
      setError(apiMessage(err));
    }
  }

  return <>
    <PageHeader eyebrow="Analiz" title="Raporlar" description="Kurum performansını ölçün; sonuçları paylaşılabilir formatlarda dışa aktarın.">
      <button className="btn btn-secondary" onClick={handlePrint} disabled={loading}><Printer size={16} />Yazdır</button>
      <button className="btn btn-secondary" onClick={() => exportReport("csv")} disabled={loading}><Download size={16} />CSV</button>
      <button className="btn btn-primary" onClick={() => exportReport("excel")} disabled={loading}><FileSpreadsheet size={16} />Excel</button>
    </PageHeader>
    {aiAnalysis && (
      <div className="card" style={{ marginBottom: 18 }}>
        <div className="card-head">
          <div>
            <h2>AI Rapor Analizi</h2>
            <p>Veri odaklı öngörüler ve öneriler</p>
          </div>
          <TrendingUp size={20} color="#176b5b" />
        </div>
        <div className="card-pad">
          {aiAnalysis.priority_actions && aiAnalysis.priority_actions.length > 0 && (
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Öncelikli Aksiyonlar</h3>
              {aiAnalysis.priority_actions.slice(0, 3).map((action: string, index: number) => (
                <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                  <AlertTriangle size={16} color={index === 0 ? "#dc2626" : "#176b5b"} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span style={{ fontSize: 13 }}>{action}</span>
                </div>
              ))}
            </div>
          )}
          {aiAnalysis.key_insights && aiAnalysis.key_insights.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Temel İçgörüler</h3>
              {aiAnalysis.key_insights.slice(0, 3).map((insight: string, index: number) => (
                <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                  <TrendingUp size={16} color="#176b5b" style={{ flexShrink: 0, marginTop: 2 }} />
                  <span style={{ fontSize: 13 }}>{insight}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )}
    <section className="card">
      <div className="card-head"><div><h2>Rapor görünümü</h2><p>{now.toLocaleDateString("tr-TR", { month: "long", year: "numeric" })} dönemi</p></div>
        <select className="filter-select" value={branchId} onChange={(event) => setBranchId(event.target.value)} aria-label="Şube seç">
          <option value="">Tüm şubeler</option>
          {branches.map((branch) => <option value={String(branch.id)} key={String(branch.id)}>{String(branch.name || "Şube")}</option>)}
        </select>
      </div>
      <div className="report-tabs">{tabs.map((item) => <button className={`report-tab${tab === item.key ? " active" : ""}`} onClick={() => setTab(item.key)} key={item.key}>{item.label}</button>)}</div>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={load} /> : <>
        <div className="chart-box" style={{ height: 340 }}><ResponsiveContainer width="100%" height="100%"><BarChart data={chartRows} margin={{ left: 8, right: 15 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7ece8" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10 }} tickFormatter={(value) => `${Math.round(value / 1000)}b`} /><Tooltip formatter={(value) => money(Number(value))} contentStyle={{ borderRadius: 12, borderColor: "#dfe6e1" }} /><Legend /><Bar dataKey="tahsilat" name="Tahsilat" fill="#176b5b" radius={[6, 6, 0, 0]} /><Bar dataKey="borc" name="Borç" fill="#e9a74d" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
        <div className="card-pad" style={{ borderTop: "1px solid var(--line)" }}><div className="detail-list">{scalarSummary.map(([key, value]) => <div className="detail-item" key={key}><small>{key.replaceAll("_", " ")}</small><strong>{typeof value === "number" && /amount|total|debt|payment|income/.test(key) ? money(value) : String(value)}</strong></div>)}</div></div>
      </>}
    </section>
  </>;
}

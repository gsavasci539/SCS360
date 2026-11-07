import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";
import { ReportCardRows } from "../academic/StudentReportCards";

export function ParentReportCards({ studentId }: { studentId: string }) {
  const [data, setData] = useState<Paginated<DataRecord> | null>(null), [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(""); setData(null);
    api.get<ApiResponse<Paginated<DataRecord>>>(`/parent/child/${studentId}/report-cards`, {
      params: { page, page_size: 20 }, signal: controller.signal,
    }).then((reply) => {
      if (controller.signal.aborted) return;
      if (!Array.isArray(reply.data.data?.items)) throw new Error("Karne verisi alınamadı");
      setData(reply.data.data);
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, page, revision]);
  return <section className="card" style={{ padding: 20, marginTop: 20 }} aria-label="Yayımlanan karneler">
    <h2>Yayımlanan karneler</h2>
    {loading ? <LoadingState label="Karneler yükleniyor" /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> :
      data?.items.length ? <ReportCardRows cards={data.items} /> : <EmptyState title="Henüz yayımlanmış karne yok" description="Okulunuzun yayımladığı dönem karneleri burada görünür." />}
    {(data?.total_pages ?? 0) > 1 && <div className="pagination"><button className="btn btn-secondary" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}>Önceki karneler</button>
      <span>{page} / {data?.total_pages}</span><button className="btn btn-secondary" disabled={loading || page >= (data?.total_pages ?? 1)} onClick={() => setPage((value) => value + 1)}>Sonraki karneler</button></div>}
  </section>;
}

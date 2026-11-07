import { useEffect, useState } from "react";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { downloadFile } from "../../lib/download";
import { shortDate } from "../../lib/format";
import type { DataRecord } from "../../types/api";

export function ParentCertificates({ studentId }: { studentId: string }) {
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(1);
  const [more, setMore] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api.get(`/parent/child/${studentId}/certificates`, { params: { limit: 21, offset: (page - 1) * 20 }, signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) { setRows((response.data.data || []).slice(0, 20)); setMore((response.data.data || []).length > 20); setError(""); }
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, revision, page]);
  async function download(row: DataRecord) {
    setBusy(String(row.id));
    try { await downloadFile(`/parent/child/${studentId}/certificates/${row.id}/pdf`, `${String(row.title || "SCS360-belge")}.pdf`); }
    catch (reason) { setError(apiMessage(reason)); }
    finally { setBusy(""); }
  }
  return <section className="card card-pad" aria-label="Çocuğun belgeleri" style={{ marginBottom: 20 }}>
    <h2>Katılım ve başarı belgeleri</h2>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : rows.length === 0 ?
      <p>Henüz belge oluşturulmadı.</p> : <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
        {rows.map((row) => <div key={row.id} style={{ border: "1px solid #e0ebe5", padding: 16, borderRadius: 12 }}>
          <h3 style={{ overflowWrap: "anywhere" }}>{String(row.title)}</h3><Badge value={String(row.certificate_type)} />
          <p>{shortDate(row.issue_date)}</p>{row.description && <p style={{ overflowWrap: "anywhere" }}>{String(row.description)}</p>}
          <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => download(row)}>{busy === String(row.id) ? "İndiriliyor…" : "Belgeyi indir"}</button>
        </div>)}
      </div>}
    {!loading && !error && (more || page > 1) && <div className="toolbar" aria-label="Çocuğun belge sayfaları" style={{ marginTop: 16 }}>
      <button className="btn btn-secondary" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Önceki</button>
      <span>Sayfa {page}</span><button className="btn btn-secondary" disabled={!more} onClick={() => setPage((value) => value + 1)}>Sonraki</button>
    </div>}
  </section>;
}

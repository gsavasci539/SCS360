import { useEffect, useRef, useState } from "react";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { shortDate, formatTime } from "../../lib/format";
import { sha256Bytes } from "../../lib/fileIntegrity";
import type { DataRecord } from "../../types/api";

function GuardianCard({ row, studentId, canDecide, onChange }: { row: DataRecord; studentId: string; canDecide: boolean; onChange: () => void }) {
  const [name, setName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [verifiedContent, setVerifiedContent] = useState<string | null>(null);
  const submitting = useRef<AbortController | null>(null);
  const content = typeof row.content === "string" ? row.content : "";
  const expectedHash = row.content_sha256;
  const mayDecide = canDecide && row.can_decide === true;
  const verified = verifiedContent === content;
  useEffect(() => {
    if (!mayDecide || !content.trim() || typeof expectedHash !== "string" || !/^[a-f0-9]{64}$/.test(expectedHash)) return;
    const controller = new AbortController();
    sha256Bytes(new TextEncoder().encode(content), controller.signal)
      .then((actual) => { if (!controller.signal.aborted) setVerifiedContent(actual === expectedHash ? content : null); })
      .catch(() => { if (!controller.signal.aborted) setVerifiedContent(null); });
    return () => controller.abort();
  }, [content, expectedHash, mayDecide]);
  useEffect(() => () => submitting.current?.abort(), []);
  async function decide(status: string) {
    if (!mayDecide || !verified || !acknowledged || name.trim().length < 2 || submitting.current) return;
    const controller = new AbortController();
    submitting.current = controller;
    setBusy(true); setError("");
    try {
      const response = await api.post(`/parent/child/${studentId}/consents/${row.id}`, { consent_status: status, acknowledged: true,
        document_version: row.version, content_sha256: row.content_sha256, signed_name: name.trim() }, { signal: controller.signal });
      const record = response.data.data;
      if (typeof record?.id !== "string" || !record.id || record.consent_status !== status || typeof record.consented_at !== "string") {
        throw new Error("Sunucu veli kararını doğrulamadı.");
      }
      if (!controller.signal.aborted) { setAcknowledged(false); setName(""); onChange(); }
    } catch (reason) { if (!controller.signal.aborted) setError(apiMessage(reason)); }
    finally { if (!controller.signal.aborted) setBusy(false); submitting.current = null; }
  }
  return <article style={{ border: "1px solid #dce6e0", borderRadius: 12, padding: 18, overflowWrap: "anywhere" }}>
    <h3>{String(row.title)} · v{String(row.version)}</h3><p>Yürürlük: {shortDate(row.effective_date)}</p>
    <p>Karar: <Badge value={String(row.consent_status)} />{row.consented_at && <> · {shortDate(row.consented_at)} {formatTime(row.consented_at)}</>}</p>
    <details><summary>Belgenin tam metnini oku</summary>
      <p style={{ whiteSpace: "pre-wrap" }}>{String(row.content || "Belge metni yok")}</p>
      {mayDecide && !verified && <p role="status">Belge doğrulanana kadar karar kaydedilemez.</p>}
      {mayDecide && verified && <div style={{ display: "grid", gap: 12 }}>
        <label>Adınız ve soyadınız<input className="filter-select" value={name} maxLength={200} disabled={busy} onChange={(event) => setName(event.target.value)} autoComplete="name" /></label>
        <label style={{ display: "flex", gap: 8 }}><input type="checkbox" checked={acknowledged} disabled={busy} onChange={(event) => setAcknowledged(event.target.checked)} />Bu sürümün tam metnini okudum; aşağıdaki kararı kaydetmek istiyorum.</label>
        <div className="toolbar"><button className="btn btn-primary" disabled={busy || !acknowledged || name.trim().length < 2} onClick={() => decide("APPROVED")}>{busy ? "Kaydediliyor…" : "Onaylıyorum"}</button><button className="btn btn-secondary" disabled={busy || !acknowledged || name.trim().length < 2} onClick={() => decide("REJECTED")}>Onay vermiyorum</button></div>
      </div>}
    </details>
    {!canDecide && <p>Bu hesap için karar kaydetme yetkisi tanımlı değil.</p>}
    {!row.can_decide && <p>Bu belge yeni karara kapalıdır. Kayıtlı kararınız görüntülenir.</p>}
    {error && <ErrorState message={error} />}
  </article>;
}

export function ParentConsents({ studentId }: { studentId: string }) {
  const sessionVersion = useAuthStore((state) => state.sessionVersion);
  const user = useAuthStore((state) => state.user);
  const canRead = useAuthStore((state) => state.can("parent.view_children"));
  const canDecide = useAuthStore((state) => state.can("parent.give_consent"));
  if (!canRead) return <p>İzin belgelerini görüntüleme yetkiniz yok.</p>;
  return <ScopedParentConsents key={JSON.stringify([studentId, sessionVersion, user?.id, user?.organization_id, canDecide])}
    studentId={studentId} canDecide={canDecide} />;
}

function ScopedParentConsents({ studentId, canDecide }: { studentId: string; canDecide: boolean }) {
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(1);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    api.get(`/parent/child/${studentId}/consents`, { params: { limit: 21, offset: (page - 1) * 20 }, signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) { setRows(response.data.data || []); setError(""); } })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, page, revision]);
  return <section className="card card-pad" aria-label="Çocuğun onay belgeleri">
    <h2>İzin ve onay belgeleri</h2><p>Her belgenin tam metnini okuyarak onay veya ret kararınızı kaydedebilirsiniz.</p>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> : rows.length === 0 ? <p>Henüz size açık bir onay belgesi yok.</p> : <div style={{ display: "grid", gap: 16 }}>{rows.slice(0, 20).map((row) => <GuardianCard key={`${row.id}-${row.content_sha256}-${row.consent_status}`} row={row} studentId={studentId} canDecide={canDecide} onChange={() => setRevision((value) => value + 1)} />)}</div>}
    {!loading && !error && (rows.length > 20 || page > 1) && <div className="toolbar" aria-label="Veli onay sayfaları"><button className="btn btn-secondary" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Önceki</button><span>Sayfa {page}</span><button className="btn btn-secondary" disabled={rows.length <= 20} onClick={() => setPage((value) => value + 1)}>Sonraki</button></div>}
  </section>;
}

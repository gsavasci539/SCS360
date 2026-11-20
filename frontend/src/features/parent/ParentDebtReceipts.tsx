import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Badge, ErrorState, LoadingState, Modal } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { downloadFile } from "../../lib/download";
import { money, shortDate } from "../../lib/format";
import type { ApiResponse } from "../../types/api";
import { checkoutIdentifier } from "../payment/schoolCheckoutAttempt";

type Receipt = {
  id: string;
  receipt_number: string;
  issued_at: string;
  status: string;
  amount: string;
  remaining_debt: string;
};

type ReceiptPage = { student_id: string; debt_id: string; items: Receipt[]; total: number };
const pageSize = 20;

export function ParentDebtReceipts({ studentId, debtId, onClose }: {
  studentId: string;
  debtId: string;
  onClose: () => void;
}) {
  const path = `/parent/child/${studentId}/debts/${debtId}/receipts`;
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{ path: string; page: number; data: ReceiptPage } | null>(null);
  const [error, setError] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [downloadingId, setDownloadingId] = useState("");
  const activeDownload = useRef<AbortController | null>(null);
  const currentPage = result?.path === path && result.page === page ? result.data : null;

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    api.get<ApiResponse<ReceiptPage>>(path, { params: { page, page_size: pageSize }, signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return;
        const data = response.data.data;
        if (data?.student_id !== studentId || data.debt_id !== debtId || !Array.isArray(data.items) ||
            !Number.isSafeInteger(data.total) || data.total < data.items.length ||
            data.items.some((receipt) => !checkoutIdentifier(receipt.id))) {
          setError("Makbuz yanıtı seçili öğrenci ve borç için doğrulanamadı.");
          return;
        }
        setResult({ path, page, data });
      })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); });
    return () => controller.abort();
  }, [path, studentId, debtId, page, revision]);

  useLayoutEffect(() => () => activeDownload.current?.abort(), []);

  async function download(receipt: Receipt) {
    if (activeDownload.current) return;
    const controller = new AbortController();
    activeDownload.current = controller;
    setDownloadError("");
    setDownloadingId(receipt.id);
    try {
      await downloadFile(`${path}/${receipt.id}/pdf`, `${receipt.receipt_number}.pdf`, {
        signal: controller.signal, expectedContentType: "application/pdf",
      });
    } catch (reason) {
      if (!controller.signal.aborted) setDownloadError(apiMessage(reason));
    } finally {
      activeDownload.current = null;
      if (!controller.signal.aborted) setDownloadingId("");
    }
  }

  return <Modal open title="Tahsilat makbuzları" onClose={onClose}>
    {error ? <ErrorState message={error} retry={() => setRevision((value) => value + 1)} /> :
      !currentPage ? <LoadingState label="Makbuzlar yükleniyor" /> :
        currentPage.items.length ? <ul style={{ display: "grid", gap: 12, padding: 0, margin: 0, listStyle: "none" }}>
          {currentPage.items.map((receipt) => <li key={receipt.id} className="card card-pad" style={{ overflowWrap: "anywhere" }}>
            <p><strong>{receipt.receipt_number}</strong> <Badge value={receipt.status} /></p>
            <p>{shortDate(receipt.issued_at)}</p>
            <p>Tahsilat {money(receipt.amount)}</p>
            <p>Makbuz anındaki kalan öğrenci borcu {money(receipt.remaining_debt)}</p>
            <button className="btn btn-secondary" disabled={Boolean(downloadingId)} onClick={() => void download(receipt)}>
              {downloadingId === receipt.id ? "İndiriliyor…" : "PDF indir"}
            </button>
          </li>)}
        </ul> : <p>Bu borca bağlı makbuz bulunmuyor.</p>}
    {downloadError && <p role="alert">{downloadError}</p>}
    {currentPage && (page > 1 || page * pageSize < currentPage.total) && <div className="toolbar" style={{ flexWrap: "wrap" }}>
      <button className="btn btn-secondary" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Önceki sayfa</button>
      <button className="btn btn-secondary" disabled={page * pageSize >= currentPage.total} onClick={() => setPage((value) => value + 1)}>Sonraki sayfa</button>
    </div>}
  </Modal>;
}

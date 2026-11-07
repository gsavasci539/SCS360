import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api, apiMessage } from "../../lib/api";
import { hostedPaymentUrl } from "../../lib/hostedPayment";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import { checkoutBase, checkoutIdentifier, checkoutResult, checkoutScope, type CheckoutPurpose, type SchoolCheckoutResult } from "./schoolCheckoutAttempt";

const terminal = new Set(["COMPLETED", "FAILED", "REFUNDED"]);
function statusMessage(status: string | undefined) {
  if (status === "COMPLETED") return "Ödemeniz doğrulandı ve borcunuza işlendi.";
  if (status === "FAILED") return "Ödeme oturumu tamamlanmadı. Sağlayıcı sonucu başarısız olarak kayıtlı.";
  if (status === "REFUNDED") return "Bu ödeme için iade kaydı bulunuyor.";
  if (status === "PAID_REVIEW") return "Ödeme alınmış, kayıt uzlaştırması bekleniyor. Yeniden ödeme yapmayın; kurumunuzla iletişime geçin.";
  if (status === "FRAUD_REVIEW") return "Ödeme incelemede. Sonuç kesinleşmeden yeniden ödeme yapmayın.";
  if (status === "INITIALIZING") return "Ödeme oturumu hazırlanıyor. Yeni ödeme başlatmadan bu işlemin sonucunu kontrol edin.";
  return "Ödemenizin doğrulanması bekleniyor. Sonuç kesinleşmeden yeniden ödeme yapmayın.";
}
export function SchoolCheckoutStatus({ checkoutId, onComplete, purpose = "staff", onUpdate, onMissing, initialResult, expectedDebtId, expectedAmount }: {
  checkoutId: string; onComplete?: () => void; purpose?: CheckoutPurpose; onUpdate?: (result: SchoolCheckoutResult) => void;
  onMissing?: () => void; initialResult?: SchoolCheckoutResult | null;
  expectedDebtId?: string; expectedAmount?: string;
}) {
  const user = useAuthStore((state) => state.user), sessionVersion = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const allowed = purpose === "parent" ? hasPermission(user, "parent.make_payment")
    : ["parent.make_payment", "finance.write", "finance.read"].some((permission) => hasPermission(user, permission));
  const scope = allowed ? checkoutScope(user, workspace, purpose) : null;
  const accessKey = JSON.stringify([scope, sessionVersion, checkoutId, purpose, [...(user?.permissions || [])].sort()]);
  const activeKey = useRef(accessKey);
  const handlers = useRef({ onComplete, onUpdate, onMissing });
  useLayoutEffect(() => {
    activeKey.current = accessKey;
    handlers.current = { onComplete, onUpdate, onMissing };
  }, [accessKey, onComplete, onUpdate, onMissing]);
  const [record, setRecord] = useState<{ key: string; result: SchoolCheckoutResult | null }>({ key: accessKey, result: initialResult || null });
  const [error, setError] = useState(""), [busy, setBusy] = useState(false), [missing, setMissing] = useState(false), [revision, setRevision] = useState(0);
  const [pageUrl, setPageUrl] = useState<{ key: string; value: string } | null>(null);
  const controller = useRef<AbortController | null>(null), completed = useRef(new Set<string>()), inFlight = useRef(false);
  const result = record.key === accessKey ? record.result : null;
  function accept(value: unknown, key: string, allowUrl: boolean) {
    const data = checkoutResult(value, checkoutId);
    if (expectedDebtId && data.debt_id !== expectedDebtId || expectedAmount && data.amount !== expectedAmount) throw new Error("Ödeme sonucu seçilen borç ve tutarla eşleşmiyor.");
    if (activeKey.current !== key) return;
    setRecord({ key, result: data }); setMissing(false); setError("");
    if (allowUrl && (data.checkout_url || data.payment_page_url)) {
      const url = hostedPaymentUrl(data.checkout_url || data.payment_page_url);
      if (!url) throw new Error("Ödeme sayfası doğrulanamadı.");
      setPageUrl({ key, value: url });
    } else if (data.status !== "PENDING") setPageUrl(null);
    handlers.current.onUpdate?.(data);
    if (data.status === "COMPLETED" && !completed.current.has(key)) {
      completed.current.add(key); handlers.current.onComplete?.();
    }
  }
  useEffect(() => {
    const key = accessKey, abort = new AbortController(); controller.current = abort;
    setError(""); setMissing(false); setBusy(false); inFlight.current = false; setPageUrl(null);
    if (initialResult && scope) {
      try { accept(initialResult, key, true); } catch (reason) { setError(apiMessage(reason)); }
    }
    async function load() {
      if (!scope || !checkoutIdentifier(checkoutId) || inFlight.current || abort.signal.aborted) return;
      inFlight.current = true;
      try {
        const response = await api.get(`${checkoutBase(purpose)}/${checkoutId}`, { signal: abort.signal });
        if (!abort.signal.aborted && activeKey.current === key) accept(response.data.data, key, false);
      } catch (reason) {
        if (abort.signal.aborted || activeKey.current !== key) return;
        const status = (reason as { response?: { status?: number } })?.response?.status;
        if (status === 404) { setMissing(true); setRecord({ key, result: null }); handlers.current.onMissing?.(); }
        else setError(apiMessage(reason));
      } finally { if (!abort.signal.aborted && activeKey.current === key) inFlight.current = false; }
    }
    void load(); window.addEventListener("focus", load);
    return () => { abort.abort(); window.removeEventListener("focus", load); };
  }, [accessKey, revision]);
  async function action(kind: "resume" | "refresh") {
    if (!scope || inFlight.current || !result || kind === "resume" && !result.can_resume || kind === "refresh" && !result.can_refresh) return;
    const key = accessKey, abort = controller.current;
    if (!abort || abort.signal.aborted) return;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const response = await api.post(`${checkoutBase(purpose)}/${checkoutId}/${kind}`, {}, { signal: abort.signal });
      if (!abort.signal.aborted && activeKey.current === key) accept(response.data.data, key, kind === "resume");
    } catch (reason) { if (!abort.signal.aborted && activeKey.current === key) setError(apiMessage(reason)); }
    finally { if (!abort.signal.aborted && activeKey.current === key) { inFlight.current = false; setBusy(false); } }
  }
  const url = pageUrl?.key === accessKey && result?.status === "PENDING" ? pageUrl.value : null;
  return <section aria-label="Öğrenci ödeme sonucu">
    <p role="status">{statusMessage(result?.status)}</p>
    {missing && <p>Ödeme isteği henüz sunucuya ulaşmamış olabilir. Aynı işlem kimliğiyle fatura bilgilerini tekrar girin; yeni ödeme başlatmayın.</p>}
    {error && <p role="alert">{error}</p>}
    {!scope && <p role="alert">Ödeme sonucunu görmek için hesabınızı ve kurum çalışma alanını kontrol edin.</p>}
    {url && <p><a className="btn btn-primary" href={url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Güvenli ödeme sayfasını aç</a></p>}
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
      {result?.can_resume && !terminal.has(result.status) && <button className="btn btn-secondary" disabled={busy} onClick={() => action("resume")}>Mevcut ödeme sayfasını getir</button>}
      {result?.can_refresh && !terminal.has(result.status) && <button className="btn btn-secondary" disabled={busy} onClick={() => action("refresh")}>Ödeme sonucunu kontrol et</button>}
      {(error || missing) && scope && <button className="btn btn-secondary" disabled={busy} onClick={() => setRevision((value) => value + 1)}>Kaydı yeniden yükle</button>}
    </div>
  </section>;
}

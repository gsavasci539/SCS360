import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, apiMessage } from "../../lib/api";
import { money } from "../../lib/format";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import { SchoolCheckoutStatus } from "./SchoolCheckoutStatus";
import { checkoutAmount, checkoutAttemptKey, checkoutResult, checkoutScope, clearSchoolCheckout, readSchoolCheckout, saveSchoolCheckout,
  type CheckoutPurpose, type SchoolCheckoutAttempt, type SchoolCheckoutResult } from "./schoolCheckoutAttempt";

type Props = { debtId: string; amount: unknown; purpose?: CheckoutPurpose; available: boolean; onComplete?: () => void };
type Request = { debt_id: string; amount: string; request_id: string; buyer: Record<string, string> };
export function SchoolCheckoutForm(props: Props) {
  const user = useAuthStore((state) => state.user), sessionVersion = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace), purpose = props.purpose || "staff";
  const scope = checkoutScope(user, workspace, purpose), storageKey = checkoutAttemptKey(scope, props.debtId);
  const allowed = hasPermission(user, "parent.make_payment") || purpose === "staff" && hasPermission(user, "finance.write");
  return <ScopedCheckout key={JSON.stringify([storageKey, sessionVersion, [...(user?.permissions || [])].sort()])} {...props}
    available={props.available && allowed} purpose={purpose} storageKey={storageKey} />;
}
function ScopedCheckout({ debtId, amount, purpose = "staff", available, onComplete, storageKey }: Props & { storageKey: string | null }) {
  const [saved] = useState(() => readSchoolCheckout(storageKey));
  const [attempt, setAttempt] = useState<SchoolCheckoutAttempt | null>(saved.attempt), [error, setError] = useState(saved.error);
  const [storageError, setStorageError] = useState(Boolean(saved.error)), [missing, setMissing] = useState(false), [busy, setBusy] = useState(false);
  const [verifiedTerminal, setVerifiedTerminal] = useState(false);
  const [initialized, setInitialized] = useState<SchoolCheckoutResult | null>(null), [revision, setRevision] = useState(0);
  const [original, setOriginal] = useState<Request | null>(null);
  const inFlight = useRef(false), controller = useRef(new AbortController());
  useEffect(() => { const abort = new AbortController(); controller.current = abort; return () => abort.abort(); }, []);
  const currentAmount = checkoutAmount(amount);
  function update(result: SchoolCheckoutResult) {
    if (!attempt || controller.current.signal.aborted) return;
    if (result.debt_id !== attempt.debt_id || checkoutAmount(result.amount) !== attempt.amount) {
      setError("Ödeme sonucu seçilen borç ve tutarla eşleşmiyor."); return;
    }
    setMissing(false);
    setOriginal(null);
    setVerifiedTerminal(["FAILED", "REFUNDED"].includes(result.status));
    const current = readSchoolCheckout(storageKey);
    if (current.error || current.attempt?.request_id !== attempt.request_id) {
      setStorageError(true); setError("Önceki ödeme bilgisi değişti. Yeni işlem açmadan sonucu kontrol edin."); return;
    }
    try { const next = { ...attempt, status: result.status }; saveSchoolCheckout(storageKey, next); setAttempt(next); }
    catch (reason) { setError(apiMessage(reason)); setStorageError(true); }
  }
  async function send(request: Request) {
    if (inFlight.current || controller.current.signal.aborted) return;
    inFlight.current = true; setBusy(true); setError(""); setMissing(false);
    try {
      const recovery = readSchoolCheckout(storageKey);
      if (recovery.error || recovery.attempt?.request_id !== request.request_id) {
        setStorageError(true); throw new Error("Önceki ödeme kimliği saklanamadı veya değişti. Yeni ödeme başlatmadan sonucu kontrol edin.");
      }
      const response = await api.post(purpose === "parent" ? "/parent/payments/initialize" : "/payments/iyzico/initialize", request, { signal: controller.current.signal });
      if (controller.current.signal.aborted) return;
      const result = checkoutResult(response.data.data, request.request_id);
      if (result.debt_id !== request.debt_id || checkoutAmount(result.amount) !== request.amount) throw new Error("Ödeme sonucu seçilen borç ve tutarla eşleşmiyor.");
      const next: SchoolCheckoutAttempt = { version: 1, request_id: request.request_id, debt_id: request.debt_id, amount: request.amount, status: result.status };
      saveSchoolCheckout(storageKey, next); setOriginal(null); setAttempt(next); setInitialized(result);
      setVerifiedTerminal(["FAILED", "REFUNDED"].includes(result.status));
    } catch (reason) { if (!controller.current.signal.aborted) setError(apiMessage(reason)); }
    finally { if (!controller.current.signal.aborted) { setBusy(false); inFlight.current = false; setRevision((value) => value + 1); } }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || inFlight.current || storageError || !available) return;
    const selectedAmount = attempt?.amount || currentAmount;
    if (!selectedAmount) { setError("Ödeme tutarı doğrulanamadı."); return; }
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const buyer = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, String(value).trim()]));
    const next: SchoolCheckoutAttempt = attempt || { version: 1, request_id: crypto.randomUUID(), debt_id: debtId, amount: selectedAmount, status: "INITIALIZING" };
    try { saveSchoolCheckout(storageKey, next); }
    catch (reason) { setError(apiMessage(reason)); setStorageError(true); return; }
    const request = { debt_id: next.debt_id, amount: next.amount, request_id: next.request_id, buyer };
    setOriginal(request); setAttempt(next); await send(request);
  }
  function newAttempt() {
    if (!attempt || !verifiedTerminal || !["FAILED", "REFUNDED"].includes(attempt.status) || busy) return;
    try { clearSchoolCheckout(storageKey, attempt.request_id); setOriginal(null); setAttempt(null); setInitialized(null); setMissing(false); setError(""); setVerifiedTerminal(false); }
    catch (reason) { setError(apiMessage(reason)); setStorageError(true); }
  }
  function reloadSaved() {
    const current = readSchoolCheckout(storageKey); setAttempt(current.attempt); setError(current.error); setStorageError(Boolean(current.error));
  }
  const showForm = !storageError && (!attempt || missing && !original) && available && Boolean(currentAmount);
  return <section aria-label={purpose === "parent" ? "Veli güvenli öğrenci ödemesi" : "Güvenli öğrenci ödemesi"}>
    {error && <p role="alert">{error}</p>}
    {storageError && <button className="btn btn-secondary" onClick={reloadSaved}>Ödeme kaydını yeniden oku</button>}
    {attempt && !busy && <SchoolCheckoutStatus key={`${attempt.request_id}:${revision}`} purpose={purpose} checkoutId={attempt.request_id}
      expectedDebtId={attempt.debt_id} expectedAmount={attempt.amount} initialResult={initialized}
      onUpdate={update} onMissing={() => setMissing(true)} onComplete={onComplete} />}
    {busy && <p role="status">Ödeme oturumu hazırlanıyor…</p>}
    {attempt && <p className="cell-sub">Bu işlemdeki tutar: {money(attempt.amount)}. İşlem kimliği korunuyor; sayfayı yenilediğinizde aynı ödeme kaydından devam edilir.</p>}
    {missing && original && !busy && <button className="btn btn-primary" onClick={() => send(original)}>İlk isteği aynı kimlikle tekrar gönder</button>}
    {showForm && <form aria-label="Öğrenci ödeme bilgileri" onSubmit={submit}><fieldset disabled={busy} style={{ display: "grid", gap: 12, border: 0, padding: 0 }}>
      <p>Kart bilgilerinizi yalnız ödeme sağlayıcısının sayfasında girin. Kimlik ve fatura bilgileri tarayıcı depolamasına kaydedilmez.</p>
      <label>Kimlik / pasaport numarası<input name="identityNumber" required minLength={5} maxLength={50} autoComplete="off" /></label>
      <label>Ödeme telefonu<input name="gsmNumber" type="tel" required minLength={5} maxLength={30} autoComplete="tel" /></label>
      <label>Fatura adresi<textarea name="registrationAddress" required minLength={5} maxLength={500} autoComplete="street-address" /></label>
      <label>Şehir<input name="city" required maxLength={100} autoComplete="address-level2" /></label>
      <label>Ülke<input name="country" required maxLength={100} autoComplete="country-name" /></label>
      <button className="btn btn-primary">{attempt ? "Aynı işlem kimliğiyle tekrar gönder" : "Ödeme sayfasını hazırla"}</button>
    </fieldset></form>}
    {!attempt && !storageError && (!available || !currentAmount) && <p>Bu borç için yeni online ödeme açılamıyor. Kurumunuzla iletişime geçin.</p>}
    {attempt && verifiedTerminal && ["FAILED", "REFUNDED"].includes(attempt.status) && available && currentAmount && !storageError && <p>
      <button className="btn btn-secondary" disabled={busy} onClick={newAttempt}>Yeni ödeme işlemi oluştur</button>
    </p>}
  </section>;
}

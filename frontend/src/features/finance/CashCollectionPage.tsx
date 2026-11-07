import { useEffect, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Save } from "lucide-react";
import { Field, PageHeader } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { ResourceChoice } from "../resources/ResourceChoice";
import { api, apiMessage } from "../../lib/api";
import { money } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse } from "../../types/api";
import { cashAttemptKey, clearCashAttempt, completeCashAttempt, readCashAttempt, writeCashAttempt, type CashAttempt, type CashReceipt, type CashRequest } from "./cashAttempt";

type Values = Record<string, string | number | boolean>;
export function CashCollectionPage() {
  const user = useAuthStore((state) => state.user), workspace = usePlatformWorkspace((state) => state.workspace);
  const storageKey = cashAttemptKey(user, workspace);
  return <CashCollectionForm key={storageKey || "unavailable"} storageKey={storageKey} />;
}

function CashCollectionForm({ storageKey }: { storageKey: string | null }) {
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const can = useAuthStore((state) => state.can), navigate = useNavigate(), { showToast } = useToast();
  const [stored] = useState(() => readCashAttempt(storageKey));
  const [attempt, setAttempt] = useState<CashAttempt | null>(stored.attempt);
  const [requestId, setRequestId] = useState(() => stored.attempt?.request.request_id || crypto.randomUUID());
  const [error, setError] = useState(""), [receipt, setReceipt] = useState<CashReceipt | null>(stored.attempt?.receipt || null);
  const { register, control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<Values>({
    defaultValues: stored.attempt ? { ...stored.attempt.request, notes: stored.attempt.request.notes || "" } : { debt_id: "", amount: "", payment_method: "", notes: "" },
  });
  async function submit(values: Values) {
    if (receipt || stored.error) return; setError("");
    const body: CashRequest = attempt?.request || { debt_id: String(values.debt_id), amount: String(values.amount),
      payment_method: String(values.payment_method), notes: String(values.notes).trim() || null, request_id: requestId };
    const pending: CashAttempt = { version: 1, request: body, receipt: null };
    try { writeCashAttempt(storageKey, pending); } catch (reason) { setError(apiMessage(reason)); return; }
    setAttempt(pending);
    try {
      const response = await api.post<ApiResponse<CashReceipt>>("/payments", body);
      // If persistence is unavailable after success, the pending snapshot still
      // safely resumes the same server request following a reload.
      try { completeCashAttempt(storageKey, pending, response.data.data); } catch { /* Keep the original pending snapshot. */ }
      if (!mounted.current) return;
      setReceipt(response.data.data); showToast("Tahsilat tamamlandı", "Makbuz otomatik olarak oluşturuldu.");
      if (can("receipt.read") && response.data.data.receipt_id) navigate(`/finance/receipts/${response.data.data.receipt_id}`);
    } catch (reason) {
      if (!mounted.current) return;
      if (isAxiosError(reason) && reason.response?.status === 422) {
        // Validation errors roll back before the HTTP response; editing is safe.
        try { clearCashAttempt(storageKey); setAttempt(null); setRequestId(crypto.randomUUID()); } catch (failure) { setError(apiMessage(failure)); return; }
      }
      setError(apiMessage(reason));
    }
  }
  function newPayment() {
    try { clearCashAttempt(storageKey); } catch (reason) { setError(apiMessage(reason)); return; }
    setReceipt(null); setAttempt(null); setRequestId(crypto.randomUUID()); setError("");
    reset({ debt_id: "", amount: "", payment_method: "", notes: "" });
  }
  return <>
    <PageHeader eyebrow="Finans" title="Yeni tahsilat" description="Borcu seçip kayıtlı kalan tutarı aşmadan tahsilat oluşturun.">
      {can("finance.read") && <Link className="btn btn-secondary" to="/finance/payments"><ArrowLeft size={16} />Listeye dön</Link>}
    </PageHeader>
    {stored.error && <p role="alert">{stored.error}</p>}
    {receipt ? <section className="card card-pad" aria-label="Tahsilat sonucu">
      <h2>Tahsilat tamamlandı</h2><p>Makbuz: <strong>{receipt.receipt_number}</strong></p><p>İşlem anındaki kalan toplam borç: {money(receipt.remaining_debt)}</p>
      {error && <p role="alert">{error}</p>}
      <button className="btn btn-primary" onClick={newPayment}>Yeni tahsilat</button>
    </section> : <form className="card form-card" onSubmit={(event) => { void handleSubmit(submit)(event); }}>
      <div className="form-section"><h2>Ödeme bilgileri</h2><p>Bağlantı kesilirse aynı formdan tekrar deneyebilirsiniz. Yeni bir tahsilat açmadan önce önceki işlemin sonucunu kontrol edin.</p>
        {error && <p role="alert">{error}</p>}
        {attempt && <p role="status">Önceki tahsilatın sonucu bekleniyor. Aynı işlem kimliği ve kayıtlı tutarla doğrulama yapılacak; sayfayı yenilediğinizde bu bilgiler korunur.</p>}
        <fieldset disabled={isSubmitting || Boolean(attempt) || Boolean(stored.error)} style={{ border: 0, padding: 0, minWidth: 0 }}><div className="form-grid">
          <ResourceChoice field={{ name: "debt_id", label: "Borç kaydı", required: true, type: "select", searchable: true, optionSource: "/payments/debt-options" }} control={control} />
          <Field label="Ödeme tutarı" required error={errors.amount?.message}>
            <input type="number" min="0.01" max="9999999999.99" step="0.01" required {...register("amount", { required: "Tutar zorunludur.", min: { value: 0.01, message: "Tutar sıfırdan büyük olmalı." } })} />
          </Field>
          <Field label="Ödeme yöntemi" required error={errors.payment_method?.message}><select required {...register("payment_method", { required: "Yöntem seçin." })}>
            <option value="">Seçiniz</option><option value="CASH">Nakit</option><option value="CREDIT_CARD">Kredi kartı</option>
            <option value="BANK_TRANSFER">Banka havalesi</option><option value="EFT">EFT</option><option value="OTHER">Diğer</option>
          </select></Field>
          <Field label="Açıklama" full><textarea {...register("notes")} maxLength={2000} /></Field>
        </div></fieldset>
      </div>
      <div className="form-actions">{can("finance.read") && <Link className="btn btn-secondary" to="/finance/payments">Vazgeç</Link>}
        <button className="btn btn-primary" disabled={isSubmitting || Boolean(stored.error)}><Save size={16} />{isSubmitting ? "Kaydediliyor…" : "Tahsilatı tamamla"}</button></div>
    </form>}
  </>;
}

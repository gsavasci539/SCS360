import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { money } from "../../lib/format";
import { getHomePath } from "../../lib/home";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { DataRecord } from "../../types/api";
import { SchoolCheckoutForm } from "./SchoolCheckoutForm";
import { SchoolCheckoutStatus } from "./SchoolCheckoutStatus";
import { checkoutIdentifier, checkoutScope, type SchoolCheckoutResult } from "./schoolCheckoutAttempt";

export function SchoolPaymentPage() {
  const { debtId } = useParams<{ debtId: string; amount: string }>(), [search] = useSearchParams();
  const user = useAuthStore((state) => state.user), sessionVersion = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace), scope = checkoutScope(user, workspace, "staff");
  const returned = search.get("checkout"), checkoutId = checkoutIdentifier(returned), validDebt = checkoutIdentifier(debtId);
  const canStart = hasPermission(user, "finance.write") || hasPermission(user, "parent.make_payment");
  const [record, setRecord] = useState<{ key: string; debt: DataRecord } | null>(null), [returnedRecord, setReturnedRecord] = useState<{ key: string; result: SchoolCheckoutResult } | null>(null);
  const [error, setError] = useState(""), [loading, setLoading] = useState(true), [revision, setRevision] = useState(0);
  const key = JSON.stringify([scope, sessionVersion, validDebt, checkoutId]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(false); setError(""); setReturnedRecord(null);
    if (!scope || !canStart || returned !== null || !validDebt) return () => controller.abort();
    setLoading(true);
    api.get(`/payments/iyzico/debts/${validDebt}`, { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) setRecord({ key, debt: response.data.data });
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [key, revision, canStart]);
  const debt = record?.key === key ? record.debt : null;
  const result = returnedRecord?.key === key ? returnedRecord.result : null;
  return <main className="saas-workspace" style={{ maxWidth: 680, padding: 20, margin: "30px auto" }}>
    <section className="card card-pad"><h1>Öğrenci ödemesi</h1>
      {!scope ? <ErrorState message="Ödeme için hesabınızı ve kurum çalışma alanını kontrol edin." />
        : returned !== null ? checkoutId ? <div key={key}>
          {result?.amount && <p>Bu ödeme işlemindeki tutar: {money(result.amount)}</p>}
          <SchoolCheckoutStatus checkoutId={checkoutId} onUpdate={(value) => setReturnedRecord({ key, result: value })} />
        </div> : <ErrorState message="Ödeme işlem kimliği geçersiz." />
          : !canStart ? <ErrorState message="Yeni öğrenci ödemesi başlatma yetkiniz bulunmuyor." />
            : !validDebt ? <ErrorState message="Borç kimliği geçersiz." /> : <>
            {loading && !debt && <LoadingState />}{error && <ErrorState message={error} retry={() => setRevision((value) => value + 1)} />}
            {debt && <><p>{String(debt.description || "Okul ödemesi")}</p><p>Güncel kalan tutar: {money(debt.remaining_amount)}</p>
              {!debt.online_payment_available && <p>Bu kurumda yeni online ödeme açık değil. Mevcut ödeme kaydınızın sonucu ayrıca kontrol edilebilir.</p>}
              <SchoolCheckoutForm debtId={validDebt} amount={debt.remaining_amount}
                available={Boolean(debt.online_payment_available) && debt.status !== "CANCELLED"}
                onComplete={() => setRevision((value) => value + 1)} />
            </>}
          </>}
      <p><Link to={getHomePath(user)}>Çalışma alanına dön</Link></p>
    </section>
  </main>;
}

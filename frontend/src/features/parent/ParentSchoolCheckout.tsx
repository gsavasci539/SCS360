import { Modal } from "../../components/ui";
import { money } from "../../lib/format";
import { SchoolCheckoutForm } from "../payment/SchoolCheckoutForm";
import { SchoolCheckoutStatus } from "../payment/SchoolCheckoutStatus";
import { checkoutIdentifier, type SchoolCheckoutReference } from "../payment/schoolCheckoutAttempt";

export function ParentSchoolCheckout({ debtId, amount, childName, available, onClose, onComplete, onOpenConflict }: {
  debtId: string; amount: unknown; childName: string; available: boolean; onClose: () => void; onComplete: () => void;
  onOpenConflict: (balanceChanged: boolean) => void;
}) {
  return <Modal open title="Öğrenci ödemesi" description={amount == null ? childName : `${childName} · ${money(amount)}`} onClose={onClose}>
    <SchoolCheckoutForm purpose="parent" debtId={debtId} amount={amount} available={available}
      onComplete={onComplete} onOpenConflict={onOpenConflict} />
  </Modal>;
}

export function ParentCheckoutReturn({ checkoutId, onComplete, onClose }: { checkoutId: string; onComplete: () => void; onClose: () => void }) {
  const identifier = checkoutIdentifier(checkoutId);
  return <section className="card card-pad" aria-label="Dönen öğrenci ödemesi" style={{ marginBottom: 18 }}>
    <h2>Ödeme işlem sonucu</h2>
    <p>Bu sonuç ödeme işlemine aittir. Öğrenci borçları güncel kayıtlardan ayrıca yüklenir.</p>
    {identifier ? <SchoolCheckoutStatus purpose="parent" checkoutId={identifier} onComplete={onComplete} /> : <p role="alert">Ödeme işlem kimliği geçersiz.</p>}
    <button className="btn btn-secondary" onClick={onClose}>Sonuç bölümünü kapat</button>
  </section>;
}

export function ParentSavedCheckout({ attempt, childName, onComplete, onClose }: {
  attempt: SchoolCheckoutReference; childName: string; onComplete: () => void; onClose: () => void;
}) {
  return <Modal open title="Kayıtlı ödeme sonucu" description={childName} onClose={onClose}>
    <SchoolCheckoutStatus purpose="parent" readOnly checkoutId={attempt.request_id}
      expectedDebtId={attempt.debt_id} expectedAmount={attempt.amount} onComplete={onComplete} />
  </Modal>;
}

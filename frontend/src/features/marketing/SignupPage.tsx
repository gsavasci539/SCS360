import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { packagePrice } from "../../lib/subscription";
import { useAuthStore } from "../../stores/auth";
import { ErrorState, LoadingState } from "../../components/ui";
import type { AuthPayload } from "../../types/api";
import { PublicLayout, usePublicPlans } from "./MarketingPage";

export function SignupPage() {
  const [params] = useSearchParams(), navigate = useNavigate(); const { plans, loading, error, retry } = usePublicPlans();
  const [busy, setBusy] = useState(false), [failure, setFailure] = useState(""), [requestId, setRequestId] = useState(() => newRequestId());
  const user = useAuthStore((state) => state.user); const plan = plans.find((row) => row.id === params.get("paket"));
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || !plan) return; const fields = Object.fromEntries(new FormData(event.currentTarget)); setFailure("");
    if (fields.owner_password !== fields.confirm_password) { setFailure("Parolalar eşleşmiyor."); return; }
    delete fields.confirm_password; setBusy(true);
    try {
      await api.post("/public/signup", { ...fields, plan_id: plan.id, request_id: requestId });
      const response = await api.post("/auth/login", { email: fields.owner_email, password: fields.owner_password });
      useAuthStore.getState().setSession(response.data.data as AuthPayload, false);
      navigate(`/subscription?paket=${plan.id}`, { replace: true });
    } catch (reason) { setFailure(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <PublicLayout title="Kurum üyeliğini başlat"><section className="marketing-signup marketing-section"><div><span className="marketing-kicker">KURUMUNUZA BİR ALAN AÇIN</span><h1>Birlikte başlayalım.</h1><p>Kurum sahibi hesabınızı oluşturun, ardından üyelik ödeme adımına geçin.</p>
    {plan && <aside className="marketing-signup-plan"><h2>{String(plan.name)}</h2><strong>{packagePrice(plan.price, plan.currency)} / {Number(plan.period_months) === 12 ? "yıl" : "ay"}</strong><p>{String(plan.branch_limit)} şube · {String(plan.student_limit)} öğrenci · {String(plan.user_limit)} kullanıcı</p><small>Çalışma alanınız ödeme doğrulandıktan sonra açılır.</small><Link to="/fiyatlandirma">Paket seçimini değiştir</Link></aside>}</div>
    <div className="marketing-signup-card">{user ? <><h2>Bir hesabınızla giriş yaptınız.</h2><p>Mevcut kurumunuzun üyeliğini panelinizden yönetebilirsiniz.</p><Link className="marketing-primary" to={user.is_super_admin ? "/platform" : `/subscription${plan ? `?paket=${plan.id}` : ""}`}>Üyeliği yönet</Link></> : loading ? <LoadingState label="Paket bilgileri yükleniyor" /> : error ? <ErrorState message={error} retry={retry} /> : !plan ? <><h2>Paket seçerek başlayın.</h2><p>Bu paket şu anda satışa açık değil veya paket seçimi yapılmamış.</p><Link className="marketing-primary" to="/fiyatlandirma">Güncel paketlere git</Link></> : <>
      <h2>Kurum sahibi hesabı</h2>{failure && <p role="alert" className="marketing-form-error">{failure}</p>}
      <form aria-label="Kurum üyeliği oluştur" onSubmit={submit} onChange={() => setRequestId(newRequestId())}><fieldset disabled={busy}><label>Kurum adı<input name="name" minLength={2} maxLength={255} autoComplete="organization" required /></label><div className="marketing-name-fields"><label>Adınız<input name="owner_first_name" maxLength={100} autoComplete="given-name" required /></label><label>Soyadınız<input name="owner_last_name" maxLength={100} autoComplete="family-name" required /></label></div><label>E-posta adresiniz<input name="owner_email" type="email" maxLength={255} autoComplete="email" required /></label><label>Parola<input name="owner_password" type="password" minLength={8} maxLength={4096} autoComplete="new-password" required /></label><label>Parola tekrarı<input name="confirm_password" type="password" minLength={8} maxLength={4096} autoComplete="new-password" required /></label><p>Bu hesap kurum üyeliğinin sahibi olur. Öğretmen, öğrenci ve veli hesaplarını kurum panelinizden yönetebilirsiniz.</p><button className="marketing-primary">{busy ? "Hesabınız hazırlanıyor…" : "Hesabı oluştur ve ödeme adımına geç"}</button></fieldset></form><p className="marketing-signin-note">Hesabınız zaten var mı? <Link to="/login">Giriş yapın</Link></p>
    </>}</div>
  </section></PublicLayout>;
}

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Eye, EyeOff, School } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { api, apiMessage, unwrap } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, AuthPayload } from "../../types/api";
import { useToast } from "../../components/Toast";
import { Field } from "../../components/ui";

const loginSchema = z.object({ email: z.email("Geçerli bir e-posta yazın."), password: z.string().min(1, "Şifrenizi yazın."), remember: z.boolean().optional() });
type LoginForm = z.infer<typeof loginSchema>;

function AuthFrame({ children }: { children: React.ReactNode }) {
  return <div className="login-page"><section className="login-panel"><div className="login-brand"><div className="brand-mark"><School size={23} /></div><div><div className="brand-title">Okul360</div><div className="brand-subtitle">Eğitim yönetimi</div></div></div>{children}</section><aside className="login-visual" aria-hidden="true"><div className="visual-card one"><small>Bu ay tahsilat</small><strong>₺486.200</strong><div className="mini-bars"><i style={{ height: "42%" }} /><i style={{ height: "67%" }} /><i style={{ height: "54%" }} /><i style={{ height: "82%" }} /><i style={{ height: "100%" }} /></div></div><div className="visual-card two"><small>Bugün okulda</small><strong>247 öğrenci</strong><div className="progress" style={{ marginTop: 15, background: "rgba(255,255,255,.15)" }}><span style={{ width: "92%", background: "#f1b65f" }} /></div></div><div className="visual-copy"><p className="quote">Her öğrenciye daha fazla zaman, her karara daha net bir bakış.</p><p className="caption">Şubeler, sınıflar ve finans tek bir sakin çalışma alanında.</p></div></aside></div>;
}

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState("");
  const setSession = useAuthStore((state) => state.setSession);
  const accessToken = useAuthStore((state) => state.accessToken);
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();
  const [params] = useSearchParams();
  const demoEnabled = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEMO_CREDENTIALS === "true";
  const demoEmail = demoEnabled ? import.meta.env.VITE_DEMO_EMAIL || "" : "";
  const demoPassword = demoEnabled ? import.meta.env.VITE_DEMO_PASSWORD || "" : "";
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({ resolver: zodResolver(loginSchema), defaultValues: { email: demoEmail, password: demoPassword, remember: false } });
  const parentHome = () => useAuthStore.getState().can("parent.view_children") ? "/parent/dashboard" : "/dashboard";
  const canteenHome = () => useAuthStore.getState().can("canteen.write") ? "/canteen/sales" : "/canteen";
  if (accessToken) return <Navigate to={canteenHome()} replace />;
  const submit = async (values: LoginForm) => {
    setServerError("");
    try {
      const payload = unwrap(await api.post<ApiResponse<AuthPayload>>("/auth/login", { email: values.email, password: values.password }));
      setSession(payload, Boolean(values.remember)); showToast("Hoş geldiniz", `${payload.user.first_name}, çalışma alanınız hazır.`);
      const requestedPath = params.get("next");
      const safeNext = requestedPath?.startsWith("/") && !requestedPath.startsWith("//") ? requestedPath : undefined;
      navigate(safeNext || (location.state as { from?: string } | null)?.from || canteenHome(), { replace: true });
    } catch (error) { setServerError(apiMessage(error)); }
  };
  return <AuthFrame><div className="eyebrow">Güvenli giriş</div><h1>Günün akışına<br />kaldığınız yerden devam edin.</h1><p className="login-lead">Kurumunuzdaki öğrenci, sınıf, yoklama ve finans süreçlerine tek noktadan ulaşın.</p><form className="login-form" onSubmit={handleSubmit(submit)} noValidate><Field label="E-posta adresi" required error={errors.email?.message}><input aria-label="E-posta adresi" autoComplete="email" placeholder="ornek@kurum.com" {...register("email")} /></Field><Field label="Şifre" required error={errors.password?.message}><div className="password-wrap"><input aria-label="Şifre" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Şifreniz" {...register("password")} /><button type="button" className="password-toggle" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Şifreyi gizle" : "Şifreyi göster"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></Field>{serverError && <div className="field-error" role="alert" style={{ padding: "10px 12px", borderRadius: 10, background: "#fff0ef" }}>{serverError}</div>}<div className="login-extra"><label className="checkbox-line"><input type="checkbox" {...register("remember")} />Beni hatırla</label><Link to="/forgot-password" className="text-link">Şifremi unuttum</Link></div><button className="btn btn-primary login-submit" disabled={isSubmitting}>{isSubmitting ? "Giriş yapılıyor…" : "Giriş yap"}</button></form>{demoEnabled && <div className="demo-box"><strong>Demo hesap</strong><br />{demoEmail} · {demoPassword}</div>}</AuthFrame>;
}

const forgotSchema = z.object({ email: z.email("Geçerli bir e-posta yazın.") });
export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false); const { showToast } = useToast();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<{ email: string }>({ resolver: zodResolver(forgotSchema) });
  const submit = async (values: { email: string }) => { try { await api.post("/auth/forgot-password", values); setSent(true); showToast("Bağlantı gönderildi", "E-posta kutunuzu kontrol edin."); } catch (error) { showToast("İşlem tamamlanamadı", apiMessage(error), "error"); } };
  return <AuthFrame><Link className="text-link inline" style={{ gap: 7, marginBottom: 25 }} to="/login"><ArrowLeft size={15} />Girişe dön</Link><div className="eyebrow">Hesap kurtarma</div><h1>Şifrenizi yenileyin.</h1><p className="login-lead">Kayıtlı e-posta adresinizi girin; sıfırlama bağlantısını gönderelim.</p>{sent ? <div className="demo-box" style={{ fontSize: 13 }}>İsteğiniz alındı. Hesap varsa sıfırlama bağlantısı e-posta adresine gönderildi.</div> : <form className="login-form" onSubmit={handleSubmit(submit)}><Field label="E-posta adresi" required error={errors.email?.message}><input autoFocus placeholder="ornek@kurum.com" {...register("email")} /></Field><button className="btn btn-primary login-submit" disabled={isSubmitting}>{isSubmitting ? "Gönderiliyor…" : "Bağlantı gönder"}</button></form>}</AuthFrame>;
}

const resetSchema = z.object({ password: z.string().min(8, "En az 8 karakter yazın."), confirm: z.string() }).refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Şifreler eşleşmiyor." });
export function ResetPasswordPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const { showToast } = useToast();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<{ password: string; confirm: string }>({ resolver: zodResolver(resetSchema) });
  const submit = async (values: { password: string }) => { const token = params.get("token"); if (!token) return showToast("Geçersiz bağlantı", "Sıfırlama anahtarı bulunamadı.", "error"); try { await api.post("/auth/reset-password", { token, new_password: values.password }); showToast("Şifre güncellendi", "Yeni şifrenizle giriş yapabilirsiniz."); navigate("/login"); } catch (error) { showToast("Şifre güncellenemedi", apiMessage(error), "error"); } };
  return <AuthFrame><div className="eyebrow">Yeni şifre</div><h1>Güçlü bir şifre belirleyin.</h1><p className="login-lead">En az 8 karakterli, yalnızca size ait bir şifre kullanın.</p><form className="login-form" onSubmit={handleSubmit(submit)}><Field label="Yeni şifre" required error={errors.password?.message}><input type="password" {...register("password")} /></Field><Field label="Şifre tekrarı" required error={errors.confirm?.message}><input type="password" {...register("confirm")} /></Field><button className="btn btn-primary login-submit" disabled={isSubmitting}>Şifreyi güncelle</button></form></AuthFrame>;
}

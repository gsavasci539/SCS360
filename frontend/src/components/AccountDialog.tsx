import { useCallback, useId, useRef, useState, type FormEvent } from "react";
import { api, apiMessage } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import type { ApiResponse, AuthUser } from "../types/api";
import { Field, Modal } from "./ui";

export function AccountDialog({ user, mode, onClose, onSaved }: {
  user: AuthUser;
  mode: "profile" | "password";
  onClose: () => void;
  onSaved: (mode: "profile" | "password") => void;
}) {
  const formId = useId();
  const saving = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [email, setEmail] = useState(user.email);
  const [phone, setPhone] = useState(user.phone ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const emailChanged = email.trim().toLowerCase() !== user.email.toLowerCase();
  const passwordMode = mode === "password";
  const close = useCallback(() => { if (!saving.current) onClose(); }, [onClose]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving.current) return;
    if (passwordMode && newPassword !== repeatPassword) {
      setError("Yeni şifreler uyuşmuyor.");
      return;
    }
    if (!passwordMode && (!firstName.trim() || !lastName.trim())) {
      setError("Ad ve soyad gerekli.");
      return;
    }
    saving.current = true;
    setBusy(true);
    setError("");
    const sessionVersion = useAuthStore.getState().sessionVersion;
    function checkSession() {
      const state = useAuthStore.getState();
      if (state.sessionVersion !== sessionVersion || state.user?.id !== user.id) throw new Error("Oturum değişti.");
      return state;
    }
    try {
      if (passwordMode) {
        const { data: response } = await api.post<ApiResponse<{ id: string }>>("/auth/change-password", {
          current_password: currentPassword, new_password: newPassword,
        });
        if (!response.success || response.data?.id !== user.id) throw new Error("Şifre değişikliği doğrulanamadı.");
        checkSession().clearSession();
      } else {
        const profile = {
          first_name: firstName.trim(), last_name: lastName.trim(), email: email.trim(), phone: phone.trim() || null,
        };
        const { data: response } = await api.put<ApiResponse<{ id: string; email: string }>>("/auth/me", {
          ...profile, ...(emailChanged ? { current_password: currentPassword } : {}),
        });
        if (!response.success || response.data?.id !== user.id || !response.data.email) {
          throw new Error("Profil yanıtı doğrulanamadı.");
        }
        checkSession();
        const { data: result } = await api.get<ApiResponse<AuthUser>>("/auth/me");
        const saved = result.data;
        if (!result.success || saved?.id !== user.id || saved.email !== response.data.email ||
          saved.first_name !== profile.first_name || saved.last_name !== profile.last_name ||
          (saved.phone ?? null) !== profile.phone) throw new Error("Kaydedilen profil doğrulanamadı.");
        checkSession().setUser(saved);
      }
      onSaved(mode);
    } catch (failure) {
      setError(apiMessage(failure));
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }

  return <Modal open title={passwordMode ? "Şifre değiştir" : "Profil bilgileri"} onClose={close}
    actions={<>
      <button className="btn btn-secondary" onClick={close} disabled={busy}>Vazgeç</button>
      <button className="btn btn-primary" form={formId} type="submit" disabled={busy}>
        {busy ? "Kaydediliyor…" : "Kaydet"}
      </button>
    </>}>
    <form id={formId} className="form-grid" onSubmit={submit}>
      {!passwordMode && <>
        <Field label="Ad"><input autoComplete="given-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} maxLength={100} required disabled={busy} /></Field>
        <Field label="Soyad"><input autoComplete="family-name" value={lastName} onChange={(e) => setLastName(e.target.value)} maxLength={100} required disabled={busy} /></Field>
        <Field label="E-posta" full><input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={255} required disabled={busy} /></Field>
        <Field label="Telefon" full><input type="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={20} disabled={busy} /></Field>
      </>}
      {(passwordMode || emailChanged) &&
        <Field label="Mevcut şifre" full><input type="password" autoComplete="current-password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} maxLength={4096} required disabled={busy} /></Field>}
      {passwordMode && <>
        <Field label="Yeni şifre" full><input type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} minLength={8} maxLength={4096} required disabled={busy} /></Field>
        <Field label="Yeni şifre (tekrar)" full><input type="password" autoComplete="new-password" value={repeatPassword} onChange={(e) => setRepeatPassword(e.target.value)} minLength={8} maxLength={4096} required disabled={busy} /></Field>
        <p className="field-full">Şifre değiştikten sonra yeniden giriş yapmanız gerekir.</p>
      </>}
      {error && <p className="field-full field-error" role="alert">{error}</p>}
    </form>
  </Modal>;
}

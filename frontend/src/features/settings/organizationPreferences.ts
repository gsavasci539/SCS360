export interface AppSettings {
  school_name: string;
  academic_year: string | null;
  default_currency: string;
  max_upload_size_mb: number;
  allowed_file_types: string;
  receipt_email_enabled: boolean | null;
  overdue_reminders_enabled: boolean | null;
  failed_notification_alerts_enabled: boolean | null;
}

export interface OrganizationPreferences {
  organization_id: string;
  values: AppSettings;
  upload_policy: { max_size_mb: number; allowed_extensions: string[] };
}

export const notificationPreferences = [
  ["receipt_email_enabled", "Ödeme sonrası makbuz e-postası"],
  ["overdue_reminders_enabled", "Geciken borç hatırlatmaları"],
  ["failed_notification_alerts_enabled", "Başarısız gönderim uyarıları"],
] as const;

export const sectionFields: Record<string, (keyof AppSettings)[]> = {
  general: ["school_name", "academic_year", "default_currency"],
  uploads: ["max_upload_size_mb", "allowed_file_types"],
  notifications: notificationPreferences.map(([key]) => key),
};

export function readPreferences(data: OrganizationPreferences | undefined, organization: string | null | undefined) {
  if (!organization || data?.organization_id !== organization) throw new Error("Kurum tercihleri doğrulanamadı.");
  const { values, upload_policy: policy } = data;
  if (!values || !policy || typeof values.school_name !== "string" ||
    (values.academic_year !== null && typeof values.academic_year !== "string") ||
    !["TRY", "EUR", "USD"].includes(values.default_currency) || typeof values.allowed_file_types !== "string" ||
    !Number.isInteger(values.max_upload_size_mb) || !Number.isInteger(policy.max_size_mb) ||
    values.max_upload_size_mb < 1 || values.max_upload_size_mb > policy.max_size_mb ||
    !Array.isArray(policy.allowed_extensions) || policy.allowed_extensions.some((item) => typeof item !== "string") ||
    notificationPreferences.some(([key]) => values[key] !== null && typeof values[key] !== "boolean")) {
    throw new Error("Kurum tercihleri doğrulanamadı.");
  }
  return data;
}

export function preferenceChanges(snapshot: OrganizationPreferences, draft: AppSettings, section: string) {
  const typedExtensions = new Set(draft.allowed_file_types.split(",").map((value) => value.trim().toLowerCase()).filter(Boolean));
  if (section === "uploads" && [...typedExtensions].some((value) => !snapshot.upload_policy.allowed_extensions.includes(value))) {
    throw new Error("Yalnız sunucunun izin verdiği uzantıları girin.");
  }
  const normalized: AppSettings = {
    ...draft, school_name: draft.school_name.trim(), academic_year: draft.academic_year?.trim() || null,
    allowed_file_types: snapshot.upload_policy.allowed_extensions.filter((value) => typedExtensions.has(value)).join(","),
  };
  const keys = (sectionFields[section] ?? []).filter((key) => normalized[key] !== snapshot.values[key]);
  return {
    organization_id: snapshot.organization_id,
    changes: Object.fromEntries(keys.map((key) => [key, normalized[key]])),
    expected: Object.fromEntries(keys.map((key) => [key, snapshot.values[key]])),
  };
}

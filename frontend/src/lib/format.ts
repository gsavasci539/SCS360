export const money = (value: unknown) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", minimumFractionDigits: 0 }).format(Number(value || 0));

export const shortDate = (value: unknown) => {
  if (!value) return "—";
  const raw = String(value);
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  const date = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(raw);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "short", year: "numeric" }).format(date);
};

export const dateInputValue = (date = new Date()) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export const monthInputValue = (date = new Date()) => dateInputValue(date).slice(0, 7);

export const statusLabels: Record<string, string> = {
  ACTIVE: "Aktif", active: "Aktif", SENT: "Gönderildi", PAID: "Ödendi", PRESENT: "Geldi",
  PASSIVE: "Pasif", passive: "Pasif", PENDING: "Bekliyor", pending: "Bekliyor", UNPAID: "Ödenmedi",
  PARTIALLY_PAID: "Kısmi ödendi", OVERDUE: "Gecikmiş", CANCELLED: "İptal", FAILED: "Başarısız",
  BLOCKED: "Bloke", ABSENT: "Gelmedi", EXCUSED: "İzinli", LATE: "Geç geldi", HALF_DAY: "Yarım gün",
  DRAFT: "Taslak", draft: "Taslak", GRADUATED: "Mezun", LEFT: "Ayrıldı",
};

export const statusTone = (status: unknown) => {
  const s = String(status || "").toUpperCase();
  if (["ACTIVE", "PAID", "SENT", "PRESENT"].includes(s)) return "success";
  if (["PENDING", "PARTIALLY_PAID", "LATE", "DRAFT"].includes(s)) return "warning";
  if (["FAILED", "OVERDUE", "BLOCKED", "ABSENT", "CANCELLED"].includes(s)) return "danger";
  if (["EXCUSED", "HALF_DAY"].includes(s)) return "info";
  return "neutral";
};

export const initials = (first?: string, last?: string) => `${first?.[0] || ""}${last?.[0] || ""}`.toUpperCase() || "K";

export const titleCase = (value: unknown) => {
  const str = String(value || "—");
  return statusLabels[str] || str.replaceAll("_", " ").toLocaleLowerCase("tr-TR").replace(/(^|\s)\S/g, (c) => c.toLocaleUpperCase("tr-TR"));
};

export const formatTime = (value: unknown) => {
  if (!value) return "—";
  const raw = String(value);
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("tr-TR", { hour: "2-digit", minute: "2-digit" }).format(date);
};

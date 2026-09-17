const headerLabels: Record<string, string> = {
  academic_year: "Akademik yıl", amount: "Tutar", attendance_rate: "Katılım oranı",
  branch_name: "Şube", capacity: "Kapasite", class_code: "Sınıf kodu", class_name: "Sınıf",
  date: "Tarih", days_overdue: "Gecikme günü", due_date: "Vade", end_date: "Bitiş",
  excused: "İzinli", half_day: "Yarım gün", late: "Geç", month: "Ay", new_students: "Yeni öğrenci",
  occupancy_rate: "Doluluk oranı", paid_amount: "Ödenen", parent_email: "Veli e-posta",
  parent_phone: "Veli telefonu", payment_count: "Ödeme sayısı", period_end: "Dönem sonu",
  period_start: "Dönem başlangıcı", present: "Geldi", remaining_amount: "Kalan",
  start_date: "Başlangıç", status: "Durum", student_count: "Öğrenci sayısı",
  student_name: "Öğrenci", total_amount: "Toplam tutar", total_revenue: "Toplam gelir",
  total_students: "Toplam öğrenci", type: "Tür", year: "Yıl", absent: "Gelmedi",
};

function csvCell(value: unknown): string {
  let text = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

export function createCsv<T extends object>(rows: T[]): string {
  if (!rows.length) return "";
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
    .filter((key) => key !== "id" && !key.endsWith("_id"));
  const header = keys.map((key) => csvCell(headerLabels[key] || key.replaceAll("_", " "))).join(",");
  const body = rows.map((row) => {
    const values = row as Record<string, unknown>;
    return keys.map((key) => csvCell(values[key])).join(",");
  }).join("\r\n");
  return `${header}\r\n${body}`;
}

export function downloadCsv<T extends object>(filename: string, rows: T[]): boolean {
  const csv = createCsv(rows);
  if (!csv) return false;
  const safeName = filename.replace(/[^a-z0-9_-]+/gi, "-").replace(/^-|-$/g, "") || "rapor";
  const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeName}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
  return true;
}

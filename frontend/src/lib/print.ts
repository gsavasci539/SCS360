export interface PrintColumn {
  key: string;
  label: string;
  format?: (value: unknown, row: Record<string, unknown>) => string;
}

interface PrintReportOptions {
  title: string;
  subtitle?: string;
  organization?: string;
  columns: PrintColumn[];
  rows: Record<string, unknown>[];
  summary?: Array<{ label: string; value: string }>;
}

function escapeHtml(value: unknown): string {
  return String(value ?? "—")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function printReport({ title, subtitle, organization, columns, rows, summary = [] }: PrintReportOptions) {
  const printWindow = window.open("", "_blank", "width=1120,height=760");
  if (!printWindow) throw new Error("Yazdırma penceresi açılamadı. Tarayıcı açılır pencere iznini kontrol edin.");
  printWindow.opener = null;

  const generatedAt = new Date().toLocaleString("tr-TR");
  const tableRows = rows.length
    ? rows.map((row) => `<tr>${columns.map((column) => {
      const raw = row[column.key];
      return `<td>${escapeHtml(column.format ? column.format(raw, row) : raw)}</td>`;
    }).join("")}</tr>`).join("")
    : `<tr><td class="empty" colspan="${Math.max(columns.length, 1)}">Bu rapor için kayıt bulunmuyor.</td></tr>`;

  printWindow.document.write(`<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
  @page { size: A4 landscape; margin: 14mm; }
  * { box-sizing: border-box; }
  body { margin: 0; color: #17282b; font: 12px Arial, sans-serif; background: #fff; }
  header { display: flex; justify-content: space-between; gap: 24px; padding-bottom: 16px; border-bottom: 3px solid #176b5b; }
  .brand { color: #176b5b; font-size: 13px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; }
  h1 { margin: 6px 0 4px; font-size: 23px; }
  p { margin: 0; color: #647275; }
  .meta { text-align: right; color: #647275; line-height: 1.6; }
  .summary { display: grid; grid-template-columns: repeat(${Math.max(summary.length, 1)}, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }
  .summary div { padding: 11px 13px; border: 1px solid #dfe6e1; border-radius: 7px; background: #f7faf8; }
  .summary small { display: block; color: #647275; margin-bottom: 4px; }
  .summary strong { font-size: 15px; }
  table { width: 100%; margin-top: 16px; border-collapse: collapse; table-layout: auto; }
  th { padding: 9px 8px; color: #fff; background: #176b5b; font-size: 10px; text-align: left; text-transform: uppercase; }
  td { padding: 8px; border-bottom: 1px solid #dfe6e1; vertical-align: top; }
  tbody tr:nth-child(even) { background: #f7faf8; }
  .empty { padding: 30px; color: #647275; text-align: center; }
  footer { margin-top: 14px; padding-top: 9px; border-top: 1px solid #dfe6e1; color: #7b8789; font-size: 10px; }
</style></head><body>
<header><div><div class="brand">${escapeHtml(organization || "SCS Okul Yönetim Sistemi")}</div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(subtitle || "")}</p></div><div class="meta">Oluşturulma<br><strong>${escapeHtml(generatedAt)}</strong></div></header>
${summary.length ? `<section class="summary">${summary.map((item) => `<div><small>${escapeHtml(item.label)}</small><strong>${escapeHtml(item.value)}</strong></div>`).join("")}</section>` : ""}
<table><thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr></thead><tbody>${tableRows}</tbody></table>
<footer>Bu belge sistemdeki güncel kayıtlar kullanılarak otomatik oluşturulmuştur.</footer>
</body></html>`);
  printWindow.document.close();
  printWindow.focus();
  window.setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 250);
}

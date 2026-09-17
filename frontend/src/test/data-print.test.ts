import { afterEach, describe, expect, it, vi } from "vitest";
import { toArray, toPaginated } from "../lib/data";
import { printReport } from "../lib/print";
import { dateInputValue, monthInputValue, shortDate } from "../lib/format";
import { createCsv } from "../lib/export";

describe("API veri normalizasyonu", () => {
  it("dizi ve sayfalı cevapları güvenli biçimde işler", () => {
    const rows = [{ id: "1" }];
    expect(toArray(rows)).toEqual(rows);
    expect(toArray({ items: rows, total: 1, page: 1, page_size: 20, total_pages: 1 })).toEqual(rows);
    expect(toArray(undefined)).toEqual([]);
    expect(toPaginated(undefined).items).toEqual([]);
  });
});

describe("yerel tarih biçimleme", () => {
  it("tarih girdisini UTC'ye dönüştürmeden üretir", () => {
    const date = new Date(2026, 0, 2, 0, 30);
    expect(dateInputValue(date)).toBe("2026-01-02");
    expect(monthInputValue(date)).toBe("2026-01");
    expect(shortDate("2026-01-02")).toContain("2026");
  });
});

describe("CSV dışa aktarma", () => {
  it("gizli kimlik alanlarını çıkarır ve formül enjeksiyonunu etkisizleştirir", () => {
    const csv = createCsv([{ id: "1", student_id: "2", student_name: "=2+2", amount: 100 }]);
    expect(csv).toContain("Öğrenci");
    expect(csv).toContain("'=2+2");
    expect(csv).not.toContain("student_id");
  });
});

describe("rapor yazdırma şablonu", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("yalnızca rapor verilerinden özel belge üretir", () => {
    vi.useFakeTimers();
    const write = vi.fn();
    const close = vi.fn();
    const focus = vi.fn();
    const print = vi.fn();
    const printWindow = { document: { write, close }, focus, print, close, opener: window } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(printWindow);

    printReport({
      title: "Aylık Tahsilat",
      subtitle: "Haziran 2026",
      columns: [{ key: "student", label: "Öğrenci" }, { key: "amount", label: "Tutar" }],
      rows: [{ student: "Ayşe Yılmaz", amount: "1.500 TL" }],
    });
    vi.runAllTimers();

    const html = String(write.mock.calls[0][0]);
    expect(html).toContain("Aylık Tahsilat");
    expect(html).toContain("Ayşe Yılmaz");
    expect(html).toContain("Bu belge sistemdeki güncel kayıtlar");
    expect(print).toHaveBeenCalledOnce();
    expect(close).toHaveBeenCalled();
  });

  it("rapor metnindeki HTML içeriğini çalıştırılabilir belgeye dönüştürmez", () => {
    vi.useFakeTimers();
    const write = vi.fn();
    const printWindow = { document: { write, close: vi.fn() }, focus: vi.fn(), print: vi.fn(), close: vi.fn(), opener: window } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(printWindow);
    printReport({ title: "Test", columns: [{ key: "value", label: "Değer" }], rows: [{ value: '<img src=x onerror="alert(1)">' }] });
    const html = String(write.mock.calls[0][0]);
    expect(html).toContain("&lt;img");
    expect(html).not.toContain('<img src=x onerror="alert(1)">');
  });
});

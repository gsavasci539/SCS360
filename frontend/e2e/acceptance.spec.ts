import { expect, test, type Page } from "./fixtures";
import { readFile } from "node:fs/promises";

const sessions = new Map<string, Array<{ name: string; value: string }>>();

test("pickup desk verifies registered identity preserves delivery history and revokes grants on mobile", async ({ page }) => {
  const suffix = Date.now(), adult = `Yetkili teslim ${suffix}`, identity = `ACCEPTANCE-${suffix}`;
  await login(page, "admin"); await page.setViewportSize({ width: 390, height: 844 });
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.goto("/dismissal"); await page.getByLabel("Teslim öğrencisi", { exact: true }).selectOption({ label: "Deniz Kabul" });
  const grant = page.getByRole("form", { name: "Teslim yetkisi oluştur", exact: true });
  await grant.getByLabel("Yetkili yetişkin adı", { exact: true }).fill(adult); await grant.getByLabel("Yetkili kimlik belgesi numarası", { exact: true }).fill(identity);
  await grant.getByLabel("Yetkili fotoğraf bağlantısı", { exact: true }).fill("/private/test-reference.svg");
  await grant.getByRole("button", { name: "Teslim yetkisini kaydet", exact: true }).click();
  const row = page.getByRole("region", { name: "Teslim yetkileri", exact: true }).getByRole("row").filter({ hasText: adult });
  await expect(row).toBeVisible();
  const delivery = page.getByRole("form", { name: "Öğrenci teslimini kaydet", exact: true });
  await expect(delivery.getByLabel("Teslim alanın kimlik belgesi numarası", { exact: true })).toHaveValue("");
  await delivery.getByLabel("Teslim alanın kimlik belgesi numarası", { exact: true }).fill("WRONG-ID");
  await delivery.getByRole("button", { name: "Kimliği doğrula ve teslimi kaydet", exact: true }).click(); await expect(delivery.getByRole("alert")).toContainText("eşleşmedi");
  await delivery.getByLabel("Teslim alanın kimlik belgesi numarası", { exact: true }).fill(identity);
  await delivery.getByRole("button", { name: "Kimliği doğrula ve teslimi kaydet", exact: true }).click(); await expect(delivery.getByRole("status")).toContainText(adult);
  await expect(page.getByLabel("Teslim özeti", { exact: true })).toContainText("Seçili gün teslim kaydı: 1");
  await row.getByText("Yetkiyi aç", { exact: true }).click(); await row.getByRole("button", { name: "Yetkiyi düzenle", exact: true }).click();
  await expect(grant.getByLabel("Yetkili fotoğraf bağlantısı", { exact: true })).toHaveValue("/private/test-reference.svg");
  await grant.getByLabel("Yetkili yetişkin adı", { exact: true }).fill(`${adult} güncel`); await grant.getByRole("button", { name: "Yetki değişikliğini kaydet", exact: true }).click();
  await expect(row).toContainText(`${adult} güncel`); await row.getByRole("button", { name: "Teslim yetkisini iptal et", exact: true }).click();
  await expect(row).toContainText("İptal edildi");
  await delivery.getByLabel("Teslim alanın kimlik belgesi numarası", { exact: true }).fill(identity);
  await delivery.getByRole("button", { name: "Kimliği doğrula ve teslimi kaydet", exact: true }).click(); await expect(delivery.getByRole("alert")).toContainText("eşleşmedi");
  await page.reload(); await expect(row).toContainText("İptal edildi");
  const history = page.getByRole("region", { name: "Teslim geçmişi", exact: true }); await expect(history.getByRole("row")).toHaveCount(2);
  await expect(history.getByRole("cell", { name: adult, exact: true })).toBeVisible(); await history.getByText("Teslimi aç", { exact: true }).click(); await expect(history).toContainText("Admin Kabul");
  expect(failures).toEqual([]); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/dismissal-acceptance-mobile.png", fullPage: true });
});

test("student credentials download private QR and gate entry exit revocation persist on mobile", async ({ page }) => {
  await page.addInitScript(() => { Object.defineProperty(window.crypto, "randomUUID", { configurable: true, value: undefined }); });
  await login(page, "admin"); await page.setViewportSize({ width: 390, height: 844 });
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.goto("/security"); await page.getByLabel("Kimlik öğrencisi", { exact: true }).selectOption({ label: "Deniz Kabul" });
  const issue = page.getByRole("form", { name: "Öğrenci kimliği oluştur", exact: true });
  const issued = page.waitForResponse((response) => response.url().endsWith("/api/security/digital-id/generate") && response.request().method() === "POST");
  await issue.getByRole("button", { name: "Öğrenci kimliğini oluştur", exact: true }).click();
  const issuedResponse = await issued; expect(issuedResponse.status()).toBe(200); const token = (await issuedResponse.json()).data;
  const row = page.getByRole("region", { name: "Öğrenci kimlikleri", exact: true }).getByRole("row").filter({ hasText: token.token });
  await row.getByText("Kimliği aç", { exact: true }).click();
  const [download] = await Promise.all([page.waitForEvent("download"), row.getByRole("button", { name: "QR kodunu indir", exact: true }).click()]);
  expect(download.suggestedFilename()).toBe(`SCS360-kimlik-${token.student_id}.svg`); expect(await download.failure()).toBeNull();
  expect((await readFile((await download.path())!)).toString("utf8")).toContain("<svg");
  const gate = page.getByRole("form", { name: "Kapı geçişi kaydet", exact: true });
  await gate.getByLabel("QR / barkod değeri", { exact: true }).fill(token.token); await gate.getByLabel("Kapı / konum", { exact: true }).fill("Kabul Kapısı");
  await gate.getByRole("button", { name: "Kodu doğrula ve geçişi kaydet", exact: true }).click();
  await expect(gate.getByRole("status")).toContainText("Deniz Kabul"); await expect(page.getByLabel("Kapı özeti", { exact: true })).toContainText("Son kayda göre içeride: 1");
  await gate.getByLabel("QR / barkod değeri", { exact: true }).fill(token.token); await gate.getByLabel("Geçiş yönü", { exact: true }).selectOption("OUT");
  await gate.getByRole("button", { name: "Kodu doğrula ve geçişi kaydet", exact: true }).click();
  await expect(page.getByLabel("Kapı özeti", { exact: true })).toContainText("Çıkış kaydı: 1"); await expect(page.getByLabel("Kapı özeti", { exact: true })).toContainText("Son kayda göre içeride: 0");
  await row.getByRole("button", { name: "Kimliği iptal et", exact: true }).click(); await expect(row).toContainText("İptal edildi");
  await page.reload(); await expect(row).toContainText("İptal edildi");
  const logs = page.getByRole("region", { name: "Kapı kayıtları", exact: true }); await expect(logs.getByRole("row")).toHaveCount(3);
  await logs.getByText("Geçişi aç", { exact: true }).first().click(); await expect(logs).toContainText("Admin Kabul");
  expect(failures).toEqual([]); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/security-acceptance-mobile.png", fullPage: true });
});

test("infirmary files visits follow-ups and dose logs persist and parent rejection stays rejected", async ({ page, browser }) => {
  const suffix = Date.now(), medicine = `Kayıt testi ${suffix}`, complaint = `Revir kaydı ${suffix}`;
  await login(page, "admin"); await page.setViewportSize({ width: 390, height: 844 });
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.goto("/health"); await page.getByLabel("Sağlık öğrencisi", { exact: true }).selectOption({ label: "Deniz Kabul" });
  const file = page.getByRole("form", { name: "Sağlık dosyasını düzenle", exact: true });
  await file.getByLabel("Alerji bilgisi", { exact: true }).fill(`Kabul bilgisi ${suffix}`);
  await file.getByLabel("Acil kişi adı", { exact: true }).fill("Kabul velisi");
  await file.getByRole("button", { name: "Sağlık dosyasını kaydet", exact: true }).click();
  await expect(page.getByRole("region", { name: "Sağlık dosyaları", exact: true })).toContainText(`Kabul bilgisi ${suffix}`);
  const visit = page.getByRole("form", { name: "Revir ziyareti oluştur", exact: true });
  await visit.getByLabel("Şikâyet", { exact: true }).fill(complaint); await visit.getByLabel("Takip gerekli", { exact: true }).check();
  await visit.getByRole("button", { name: "Revir ziyaretini kaydet", exact: true }).click();
  const visitRow = page.getByRole("region", { name: "Revir ziyaretleri", exact: true }).getByRole("row").filter({ hasText: complaint });
  await visitRow.getByText("Kaydı aç", { exact: true }).click(); await visitRow.getByLabel("Takip sonuç notu", { exact: true }).fill("Takip kaydı tamamlandı.");
  await visitRow.getByRole("button", { name: "Takibi tamamla", exact: true }).click(); await expect(visitRow).toContainText("Bekleyen takip yok");
  const program = page.getByRole("form", { name: "İlaç programı oluştur", exact: true });
  await program.getByLabel("Program ilaç adı", { exact: true }).fill(medicine); await program.getByLabel("Kayıtlı doz", { exact: true }).fill("Kabul kaydı");
  await program.getByLabel("Saat / sıklık talimatı", { exact: true }).fill("10:00");
  await program.getByRole("button", { name: "İlaç programını kaydet", exact: true }).click();
  const programRow = page.getByRole("region", { name: "İlaç programları ve talepler", exact: true }).getByRole("row").filter({ hasText: medicine });
  await programRow.getByText("Kaydı aç", { exact: true }).click(); await programRow.getByLabel("Planlanan doz saati", { exact: true }).fill("10:00");
  await programRow.getByRole("button", { name: "Doz sonucunu kaydet", exact: true }).click();
  const doses = page.getByRole("region", { name: "Günlük doz kayıtları", exact: true }); await expect(doses).toContainText("Verildi");
  await page.reload(); await expect(doses).toContainText("Verildi");
  const parentContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const parent = await parentContext.newPage(); await login(parent, "parent"); await parent.goto("/parent/health");
    const parentForm = parent.getByRole("form", { name: "İlaç talimatı gönder", exact: true });
    const requestName = `Veli talimatı ${suffix}`;
    await parentForm.getByLabel("İlaç Adı", { exact: true }).fill(requestName); await parentForm.getByLabel("Doz", { exact: true }).fill("Kabul talimatı");
    await parentForm.getByLabel("Uygulama Saati", { exact: true }).fill("11:00");
    await parentForm.getByLabel("İlaç talimatı notu", { exact: true }).fill("Uzun talimat metni ".repeat(15));
    await parentForm.getByRole("button", { name: "Talimatı Gönder", exact: true }).click();
    await expect(parent.getByText("İlaç talimatı okul ekibine iletildi.", { exact: true })).toBeVisible();
    await page.reload(); const requestRow = page.getByRole("region", { name: "İlaç programları ve talepler", exact: true }).getByRole("row").filter({ hasText: requestName });
    await requestRow.getByText("Kaydı aç", { exact: true }).click(); await requestRow.getByRole("button", { name: "İlaç talebini reddet", exact: true }).click();
    await expect(requestRow).toContainText("Reddedildi"); await parent.reload();
    await expect(parent.locator(".parent-request-card").filter({ hasText: requestName })).toContainText("Reddedildi");
  } finally { await parentContext.close(); }
  expect(failures).toEqual([]); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/infirmary-acceptance-mobile.png", fullPage: true });
});

test("tutoring teacher availability request approval booking and attendance persist on mobile", async ({ page }) => {
  const subject = `Etüt kabulü ${Date.now()}`;
  await login(page, "teacher"); await page.setViewportSize({ width: 390, height: 844 });
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.goto("/tutoring");
  await page.getByLabel("Etüt öğrencisi", { exact: true }).selectOption({ label: "Deniz Kabul" });
  await page.getByLabel("Etüt öğretmeni", { exact: true }).selectOption({ label: "Teacher Kabul" });
  const window = page.getByRole("form", { name: "Müsaitlik oluştur", exact: true });
  await window.getByRole("button", { name: "Müsaitliği kaydet", exact: true }).click();
  await expect(page.getByRole("region", { name: "Öğretmen müsaitlikleri", exact: true })).toContainText("Açık");
  const request = page.getByRole("form", { name: "Etüt talebi oluştur", exact: true });
  await request.getByLabel("Talep ders adı", { exact: true }).fill(subject);
  await request.getByLabel("Tercih başlangıcı", { exact: true }).fill("10:00");
  await request.getByLabel("Tercih bitişi", { exact: true }).fill("11:00");
  await request.getByRole("button", { name: "Talep oluştur", exact: true }).click();
  const requestRow = page.getByRole("region", { name: "Ders talepleri", exact: true }).getByRole("row").filter({ hasText: subject });
  await requestRow.getByText("Kaydı aç", { exact: true }).click();
  await requestRow.getByRole("button", { name: "Talebi onayla", exact: true }).click();
  await requestRow.getByRole("button", { name: "Bu talep için ders planla", exact: true }).click();
  const plan = page.getByRole("form", { name: "Etüt planla", exact: true });
  await expect(plan.getByLabel("Ders adı", { exact: true })).toHaveValue(subject);
  await plan.getByRole("button", { name: "Dersi planla", exact: true }).click();
  const lesson = page.getByRole("region", { name: "Etüt oturumları", exact: true }).getByRole("row").filter({ hasText: subject });
  await lesson.getByText("Kaydı aç", { exact: true }).click();
  await lesson.getByLabel("İlerleme puanı", { exact: true }).fill("87");
  await lesson.getByRole("button", { name: "Devamı kaydet", exact: true }).click();
  await expect(lesson).toContainText("87/100");
  await page.reload(); await lesson.getByText("Kaydı aç", { exact: true }).click(); await expect(lesson).toContainText("87/100");
  await requestRow.getByText("Kaydı aç", { exact: true }).click(); await expect(requestRow).toContainText("Teacher Kabul");
  expect(failures).toEqual([]); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/tutoring-acceptance-mobile.png", fullPage: true });
});

test("payroll timesheets additional hours drafts and approval use real persisted amounts", async ({ page }) => {
  const note = `Kabul bordrosu ${Date.now()}`;
  await login(page, "admin"); await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/payroll");
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
  await page.getByLabel("Bordro personeli", { exact: true }).selectOption({ label: "Teacher Kabul · Kabul Test Okulu" });
  const timesheet = page.getByRole("form", { name: "Puantaj oluştur", exact: true });
  await timesheet.getByLabel("Çalışma saati", { exact: true }).fill("8");
  await timesheet.getByRole("button", { name: "Puantajı kaydet", exact: true }).click();
  await expect(page.getByRole("region", { name: "Puantaj kayıtları", exact: true })).toContainText("8 saat");
  const extra = page.getByRole("form", { name: "Ek ders kaydı oluştur", exact: true });
  await extra.getByLabel("Ek ders saati", { exact: true }).fill("4"); await extra.getByLabel("Saat ücreti", { exact: true }).fill("125.50");
  await extra.getByRole("button", { name: "Ek dersi kaydet", exact: true }).click();
  await expect(page.getByRole("region", { name: "Ek ders kayıtları", exact: true })).toContainText("502");
  const draft = page.getByRole("form", { name: "Bordro taslağı oluştur", exact: true });
  await draft.getByLabel("Temel tutar", { exact: true }).fill("50000"); await draft.getByLabel("Bordro ek ders tutarı", { exact: true }).fill("502");
  await draft.getByLabel("Prim", { exact: true }).fill("500"); await draft.getByLabel("Avans", { exact: true }).fill("1000"); await draft.getByLabel("Kesinti", { exact: true }).fill("200");
  await draft.getByLabel("Bordro notu", { exact: true }).fill(note);
  const saved = page.waitForResponse((response) => response.url().endsWith("/api/payroll/records") && response.request().method() === "POST");
  await draft.getByRole("button", { name: "Bordro taslağını kaydet", exact: true }).click();
  expect((await (await saved).json()).data.net_salary).toBe(49802);
  const row = page.getByRole("region", { name: "Bordro kayıtları", exact: true }).getByRole("row").filter({ hasText: note });
  await row.getByText("Kaydı aç", { exact: true }).click(); await row.getByRole("button", { name: "Bordroyu onayla", exact: true }).click();
  await expect(row.getByText("Onaylandı", { exact: true })).toBeVisible();
  await page.reload(); await expect(row.getByText("Onaylandı", { exact: true })).toBeVisible();
  await row.getByText("Kaydı aç", { exact: true }).click(); await expect(row).toContainText("Admin Kabul");
  expect(failures).toEqual([]); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/payroll-acceptance-mobile.png", fullPage: true });
});

test("guidance sessions notes and incident resolutions persist with actual counters", async ({ page }) => {
  const suffix = Date.now(); const summary = `Görüşme özeti ${suffix}`; const note = `Gizli danışman notu ${suffix}`; const incident = `Olay kaydı ${suffix}`;
  await login(page, "admin"); await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/guidance");
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
  await page.getByLabel("Rehberlik öğrencisi", { exact: true }).selectOption({ label: "Deniz Kabul" });
  await expect(page.getByLabel("Kayıt danışmanı", { exact: true })).toHaveValue(/.+/);
  const sessionForm = page.getByRole("form", { name: "Görüşme oluştur", exact: true });
  await sessionForm.getByLabel("Görüşme özeti", { exact: true }).fill(summary);
  await sessionForm.getByLabel("Gizlilik düzeyi", { exact: true }).selectOption("CONFIDENTIAL");
  await sessionForm.getByRole("button", { name: "Görüşmeyi kaydet", exact: true }).click();
  const session = page.getByRole("region", { name: "Görüşmeler", exact: true }).getByRole("row").filter({ hasText: summary });
  await session.getByText("Görüşme ayrıntısı", { exact: true }).click(); await expect(session.getByText(summary, { exact: true })).toBeVisible();
  const noteForm = page.getByRole("form", { name: "Danışman notu oluştur", exact: true });
  await noteForm.getByLabel("Danışman notu", { exact: true }).fill(note);
  await noteForm.getByLabel("Gizlilik düzeyi", { exact: true }).selectOption("CONFIDENTIAL");
  await noteForm.getByRole("button", { name: "Notu kaydet", exact: true }).click();
  const noteRow = page.getByRole("region", { name: "Danışman notları", exact: true }).getByRole("row").filter({ hasText: note });
  await noteRow.getByText("Notu oku", { exact: true }).click(); await expect(noteRow.getByText(note, { exact: true })).toBeVisible();
  await page.getByLabel("Olay açıklaması", { exact: true }).fill(incident);
  await page.getByRole("button", { name: "Olayı kaydet", exact: true }).click();
  const row = page.getByRole("region", { name: "Davranış olayları", exact: true }).getByRole("row").filter({ hasText: incident });
  await row.getByText("Olay ayrıntısı", { exact: true }).click();
  await row.getByLabel("Çözüm notu", { exact: true }).fill("Görüşme ve takip tamamlandı.");
  await row.getByRole("button", { name: "Çözüldü olarak kaydet", exact: true }).click();
  await expect(row).toContainText("Çözüldü");
  await page.reload(); await expect(row).toContainText("Çözüldü");
  await row.getByText("Olay ayrıntısı", { exact: true }).click();
  await expect(row).toContainText("Görüşme ve takip tamamlandı.");
  expect(failures).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/guidance-acceptance-mobile.png", fullPage: true });
});

test("published anonymous survey accepts parent and staff answers and displays real results", async ({ page, browser }) => {
  const title = `Kurum anketi ${Date.now()}`;
  await login(page, "admin"); await page.goto("/surveys");
  await page.getByLabel("Anket başlığı", { exact: true }).fill(title);
  await page.getByLabel("Hedef kitle", { exact: true }).selectOption("ALL");
  await page.getByLabel("Başlangıç tarihi", { exact: true }).fill("2026-01-01");
  await page.getByLabel("Bitiş tarihi", { exact: true }).fill("2030-01-01");
  await page.getByLabel("Anonim yanıt topla", { exact: true }).check();
  await page.getByRole("button", { name: "Anket taslağını oluştur", exact: true }).click();
  await expect(page).toHaveURL(/\/surveys\?survey=/);
  await page.getByLabel("Soru metni", { exact: true }).fill("Okul memnuniyeti");
  await page.getByRole("button", { name: "Soruyu ekle", exact: true }).click();
  await expect(page.getByRole("button", { name: "Soruyu kaldır: Okul memnuniyeti", exact: true })).toBeVisible();
  await page.getByLabel("Soru türü", { exact: true }).selectOption("MULTIPLE_CHOICE");
  await page.getByLabel("Soru metni", { exact: true }).fill("Tekrar katılır mısınız?");
  await page.getByLabel("Seçenekler (her satıra bir seçenek)", { exact: true }).fill("Evet\nHayır");
  await page.getByRole("button", { name: "Soruyu ekle", exact: true }).click();
  await expect(page.getByRole("button", { name: "Soruyu kaldır: Tekrar katılır mısınız?", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Anketi yayımla", exact: true }).click();
  await expect(page.getByRole("button", { name: "Yanıt alımını kapat", exact: true })).toBeVisible();
  for (const [role, path, score] of [["parent", "/parent/surveys", "5"], ["teacher", "/my-surveys", "3"]] as const) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    try {
      const participant = await context.newPage(); await login(participant, role);
      const failures: string[] = [];
      participant.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
      await participant.goto(path);
      const card = participant.locator("article").filter({ has: participant.getByRole("heading", { name: title, exact: true }) });
      await card.getByLabel("Okul memnuniyeti", { exact: true }).selectOption(score);
      await card.getByLabel("Tekrar katılır mısınız?", { exact: true }).selectOption("Evet");
      await card.getByRole("button", { name: "Anketi yanıtla", exact: true }).click();
      await expect(card.getByRole("status")).toHaveText("Yanıtınız kaydedildi.");
      await participant.reload(); await expect(card.getByRole("status")).toHaveText("Yanıtınız kaydedildi.");
      expect(await participant.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(failures).toEqual([]);
      if (role === "parent") await participant.screenshot({ path: "../output/survey-acceptance-mobile.png", fullPage: true });
    } finally { await context.close(); }
  }
  await page.reload();
  await expect(page.getByText("Geçerli yanıt: 2 · Ortalama: 4 / 5", { exact: true })).toBeVisible();
  const answers = page.getByRole("region", { name: "Anket yanıtları" });
  await expect(answers.getByText(/Anonim katılımcı/)).toHaveCount(2);
  await expect(answers).not.toContainText("Parent Kabul"); await expect(answers).not.toContainText("Teacher Kabul");
});

test("consent document is read and decided by its linked guardian with persistent version", async ({ page, browser }) => {
  const title = `Veli gezi izni ${Date.now()}`;
  const content = "Kabul gezisinin kapsamı, tarihleri ve koşulları. Türkçe: ığüşöç İĞÜŞÖÇ.";
  await login(page, "admin");
  await page.goto("/consents");
  await expect(page.getByLabel("Belge kurumu", { exact: true })).toHaveValue(/.+/);
  await page.getByLabel("Belge başlığı", { exact: true }).fill(title);
  await page.getByLabel("Yürürlük tarihi", { exact: true }).fill("2026-01-01");
  await page.getByLabel("Belgenin tam metni", { exact: true }).fill(content);
  await page.getByRole("button", { name: "Belgeyi oluştur", exact: true }).click();
  await expect(page.getByRole("heading", { name: `${title} · v1.0`, exact: true })).toBeVisible();
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const parent = await context.newPage();
    await login(parent, "parent");
    const failures: string[] = [];
    parent.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
    await parent.goto("/parent/consents");
    const card = parent.locator("article").filter({ hasText: title });
    await card.getByText("Belgenin tam metnini oku", { exact: true }).click();
    await expect(card.getByText(content, { exact: true })).toBeVisible();
    await expect(card.getByRole("button", { name: "Onaylıyorum", exact: true })).toBeDisabled();
    await card.getByLabel("Adınız ve soyadınız", { exact: true }).fill("Parent Kabul");
    await card.getByRole("checkbox").check();
    await card.getByRole("button", { name: "Onaylıyorum", exact: true }).click();
    await expect(card.getByText("Onaylandı", { exact: true })).toBeVisible();
    await parent.reload();
    await expect(card.getByText("Onaylandı", { exact: true })).toBeVisible();
    expect(await parent.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await parent.screenshot({ path: "../output/consent-acceptance-mobile.png", fullPage: true });
    await page.reload();
    const row = page.getByRole("region", { name: "Kayıtlı veli kararları" }).getByRole("row").filter({ hasText: title });
    await expect(row).toContainText("Deniz Kabul");
    await expect(row).toContainText("Parent Kabul");
    await expect(row).toContainText("Veli portalı");
    await expect(row).toContainText("Onaylandı");
    expect(failures).toEqual([]);
  } finally { await context.close(); }
});

test("inventory forms persist locations, assets, assignments, returns and maintenance", async ({ page }) => {
  const suffix = Date.now();
  const code = `QA-${suffix}`;
  const name = `Kabul tableti ${suffix}`;
  const room = `Kabul odası ${suffix}`;
  await login(page, "admin");
  await page.goto("/inventory");
  await expect(page.getByLabel("Envanter şubesi")).toHaveValue(/.+/);
  await page.getByLabel("Konum adı", { exact: true }).fill(room);
  await page.getByRole("button", { name: "Konumu oluştur", exact: true }).click();
  await page.getByLabel("Demirbaş kodu", { exact: true }).fill(code);
  await page.getByLabel("Demirbaş adı", { exact: true }).fill(name);
  await page.getByLabel("Demirbaş konumu", { exact: true }).selectOption({ label: room });
  await page.getByRole("button", { name: "Demirbaşı oluştur", exact: true }).click();
  await expect(page.getByRole("cell", { name, exact: true })).toBeVisible();
  await page.getByLabel("Demirbaş ara", { exact: true }).fill(code);
  await page.getByRole("combobox", { name: "İşlem demirbaşı", exact: true }).selectOption({ label: `${code} · ${name}` });
  await page.getByRole("combobox", { name: "Zimmet sorumlusu", exact: true }).selectOption({ label: "Teacher Kabul" });
  await page.getByRole("button", { name: "Zimmeti kaydet", exact: true }).click();
  const assigned = page.getByRole("region", { name: "Demirbaş zimmetleri", exact: true }).getByRole("row").filter({ hasText: name });
  await expect(assigned.getByText("Zimmetli", { exact: true })).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await assigned.getByRole("button", { name: `${name} iade al`, exact: true }).click();
  await expect(assigned.getByText("İade edildi", { exact: true })).toBeVisible();
  await page.getByLabel("Bakım açıklaması", { exact: true }).fill("Kalıcı kontrol talebi");
  await page.getByRole("button", { name: "Bakım talebini kaydet", exact: true }).click();
  const request = page.getByRole("region", { name: "Demirbaş bakım talepleri", exact: true }).getByRole("row").filter({ hasText: name });
  await expect(request.getByText("Kalıcı kontrol talebi", { exact: true })).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await request.getByRole("button", { name: `${name} bakımını tamamla`, exact: true }).click();
  await expect(request.getByText("Çözüldü", { exact: true })).toBeVisible();
  await page.reload();
  await expect(assigned.getByText("İade edildi", { exact: true })).toBeVisible();
  await expect(request.getByText("Çözüldü", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("club enrollment, events and certificate downloads persist for admin and linked parent", async ({ page, browser }) => {
  const suffix = Date.now();
  const clubName = `Kabul sanat kulübü ${suffix}`;
  const eventName = `Kabul sergisi ${suffix}`;
  const title = `Sanat katılım belgesi ${suffix}`;
  await login(page, "admin");
  await page.goto("/clubs");
  await expect(page.getByLabel("İşlem şubesi")).toHaveValue(/.+/);
  await page.getByLabel("Kulüp adı", { exact: true }).fill(clubName);
  await page.getByRole("button", { name: "Kulübü oluştur", exact: true }).click();
  await expect(page.getByLabel("İşlem kulübü")).toHaveValue(/.+/);
  await page.getByLabel("İşlem öğrencisi").selectOption({ label: "Deniz Kabul · KABUL-001" });
  await page.getByRole("button", { name: "Üyeliği kaydet", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: clubName }).filter({ hasText: "Deniz Kabul" })).toBeVisible();
  await page.getByLabel("Etkinlik adı", { exact: true }).fill(eventName);
  await page.getByLabel("Etkinlik tarihi", { exact: true }).fill("2027-01-01");
  await page.getByRole("button", { name: "Etkinliği oluştur", exact: true }).click();
  await expect(page.getByRole("cell", { name: eventName, exact: true })).toBeVisible();
  await page.getByLabel("Belge başlığı", { exact: true }).fill(title);
  await page.getByLabel("Belge açıklaması", { exact: true }).fill("Yaratıcı çalışmalarını başarıyla tamamlamıştır.");
  await page.getByLabel("Belge etkinliği", { exact: true }).selectOption({ label: eventName });
  await page.getByRole("button", { name: "Belgeyi oluştur", exact: true }).click();
  await page.reload();
  const downloadPending = page.waitForEvent("download");
  await page.getByRole("button", { name: `${title} indir`, exact: true }).click();
  const file = await downloadPending;
  const bytes = await readFile((await file.path())!);
  expect(bytes.subarray(0, 5).toString()).toBe("%PDF-");
  expect(file.suggestedFilename()).toBe(`${title}.pdf`);
  const parentContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const parent = await parentContext.newPage();
    await login(parent, "parent");
    await parent.goto("/parent/activities");
    const card = parent.getByRole("region", { name: "Çocuğun belgeleri" }).locator("div").filter({ has: parent.getByRole("heading", { name: title, exact: true }) }).last();
    await expect(card).toBeVisible();
    const parentDownload = parent.waitForEvent("download");
    await card.getByRole("button", { name: "Belgeyi indir", exact: true }).click();
    const parentBytes = await readFile((await (await parentDownload).path())!);
    expect(parentBytes.subarray(0, 5).toString()).toBe("%PDF-");
    expect(parentBytes.byteLength).toBeGreaterThan(10_000);
    expect(await parent.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally { await parentContext.close(); }
});

test("parent daily timeline displays a saved teacher report and opens its detail page", async ({ page, browser }) => {
  await login(page, "admin");
  const options = await page.evaluate(async () => {
    const { api } = await import("/src/lib/api.ts");
    const response = await api.get("/clubs/options");
    return (await api.get("/clubs/options", { params: { branch_id: response.data.data.branches[0].id } })).data.data;
  });
  const day = "2026-11-05";
  const note = `Kayıtlı günlük akış notu ${Date.now()}`;
  const report = await page.evaluate(async ({ studentId, date, notes }) => {
    const { api } = await import("/src/lib/api.ts");
    const existing = await api.get("/daily-reports", { params: { student_id: studentId, date } });
    const row = existing.data.data.items?.[0];
    const result = row ? await api.put(`/daily-reports/${row.id}`, { teacher_notes: notes }) :
      await api.post("/daily-reports", { student_id: studentId, date, teacher_notes: notes });
    return result.status;
  }, { studentId: options.students[0].id, date: day, notes: note });
  expect(report).toBe(200);
  const parentContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const parent = await parentContext.newPage();
    await login(parent, "parent");
    await parent.goto("/parent/children");
    const timeline = parent.getByRole("region", { name: "Çocuğun günlük akışı" });
    await timeline.getByLabel("Akış tarihi", { exact: true }).fill(day);
    await expect(timeline.getByText(note, { exact: true })).toBeVisible();
    await timeline.getByRole("listitem").filter({ hasText: note }).getByRole("link", { name: "İlgili sayfayı aç", exact: true }).click();
    await expect(parent).toHaveURL(/\/parent\/reports$/);
    await expect(parent.getByText(note, { exact: true })).toBeVisible();
    expect(await parent.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally { await parentContext.close(); }
});

test("parent submits an excuse and admin reviews the persisted request", async ({ page, browser }) => {
  await login(page, "parent");
  await page.goto("/parent/attendance");
  const description = `İstirahat kabul testi ${Date.now()}`;
  const section = page.getByRole("region", { name: "Mazeret talepleri", exact: true });
  await section.getByLabel("Başlangıç tarihi").fill("2026-11-03");
  await section.getByLabel("Bitiş tarihi").fill("2026-11-04");
  await section.getByLabel("Mazeret açıklaması").fill(description);
  const response = page.waitForResponse((item) => item.url().endsWith("/excuse-request"));
  await section.getByRole("button", { name: "Mazeret talebi gönder" }).click();
  expect((await response).status()).toBe(200);
  await expect(section.getByRole("row").filter({ hasText: description })).toBeVisible();
  const adminContext = await browser.newContext();
  try {
    const admin = await adminContext.newPage();
    await login(admin, "admin");
    const row = admin.getByRole("region", { name: "Bekleyen mazeret talepleri", exact: true }).getByRole("row").filter({ hasText: description });
    await expect(row).toBeVisible();
    const reviewed = admin.waitForResponse((item) => item.url().includes("/dashboard/excuse-requests/") && item.request().method() === "PUT");
    await row.getByRole("button", { name: "Onayla", exact: true }).click();
    expect((await reviewed).status()).toBe(200);
    await expect(row).toHaveCount(0);
  } finally { await adminContext.close(); }
  const historyResponse = page.waitForResponse((item) => item.url().includes("/excuse-requests") && item.request().method() === "GET");
  await page.reload();
  const history = await (await historyResponse).json();
  expect(history.data.find((row: { description: string }) => row.description === description).status).toBe("APPROVED");
  await expect(page.getByRole("row").filter({ hasText: description })).toBeVisible();
});

test("material upload and authenticated downloads work for admin and linked parent", async ({ page, browser }) => {
  await login(page, "admin");
  await page.goto("/materials");
  const title = `Kabul materyali ${Date.now()}`;
  await page.getByLabel("Materyal başlığı").fill(title);
  await page.getByLabel("Materyal görünürlüğü").selectOption("CLASS_ONLY");
  await page.getByLabel("Materyal sınıfı").selectOption({ label: "Kabul Sınıfı" });
  const content = Buffer.from("%PDF-1.4\nSCS360 acceptance material\n%%EOF");
  await page.getByLabel("Materyal dosyası").setInputFiles({ name: "kaynak.pdf", mimeType: "application/pdf", buffer: content });
  const uploadResponse = page.waitForResponse((response) => response.url().includes("/materials/upload"));
  await page.getByRole("button", { name: "Yükle", exact: true }).click();
  expect((await uploadResponse).status()).toBe(200);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: title + " indir", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("kaynak.pdf");
  expect(await readFile((await download.path())!)).toEqual(content);
  const parentContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const parent = await parentContext.newPage();
    await login(parent, "parent");
    await parent.goto("/parent/materials");
    const card = parent.locator(".parent-request-card").filter({ hasText: title });
    await expect(card).toBeVisible();
    const parentDownloadPromise = parent.waitForEvent("download");
    await card.getByRole("button", { name: "İndir", exact: true }).click();
    expect(await readFile((await (await parentDownloadPromise).path())!)).toEqual(content);
    expect(await parent.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally { await parentContext.close(); }
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: title + " kaldır", exact: true }).click();
  await expect(page.getByRole("button", { name: title + " indir", exact: true })).toHaveCount(0);
});

async function login(page: Page, role: string) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  const saved = sessions.get(role);
  if (saved) {
    await page.evaluate((entries) => { for (const { name, value } of entries) localStorage.setItem(name, value); }, saved);
    await page.goto(role === "parent" ? "/parent/academic" : role === "teacher" ? "/teacher" : "/platform");
    await expect(page).not.toHaveURL(/\/login$/);
    if (role === "admin") await enterAcceptanceSchool(page);
    return;
  }
  await page.getByRole("textbox", { name: "E-posta adresi" }).fill(`${role}@acceptance.example.com`);
  await page.getByLabel("Şifre", { exact: true }).fill("Acceptance-Only-2026!");
  await page.getByRole("checkbox", { name: "Beni hatırla" }).check();
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  const state = await page.context().storageState();
  sessions.set(role, state.origins.find((origin) => origin.origin === "http://127.0.0.1:5176")?.localStorage || []);
  if (role === "admin") await enterAcceptanceSchool(page);
}

async function enterAcceptanceSchool(page: Page) {
  const row = page.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ has: page.getByRole("cell", { name: "Kabul Test Okulu", exact: true }) });
  await row.getByRole("button", { name: "Kurum çalışma alanını aç", exact: true }).click(); await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("button", { name: "Sistem", exact: true })).toBeVisible();
}

test("SCS360 brand identity renders in login, sidebar and browser icon", async ({ page }) => {
  await page.goto("/login");
  await expect(page).toHaveTitle("SCS360 | Eğitim Yönetimi");
  const logo = page.getByRole("img", { name: "SCS360 logosu", exact: true });
  await expect(logo).toBeVisible();
  await expect.poll(() => logo.evaluate((element) => (element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await expect(page.locator(".brand-title")).toHaveText("SCS360");
  await expect(page.locator("body")).not.toContainText(/okul\s*360|edupanel/i);
  const favicon = await page.locator('link[rel="icon"][type="image/svg+xml"]').getAttribute("href");
  expect(favicon).toBe("/scs360-mark.svg?v=2");
  expect((await page.request.get(favicon!)).status()).toBe(200);
  await page.screenshot({ path: "../output/scs360-login-logo-20261103.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(logo).toBeVisible();
  await login(page, "admin");
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByRole("button", { name: "Menüyü aç", exact: true }).click();
  await expect.poll(() => page.locator("aside").evaluate((element) => Math.abs(element.getBoundingClientRect().x))).toBeLessThan(1);
  await expect(page.locator("aside .brand-title")).toHaveText("SCS360");
  await expect(page.locator("aside").getByRole("img", { name: "SCS360 logosu" })).toBeVisible();
  await page.screenshot({ path: "../output/scs360-sidebar-logo-mobile-20261103.png" });
});

test("chatbot quick question submits immediately with paginated staff student options", async ({ page }) => {
  await login(page, "admin");
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Chatbot'u aç" }).click();
  const chatbot = page.locator(".chatbot-container");
  const student = chatbot.getByRole("combobox", { name: "Öğrenci seçin", exact: true });
  await expect(student).toBeVisible();
  await expect(student.locator("option")).toHaveText(["Deniz Kabul"]);
  const suggestion = "🧠 LLM Chat Analitiği ve Konuşma Denetimi";
  const request = page.waitForRequest((item) => (item.url().includes("/v1/chatbot/process-query") || item.url().includes("/parent/chatbot")));
  const response = page.waitForResponse((item) => (item.url().includes("/v1/chatbot/process-query") || item.url().includes("/parent/chatbot")));
  await chatbot.getByRole("button", { name: suggestion, exact: true }).click();
  const payload = (await request).postDataJSON();
  expect(payload.query).toBe(suggestion);
  expect(payload.role).toBe("SUPER_ADMIN");
  expect(payload.student_id).toBeTruthy();
  const result = await response;
  expect(result.status()).toBe(200);
  const body = await result.json();
  expect((body.data || body).response_markdown.length).toBeGreaterThan(0);
});

test("admin visible pages load with real API responses", async ({ page }) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  await login(page, "admin");
  const sections = await page.locator(".nav-section").allTextContents();
  const links = new Set<string>();
  for (let index = 0; index < sections.length; index++) {
    await page.locator(".nav-section").nth(index).click();
    await expect(page.locator(".nav-section").nth(index)).toHaveAttribute("aria-expanded", "true");
    for (const href of await page.locator('nav a[href]').evaluateAll((items) => items.map((item) => item.getAttribute("href")!))) links.add(href);
  }
  expect(links.size).toBeGreaterThan(20);
  for (const href of links) {
    await page.goto(href);
    await expect(page.locator("main")).toBeVisible();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("body")).not.toContainText("Sayfa bulunamadı");
  }
  expect(failures).toEqual([]);
});

test("parent sees database grades and announcements on mobile width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "parent");
  await page.goto("/parent/academic");
  await expect(page.getByRole("cell", { name: "87 / 100", exact: true })).toBeVisible();
  await page.goto("/parent/announcements");
  await expect(page.getByText("Gerçek Kabul Duyurusu", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Bu sayfaya erişim yetkiniz yok");
  await page.getByRole("button", { name: "Chatbot'u aç" }).click();
  for (const message of ["Merhaba", "anlaşılmayan bir istek xyz", "notlarım"]) {
    await page.getByPlaceholder("Bir şey yazın...").fill(message);
    const response = page.waitForResponse((item) => (item.url().includes("/v1/chatbot/process-query") || item.url().includes("/parent/chatbot")));
    await page.getByRole("button", { name: "Mesaj gönder", exact: true }).click();
    const result = await response;
    expect(result.status()).toBe(200);
    const body = await result.json();
    expect((body.data || body).response_markdown?.length).toBeGreaterThan(0);
    if (message === "notlarım") expect((body.data || body).intent).toBe("GRADES");
    await expect(page.getByRole("button", { name: "Mesaj gönder", exact: true })).toBeDisabled();
  }
  await page.getByPlaceholder("Bir şey yazın...").fill("Detayları aç");
  await page.getByRole("button", { name: "Mesaj gönder", exact: true }).click();
  await expect(page).toHaveURL(/\/parent\/academic$/);
  await expect(page.getByRole("cell", { name: "87 / 100", exact: true })).toBeVisible();
});

test("homework create button persists and detail page opens", async ({ page }) => {
  const title = `Tarayıcı Kabul Ödevi ${Date.now()}`;
  await login(page, "teacher");
  await page.goto("/homework");
  await page.getByRole("button", { name: "Yeni ödev" }).click();
  await page.locator('input[name="title"]').fill(title);
  await page.locator('select[name="class_id"]').selectOption({ label: "Kabul Sınıfı" });
  await page.getByRole("button", { name: "Oluştur", exact: true }).click();
  await expect(page.getByText(title, { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText(title, { exact: true })).toBeVisible();
  const row = page.locator("tr").filter({ hasText: title });
  await row.locator('a[href^="/homework/"]').first().click();
  await expect(page).toHaveURL(/\/homework\/[a-f0-9-]+$/);
  await expect(page.getByText(title, { exact: true })).toBeVisible();
});

test("parent and teacher exchange persistent messages for the same child", async ({ page, browser }) => {
  const message = `Veli kabul mesajı ${Date.now()}`;
  const reply = `Öğretmen yanıtı ${Date.now()}`;
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "parent");
  await page.goto("/parent/chat");
  await page.getByRole("button", { name: "Mesaj Gönder", exact: true }).click();
  await page.getByPlaceholder("Mesajınızı yazın...").fill(message);
  await page.getByRole("button", { name: "Sohbet mesajını gönder" }).click();
  await expect(page.getByText(message, { exact: true })).toBeVisible();
  const teacherContext = await browser.newContext({ baseURL: "http://127.0.0.1:5176" });
  try {
    const teacher = await teacherContext.newPage();
    await login(teacher, "teacher");
    await teacher.goto("/teacher");
    await teacher.getByRole("button", { name: "Mesajlar", exact: true }).click();
    await teacher.getByText("Kabul Sınıfı", { exact: true }).click();
    await teacher.getByText("Deniz Kabul", { exact: true }).click();
    await expect(teacher.getByText(message, { exact: true })).toBeVisible();
    await teacher.getByPlaceholder("Mesajınızı yazın...").fill(reply);
    await teacher.getByRole("button", { name: "Sohbet mesajını gönder" }).click();
    await expect(teacher.getByText(reply, { exact: true })).toBeVisible();
    await expect(page.getByText(reply, { exact: true })).toBeVisible({ timeout: 15_000 });
    await page.screenshot({ path: "../output/chat-acceptance-mobile.png" });
  } finally {
    await teacherContext.close();
  }
});

test("parent uploads homework and teacher downloads and grades it", async ({ page, browser }) => {
  const title = `Dosyalı Ödev ${Date.now()}`;
  await login(page, "teacher");
  await page.goto("/homework");
  await page.getByRole("button", { name: "Yeni ödev" }).click();
  await page.locator('input[name="title"]').fill(title);
  await page.locator('select[name="class_id"]').selectOption({ label: "Kabul Sınıfı" });
  await page.getByRole("button", { name: "Oluştur", exact: true }).click();
  const row = page.locator("tr").filter({ hasText: title });
  await row.locator('a[href^="/homework/"]').first().click();
  const parentContext = await browser.newContext({ baseURL: "http://127.0.0.1:5176" });
  try {
    const parent = await parentContext.newPage();
    await login(parent, "parent");
    await parent.goto("/parent/homework");
    const card = parent.locator(".parent-request-card").filter({ hasText: title });
    await card.getByLabel("Teslim metni", { exact: true }).fill("Kalıcı dosyalı teslim");
    await card.getByLabel("Ödev dosyası", { exact: true }).setInputFiles({ name: "kabul.pdf", mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nBrowser acceptance\n%%EOF") });
    await card.getByRole("button", { name: "Ödevi teslim et" }).click();
    await expect(card.getByRole("status")).toHaveText("Ödev teslimi kaydedildi.");
    await parent.reload();
    await expect(card.locator("p").filter({ hasText: /^Kalıcı dosyalı teslim$/ })).toBeVisible();
    await page.reload();
    const [download] = await Promise.all([
      page.waitForEvent("download"), page.getByRole("button", { name: "Dosyayı indir: kabul.pdf", exact: true }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("kabul.pdf");
    expect(await download.failure()).toBeNull();
    await page.getByLabel("Puan", { exact: true }).fill("88");
    await page.getByLabel("Geri bildirim", { exact: true }).fill("Dosyanız değerlendirildi.");
    await page.getByRole("button", { name: "Notu kaydet" }).click();
    await expect(page.getByText("Puan: 88 / 100", { exact: true })).toBeVisible();
    await parent.reload();
    await expect(card.getByText("Puan: 88 / 100", { exact: true })).toBeVisible();
    await expect(card.getByRole("button", { name: "Ödevi teslim et" })).toHaveCount(0);
  } finally { await parentContext.close(); }
});

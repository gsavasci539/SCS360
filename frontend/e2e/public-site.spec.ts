import { expect, test, type Page } from "./fixtures";

async function authToken(page: Page) {
  return page.evaluate(() => JSON.parse(sessionStorage.getItem("scs360-session") || localStorage.getItem("scs360-session") || "{}").accessToken as string);
}

test("public pricing, pending signup, verified purchase and selected-school platform workspace work on mobile", async ({ page, browser }) => {
  const suffix = Date.now(), packageName = `Web Paketi ${suffix}`, schoolName = `Web Okulu ${suffix}`;
  await page.goto("/login"); await page.getByLabel("E-posta adresi", { exact: true }).fill("admin@acceptance.example.com");
  await page.getByLabel("Şifre", { exact: true }).fill("Acceptance-Only-2026!"); await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
  await expect(page).toHaveURL(/\/platform$/); await expect(page.getByRole("heading", { name: "Kurumlar ve Üyelikler", exact: true })).toBeVisible();
  expect(await page.getByRole("button", { name: "Öğrenci aramasına git", exact: true }).count()).toBe(0);
  expect(await page.getByRole("button", { name: "Chatbot'u aç", exact: true }).count()).toBe(0);
  const response = await page.request.post("/api/platform/plans", { headers: { Authorization: `Bearer ${await authToken(page)}` }, data: {
    code: `WEB${suffix}`, name: packageName, price: "345.67", currency: "TRY", branch_limit: 2, student_limit: 20, user_limit: 5, period_months: 1,
  } }); expect(response.status()).toBe(200); const plan = (await response.json()).data;
  const visitorContext = await browser.newContext({ viewport: { width: 390, height: 844 } }); const visitor = await visitorContext.newPage();
  try {
    const anonymousCalls: string[] = []; visitor.on("request", (request) => { if (request.url().includes("/api/")) anonymousCalls.push(new URL(request.url()).pathname); });
    await visitor.goto("/"); await expect(visitor.getByRole("heading", { name: /Eğitimde bütün resmi/ })).toBeVisible();
    const card = visitor.getByRole("article").filter({ has: visitor.getByRole("heading", { name: packageName, exact: true }) });
    await expect(card).toContainText("₺345,67"); await expect(card).toContainText("20 öğrenci");
    expect(anonymousCalls.every((path) => path === "/api/public/plans")).toBe(true);
    expect(await visitor.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await visitor.screenshot({ path: "../output/marketing-mobile-20261104.png", fullPage: true, animations: "disabled" });
    await card.getByRole("link", { name: "Paketi seç", exact: true }).click(); await expect(visitor).toHaveURL(/\/kayit\?paket=/);
    const form = visitor.getByRole("form", { name: "Kurum üyeliği oluştur", exact: true });
    await form.getByLabel("Kurum adı", { exact: true }).fill(schoolName); await form.getByLabel("Adınız", { exact: true }).fill("Web"); await form.getByLabel("Soyadınız", { exact: true }).fill("Sahibi");
    await form.getByLabel("E-posta adresiniz", { exact: true }).fill(`web-${suffix}@acceptance.example.com`); await form.getByLabel("Parola", { exact: true }).fill("AcceptancePass1!"); await form.getByLabel("Parola tekrarı", { exact: true }).fill("AcceptancePass1!");
    await form.getByRole("button", { name: "Hesabı oluştur ve ödeme adımına geç", exact: true }).click();
    await expect(visitor).toHaveURL(/\/subscription\?paket=/); await expect(visitor.getByRole("heading", { name: "Üyeliğinizi başlatın", exact: true })).toBeVisible();
    await expect(visitor.getByRole("combobox", { name: "Üyelik paketi", exact: true })).toHaveValue(plan.id);
    await visitor.getByRole("button", { name: "Ödeme talebi oluştur", exact: true }).click();
    await expect(visitor.getByRole("region", { name: "Üyelik ödeme geçmişi", exact: true })).toContainText("Bekliyor");
    await page.reload(); const invoice = page.getByRole("region", { name: "Kurum ödeme talepleri", exact: true }).getByRole("row").filter({ hasText: schoolName });
    await invoice.getByRole("button", { name: "Ödemeyi doğrula", exact: true }).click();
    const receipt = page.getByRole("form", { name: "Üyelik ödemesini doğrula", exact: true }); await receipt.getByLabel("Ödeme referansı", { exact: true }).fill(`WEB-ACCEPTANCE-ONLY-${suffix}`);
    await receipt.getByRole("button", { name: "Kontrol edilen ödemeyi kaydet", exact: true }).click(); await expect(invoice).toContainText("Ödendi");
    await visitor.getByRole("button", { name: "Üyelik durumunu yenile", exact: true }).click(); await expect(visitor.getByRole("heading", { name: "Üyelik etkin", exact: true })).toBeVisible();
    const school = page.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ hasText: schoolName });
    const summary = page.waitForResponse((value) => value.url().endsWith("/api/dashboard/summary"));
    await school.getByRole("button", { name: "Kurum çalışma alanını aç", exact: true }).click(); await expect(page).toHaveURL(/\/dashboard$/);
    const dashboard = await summary; expect(dashboard.status()).toBe(200); expect(dashboard.request().headers()["x-scs360-organization-id"]).toBeTruthy();
    await expect(page.getByLabel("Seçilen kurum çalışma alanı", { exact: true })).toContainText(schoolName);
    await page.goto("/students"); await expect(page.getByRole("heading", { name: "Öğrenciler", exact: true })).toBeVisible(); await expect(page.getByText("Deniz Kabul", { exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "Platform yönetimine dön", exact: true }).click(); await expect(page).toHaveURL(/\/platform$/);
    await expect(page.getByRole("button", { name: "SaaS Yönetimi", exact: true })).toBeVisible();
    expect(await page.getByRole("button", { name: "Öğrenci aramasına git", exact: true }).count()).toBe(0);
    await page.screenshot({ path: "../output/platform-control-20261104.png", fullPage: true, animations: "disabled" });
  } finally { await visitorContext.close(); }
});

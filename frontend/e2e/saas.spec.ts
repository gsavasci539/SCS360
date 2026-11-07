import { expect, test, type Page } from "./fixtures";

async function login(page: Page, email: string, password: string) {
  await page.goto("/login"); await page.getByLabel("E-posta adresi", { exact: true }).fill(email);
  await page.getByLabel("Şifre", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click(); await expect(page).not.toHaveURL(/\/login/);
}
async function token(page: Page) {
  return page.evaluate(() => JSON.parse(sessionStorage.getItem("scs360-session") || localStorage.getItem("scs360-session") || "{}").accessToken as string);
}

test("SaaS platform provisions an owner, expired sessions reach billing, verified renewal restores access on mobile", async ({ page, browser }) => {
  const suffix = Date.now(), school = `SaaS Kabul ${suffix}`, email = `owner-${suffix}@acceptance.example.com`;
  await login(page, "admin@acceptance.example.com", "Acceptance-Only-2026!");
  await page.goto("/platform"); const errors: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) errors.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  const plan = page.getByRole("form", { name: "Paket yönetimi", exact: true });
  await plan.getByLabel("Paket kodu", { exact: true }).fill(`SAAS${suffix}`); await plan.getByLabel("Paket adı", { exact: true }).fill(`Kabul Paketi ${suffix}`);
  await plan.getByLabel("Şube sınırı", { exact: true }).fill("1"); await plan.getByLabel("Öğrenci sınırı", { exact: true }).fill("5"); await plan.getByLabel("Kullanıcı sınırı", { exact: true }).fill("3");
  await plan.getByLabel("Paket fiyatı", { exact: true }).fill("250.50"); await plan.getByRole("button", { name: "Paketi kaydet", exact: true }).click();
  const provision = page.getByRole("form", { name: "Yeni kurum oluştur", exact: true });
  await provision.getByLabel("Kurum adı", { exact: true }).fill(school); await provision.getByLabel("Kurum sahibi adı", { exact: true }).fill("Kurum");
  await provision.getByLabel("Kurum sahibi soyadı", { exact: true }).fill("Sahibi"); await provision.getByLabel("Kurum sahibi e-postası", { exact: true }).fill(email);
  await provision.getByLabel("Başlangıç parolası", { exact: true }).fill("AcceptancePass1!");
  await provision.getByRole("combobox", { name: "Satın alınan paket", exact: true }).selectOption({ label: `Kabul Paketi ${suffix} · ₺250,50` });
  const created = page.waitForResponse((response) => response.url().endsWith("/api/platform/tenants") && response.request().method() === "POST");
  await provision.getByRole("button", { name: "Kurumu ve sahibi hesabını oluştur", exact: true }).click();
  const response = await created; expect(response.status()).toBe(200); const organization = (await response.json()).data.organization_id;
  const tenant = page.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ hasText: school }); await expect(tenant).toBeVisible();
  await tenant.getByRole("button", { name: "Üyeliği yönet", exact: true }).click();
  const membership = page.getByRole("form", { name: "Kurum üyeliğini düzenle", exact: true }); const planId = await membership.getByRole("combobox", { name: "Üyelik paketi", exact: true }).inputValue();
  const ownerContext = await browser.newContext({ viewport: { width: 390, height: 844 } }); const owner = await ownerContext.newPage();
  try {
    await login(owner, email, "AcceptancePass1!"); await owner.goto("/subscription");
    await expect(owner.getByRole("heading", { name: "Üyelik etkin", exact: true })).toBeVisible();
    await owner.goto("/users/new"); const account = owner.getByRole("form", { name: "Kullanıcı oluştur", exact: true });
    await account.getByLabel("Ad", { exact: true }).fill("Yeni"); await account.getByLabel("Soyad", { exact: true }).fill("Ekip");
    await account.getByLabel("E-posta", { exact: true }).fill(`staff-${suffix}@acceptance.example.com`);
    await account.getByLabel("Başlangıç parolası", { exact: true }).fill("AcceptancePass1!");
    await account.getByRole("button", { name: "Kullanıcıyı oluştur", exact: true }).click(); await expect(owner.getByRole("heading", { name: "Yeni Ekip", exact: true })).toBeVisible();
    await owner.getByLabel("Kurum Sahibi · Kurum rolü", { exact: true }).check(); await owner.getByRole("button", { name: "Erişimi kaydet", exact: true }).click();
    await expect(owner.getByRole("status")).toHaveText("Rol ve şube erişimi kaydedildi."); await owner.goto("/subscription");
    const now = Date.now(); const changed = await page.request.put(`/api/platform/tenants/${organization}/subscription`, {
      headers: { Authorization: `Bearer ${await token(page)}` }, data: { plan_id: planId, period_start: new Date(now - 40 * 86400000).toISOString(), period_end: new Date(now - 11 * 86400000).toISOString() },
    }); expect(changed.status()).toBe(200);
    await owner.goto("/users"); await expect(owner).toHaveURL(/\/subscription$/);
    await expect(owner.getByRole("heading", { name: "Üyelik ödemesi bekleniyor", exact: true })).toBeVisible();
    await owner.getByRole("combobox", { name: "Yenileme paketi", exact: true }).selectOption(planId);
    await owner.getByRole("button", { name: "Yenileme talebi oluştur", exact: true }).click();
    await expect(owner.getByRole("region", { name: "Üyelik ödeme geçmişi", exact: true }).getByText("Bekliyor", { exact: true })).toBeVisible();
    await page.reload(); const invoice = page.getByRole("region", { name: "Kurum ödeme talepleri", exact: true }).getByRole("row").filter({ hasText: school });
    await invoice.getByRole("button", { name: "Ödemeyi doğrula", exact: true }).click();
    const receipt = page.getByRole("form", { name: "Üyelik ödemesini doğrula", exact: true });
    await receipt.getByLabel("Ödeme referansı", { exact: true }).fill(`ACCEPTANCE-ONLY-${suffix}`);
    await receipt.getByRole("button", { name: "Kontrol edilen ödemeyi kaydet", exact: true }).click(); await expect(invoice.getByText("Ödendi", { exact: true })).toBeVisible();
    await owner.getByRole("button", { name: "Üyelik durumunu yenile", exact: true }).click(); await expect(owner.getByRole("heading", { name: "Üyelik etkin", exact: true })).toBeVisible();
    await expect(owner.getByRole("link", { name: "Çalışma alanına dön", exact: true })).toBeVisible();
    expect(await owner.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await owner.locator("form select, form button").evaluateAll((elements) => elements.every((element) => element.getBoundingClientRect().right <= window.innerWidth))).toBe(true);
    await owner.screenshot({ path: "../output/saas-subscription-mobile.png", fullPage: true, animations: "disabled" });
    await page.setViewportSize({ width: 390, height: 844 }); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await page.locator("form select, form button").evaluateAll((elements) => elements.every((element) => element.getBoundingClientRect().right <= window.innerWidth))).toBe(true);
    await page.screenshot({ path: "../output/saas-platform-mobile.png", fullPage: true, animations: "disabled" }); expect(errors).toEqual([]);
  } finally { await ownerContext.close(); }
});

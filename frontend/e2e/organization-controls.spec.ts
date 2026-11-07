import { expect, test, type Page } from "./fixtures";

async function login(page: Page, email: string, password: string) {
  await page.goto("/login"); await page.getByLabel("E-posta adresi", { exact: true }).fill(email);
  await page.getByLabel("Şifre", { exact: true }).fill(password); await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
}

test("owner edits and clears institution details while only the platform closes and reopens its account", async ({ page, browser, request }) => {
  const response = await request.post("/api/auth/login", { data: { email: "admin@acceptance.example.com", password: "Acceptance-Only-2026!" } }); expect(response.status()).toBe(200);
  const auth = { Authorization: `Bearer ${(await response.json()).data.access_token}` };
  const suffix = Date.now(), name = `Kurum Yetki ${suffix}`, email = `organization-owner-${suffix}@acceptance.example.com`;
  const plan = await request.post("/api/platform/plans", { headers: auth, data: { code: `ORG${suffix}`, name: `Kurum Paketi ${suffix}`, price: "100.00", branch_limit: 2, student_limit: 20, user_limit: 5 } }); expect(plan.status()).toBe(200);
  const created = await request.post("/api/platform/tenants", { headers: auth, data: { request_id: crypto.randomUUID(), name, plan_id: (await plan.json()).data.id,
    owner_email: email, owner_first_name: "Kurum", owner_last_name: "Sahibi", owner_password: "AcceptancePass1!" } }); expect(created.status()).toBe(200);
  await login(page, "admin@acceptance.example.com", "Acceptance-Only-2026!"); await expect(page).toHaveURL(/\/platform$/);
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } }); const owner = await context.newPage();
  try {
    await login(owner, email, "AcceptancePass1!"); await expect(owner).toHaveURL(/\/dashboard$/);
    const failures: string[] = []; let closing = false;
    owner.on("response", (reply) => { if (reply.url().includes("/api/") && reply.status() >= 400 && !(closing && reply.status() === 402)) failures.push(`${reply.status()} ${new URL(reply.url()).pathname}`); });
    await owner.goto("/branches"); await owner.getByRole("link", { name: "Şube ekle", exact: true }).click();
    await owner.getByLabel(/^Şube adı\s*\*?$/).fill("Yeni Şube");
    await owner.getByLabel(/^Kapasite\s*\*?$/).fill("20");
    await owner.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(owner).toHaveURL(/\/branches$/);
    await expect(owner.getByText("0 / 20", { exact: true })).toBeVisible();
    await owner.getByRole("link", { name: "Detayı aç", exact: true }).click(); await expect(owner.getByRole("heading", { name: "Yeni Şube", exact: true })).toBeVisible();
    await owner.getByRole("link", { name: "Düzenle", exact: true }).click();
    await owner.getByLabel("Telefon", { exact: true }).fill("05321112233");
    await owner.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(owner).toHaveURL(/\/branches$/);
    await expect(owner.getByText("05321112233", { exact: true })).toBeVisible();
    await owner.getByRole("link", { name: "Düzenle", exact: true }).click();
    await owner.getByRole("checkbox", { name: "Şube aktif", exact: true }).uncheck();
    await owner.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(owner).toHaveURL(/\/branches$/);
    await expect(owner.getByText("Pasif", { exact: true })).toBeVisible();
    await owner.getByRole("link", { name: "Düzenle", exact: true }).click();
    await expect(owner.getByRole("checkbox", { name: "Şube aktif", exact: true })).not.toBeChecked();
    await owner.getByRole("checkbox", { name: "Şube aktif", exact: true }).check();
    await owner.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(owner).toHaveURL(/\/branches$/);
    await owner.goto("/organizations"); await expect(owner.getByRole("link", { name: "Düzenle", exact: true })).toBeVisible();
    await expect(owner.getByRole("link", { name: "Kurum ekle", exact: true })).toHaveCount(0);
    await expect(owner.getByRole("button", { name: "Kaldır", exact: true })).toHaveCount(0);
    await owner.getByRole("link", { name: "Düzenle", exact: true }).click();
    await owner.getByLabel("Telefon", { exact: true }).fill("05320000000"); await owner.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(owner).toHaveURL(/\/organizations$/);
    await owner.getByRole("link", { name: "Düzenle", exact: true }).click(); await expect(owner.getByLabel("Telefon", { exact: true })).toHaveValue("05320000000");
    await owner.getByLabel("Telefon", { exact: true }).fill(""); await owner.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(owner).toHaveURL(/\/organizations$/);
    await owner.getByRole("link", { name: "Düzenle", exact: true }).click(); await expect(owner.getByLabel("Telefon", { exact: true })).toHaveValue("");
    const tenant = page.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ hasText: name });
    await tenant.getByRole("button", { name: "Kurum hesabını kapat", exact: true }).click(); await expect(tenant.getByRole("button", { name: "Kurum hesabını aç", exact: true })).toBeVisible();
    closing = true; await owner.goto("/organizations"); await expect(owner).toHaveURL(/\/subscription$/);
    await expect(owner.getByText("Kurum hesabı kapatılmış. Platform yöneticisiyle iletişime geçin.", { exact: true }).first()).toBeVisible();
    await tenant.getByRole("button", { name: "Kurum hesabını aç", exact: true }).click(); await expect(tenant.getByRole("button", { name: "Kurum hesabını kapat", exact: true })).toBeVisible();
    await owner.getByRole("button", { name: "Üyelik durumunu yenile", exact: true }).click(); await expect(owner.getByRole("heading", { name: "Üyelik etkin", exact: true })).toBeVisible();
    closing = false; await owner.goto("/organizations"); await expect(owner.getByRole("link", { name: "Düzenle", exact: true })).toBeVisible();
    expect(failures).toEqual([]); expect(await owner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  } finally { await context.close(); }
});

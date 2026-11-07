import { expect, test, type Page } from "./fixtures";

async function token(page: Page) { return page.evaluate(() => JSON.parse(sessionStorage.getItem("scs360-session") || localStorage.getItem("scs360-session") || "{}").accessToken); }

test("new school owner can create a parent login and link the contact without changing other schools", async ({ page, browser, request }) => {
  const suffix = Date.now(), email = `parent-account-${suffix}@acceptance.example.com`, password = "AcceptancePass1!";
  const rootLogin = await request.post("/api/auth/login", { data: { email: "admin@acceptance.example.com", password: "Acceptance-Only-2026!" } });
  expect(rootLogin.status()).toBe(200); const root = { Authorization: `Bearer ${(await rootLogin.json()).data.access_token}` };
  const plan = await request.post("/api/platform/plans", { headers: root, data: { code: `PARENT${suffix}`, name: `Hesap Paketi ${suffix}`, price: "100.00", branch_limit: 2, student_limit: 20, user_limit: 4 } });
  expect(plan.status()).toBe(200);
  const ownerEmail = `parent-owner-${suffix}@acceptance.example.com`;
  const school = await request.post("/api/platform/tenants", { headers: root, data: { request_id: crypto.randomUUID(), name: `Hesap Okulu ${suffix}`, plan_id: (await plan.json()).data.id, owner_email: ownerEmail, owner_first_name: "Hesap", owner_last_name: "Sahibi", owner_password: password } }); expect(school.status()).toBe(200);
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/login");
  await page.getByLabel("E-posta adresi", { exact: true }).fill(ownerEmail); await page.getByLabel("Şifre", { exact: true }).fill(password); await page.getByRole("button", { name: "Giriş yap", exact: true }).click(); await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto("/users/new"); const create = page.getByRole("form", { name: "Kullanıcı oluştur", exact: true });
  await create.getByLabel("Ad", { exact: true }).fill("Yeni"); await create.getByLabel("Soyad", { exact: true }).fill("Veli"); await create.getByLabel("E-posta", { exact: true }).fill(email); await create.getByLabel("Başlangıç parolası", { exact: true }).fill(password);
  await create.getByRole("button", { name: "Kullanıcıyı oluştur", exact: true }).click(); await expect(page).toHaveURL(/\/users\/[0-9a-f-]+$/);
  await page.getByRole("checkbox", { name: "Veli · Kurum rolü", exact: true }).check(); await page.getByRole("button", { name: "Erişimi kaydet", exact: true }).click(); await expect(page.getByRole("status")).toContainText("Rol ve şube erişimi kaydedildi");
  const auth = { Authorization: `Bearer ${await token(page)}` };
  const contact = await request.post("/api/parents", { headers: auth, data: { organization_id: (await school.json()).data.organization_id, first_name: "Yeni", last_name: "Veli", phone: "05000000000", receive_notifications: false } });
  expect(contact.status()).toBe(200); const id = (await contact.json()).data.id;
  await page.goto(`/parents/${id}`); const link = page.getByRole("region", { name: "Veli giriş hesabı", exact: true });
  await link.getByRole("combobox", { name: "Bağlanacak giriş hesabı", exact: true }).selectOption({ label: `Yeni Veli · ${email}` });
  await link.getByRole("button", { name: "Giriş hesabı bağlantısını kaydet", exact: true }).click(); await expect(link.getByRole("status")).toContainText("bağlantısı kaydedildi");
  await page.goto(`/parents/${id}/edit`); await expect(page.getByLabel("Telefon", { exact: true })).toHaveValue("05000000000");
  await expect(page.getByLabel("Bildirim almayı kabul ediyor", { exact: true })).not.toBeChecked();
  await page.getByLabel("Telefon", { exact: true }).fill(""); await page.getByLabel("SMS telefonu", { exact: true }).fill("05000000001"); await page.getByLabel("Bildirim almayı kabul ediyor", { exact: true }).check();
  await page.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(page).toHaveURL(/\/parents$/);
  const saved = await request.get(`/api/parents/${id}`, { headers: auth }); expect(saved.status()).toBe(200); const body = (await saved.json()).data;
  expect(body.phone).toBeNull(); expect(body.sms_phone).toBe("05000000001"); expect(body.receive_notifications).toBe(true); expect(body.user_id).toBeTruthy();
  const parentContext = await browser.newContext(); const parent = await parentContext.newPage();
  try {
    await parent.goto("/login"); await parent.getByLabel("E-posta adresi", { exact: true }).fill(email); await parent.getByLabel("Şifre", { exact: true }).fill(password); await parent.getByRole("button", { name: "Giriş yap", exact: true }).click(); await expect(parent).toHaveURL(/\/parent\/dashboard$/);
    const children = await parent.request.get("/api/parent/my-children", { headers: { Authorization: `Bearer ${await token(parent)}` } }); expect(children.status()).toBe(200); expect((await children.json()).data).toEqual([]);
    await expect(parent.getByText("Deniz Kabul", { exact: true })).toHaveCount(0);
  } finally { await parentContext.close(); }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

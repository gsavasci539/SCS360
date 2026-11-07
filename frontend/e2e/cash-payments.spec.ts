import { expect, test, type Page } from "./fixtures";

async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("E-posta adresi", { exact: true }).fill(email);
  await page.getByLabel("Şifre", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
}

test("collector retries a committed cash payment once and the selected cancellation preserves the other payment", async ({ page, browser, request, baseURL }) => {
  const suffix = Date.now(), schoolName = `Tahsilat Okulu ${suffix}`, password = "AcceptancePass1!";
  const signed = await request.post("/api/auth/login", { data: { email: "admin@acceptance.example.com", password: "Acceptance-Only-2026!" } });
  expect(signed.status()).toBe(200);
  const root = { Authorization: `Bearer ${(await signed.json()).data.access_token}` };
  async function post(path: string, data: Record<string, unknown>, headers = root) {
    const result = await request.post(path, { data, headers });
    expect(result.status(), await result.text()).toBe(200); return (await result.json()).data;
  }
  async function get(path: string, headers: Record<string, string>) {
    const result = await request.get(path, { headers });
    expect(result.status(), await result.text()).toBe(200); return (await result.json()).data;
  }
  const plan = await post("/api/platform/plans", { code: `CASH${suffix}`, name: `Tahsilat Paketi ${suffix}`, price: "100.00", branch_limit: 2, student_limit: 5, user_limit: 5 });
  const school = await post("/api/platform/tenants", { request_id: crypto.randomUUID(), name: schoolName, plan_id: plan.id,
    owner_email: `cash-owner-${suffix}@acceptance.example.com`, owner_first_name: "Okul", owner_last_name: "Sahibi", owner_password: password });
  const auth = { ...root, "X-SCS360-Organization-Id": school.organization_id };
  const branch = await post("/api/branches", { organization_id: school.organization_id, name: "Tahsilat Şubesi" }, auth);
  const student = await post("/api/students", { organization_id: school.organization_id, branch_id: branch.id, first_name: "Deniz", last_name: "Tahsilat" }, auth);
  const options = await get("/api/users/options", auth);
  const role = options.roles.find((row: { slug: string; organization_id: string }) => row.slug === "accountant" && row.organization_id === school.organization_id);
  expect(role).toBeTruthy();
  const permissions = await get("/api/permissions", auth);
  const collect = permissions.find((row: { code: string }) => row.code === "finance.collect_payment");
  expect(collect).toBeTruthy();
  const assigned = await request.put(`/api/roles/${role.id}/permissions`, { headers: auth, data: { permission_ids: [collect.id] } });
  expect(assigned.status(), await assigned.text()).toBe(200);
  const email = `cash-collector-${suffix}@acceptance.example.com`;
  const cashier = await post("/api/users", { email, password, first_name: "Yetkili", last_name: "Tahsildar" }, auth);
  expect((await request.put(`/api/users/${cashier.id}/access`, { headers: auth, data: { role_ids: [role.id], branch_ids: [branch.id] } })).status()).toBe(200);
  let lastDebt = "";
  for (let index = 0; index < 105; index++) {
    const date = new Date(); date.setUTCDate(date.getUTCDate() + index);
    const debt = await post("/api/debts", { student_id: student.id, debt_type: "EDUCATION", amount: "10.00", due_date: date.toISOString().slice(0, 10), description: `Invoice${String(index).padStart(3, "0")}` }, auth);
    lastDebt = debt.id;
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, email, password); await expect(page).toHaveURL(/\/finance\/payments\/new$/);
  const failures: string[] = [], nonces: string[] = [];
  page.on("response", (reply) => { if (reply.url().includes("/api/") && reply.status() >= 400) failures.push(`${reply.status()} ${new URL(reply.url()).pathname}`); });
  await page.getByRole("searchbox", { name: "Borç kaydı ara", exact: true }).fill("Invoice104");
  const debts = page.getByRole("combobox", { name: /^Borç kaydı/ });
  await expect(debts.getByRole("option", { name: /Invoice104/ })).toHaveCount(1);
  await debts.selectOption(lastDebt);
  await page.getByLabel("Ödeme tutarı").fill("6.25"); await page.getByLabel("Ödeme yöntemi").selectOption("CASH");
  let dropped = false;
  await page.route("**/api/payments", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    nonces.push(route.request().postDataJSON().request_id);
    if (!dropped) { dropped = true; const response = await route.fetch(); expect(response.status()).toBe(200); await route.abort("timedout"); }
    else await route.continue();
  });
  await page.getByRole("button", { name: "Tahsilatı tamamla", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Sunucu yanıt vermedi");
  await page.reload();
  await expect(page.getByLabel("Ödeme tutarı")).toHaveValue("6.25");
  await expect(page.getByLabel("Ödeme yöntemi")).toHaveValue("CASH");
  await expect(page.getByRole("combobox", { name: /^Borç kaydı/ })).toHaveValue(lastDebt);
  await page.getByRole("button", { name: "Tahsilatı tamamla", exact: true }).click();
  await expect(page.getByRole("region", { name: "Tahsilat sonucu", exact: true })).toContainText("RCP-");
  await expect(page).toHaveURL(/\/finance\/payments\/new$/);
  expect(nonces).toHaveLength(2); expect(nonces[0]).toBeTruthy(); expect(nonces[1]).toBe(nonces[0]);
  const payments = await get("/api/payments?status=ALL", auth);
  expect(payments.items).toHaveLength(1); expect(Number(payments.items[0].amount)).toBe(6.25);
  const original = payments.items[0].id;
  expect(Number((await get(`/api/debts/${lastDebt}`, auth)).paid_amount)).toBe(6.25);
  await expect(page.getByRole("region", { name: "Tahsilat sonucu", exact: true })).toContainText("1.043,75");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const second = await post("/api/payments", { debt_id: lastDebt, amount: "2.00", payment_method: "CASH", request_id: crypto.randomUUID() }, auth);
  const context = await browser.newContext({ baseURL, viewport: { width: 390, height: 844 } });
  try {
    const owner = await context.newPage();
    await login(owner, "admin@acceptance.example.com", "Acceptance-Only-2026!"); await expect(owner).toHaveURL(/\/platform$/);
    await owner.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ hasText: schoolName }).getByRole("button", { name: "Kurum çalışma alanını aç", exact: true }).click();
    await expect(owner).toHaveURL(/\/dashboard$/);
    await expect(owner.getByLabel("Seçilen kurum çalışma alanı")).toContainText(schoolName);
    owner.on("response", (reply) => { if (reply.url().includes("/api/") && reply.status() >= 400) failures.push(`${reply.status()} ${new URL(reply.url()).pathname}`); });
    await owner.goto("/finance/payments");
    const selected = owner.getByRole("row").filter({ has: owner.locator(`a[href="/finance/payments/${second.payment_id}"]`) });
    await selected.getByRole("button", { name: "İptal et", exact: true }).click();
    const dialog = owner.getByRole("dialog", { name: "Tahsilat iptali", exact: true });
    await expect(dialog).toContainText("Deniz Tahsilat"); await expect(dialog).toContainText("₺2");
    await dialog.getByLabel("İptal nedeni").fill("Yalnız seçilen ikinci kayıt kabul kontrolü");
    await dialog.getByRole("button", { name: "İptal et", exact: true }).click(); await expect(dialog).toHaveCount(0);
    await expect(selected.getByText("İptal", { exact: true })).toBeVisible();
    const final = await get("/api/payments?status=ALL", auth);
    expect(final.items.find((row: { id: string }) => row.id === original).cancelled).toBe(false);
    expect(final.items.find((row: { id: string }) => row.id === second.payment_id).cancelled).toBe(true);
    expect(Number((await get(`/api/debts/${lastDebt}`, auth)).paid_amount)).toBe(6.25);
    expect(await owner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await owner.locator(".table-wrap").evaluate((element) => { element.scrollLeft = 0; });
    await owner.evaluate(() => window.scrollTo(0, 0));
    await owner.screenshot({ path: "../output/cash-payments-mobile-20261104.png", fullPage: true });
    await owner.goto("/ai-analytics");
    await owner.getByRole("button", { name: "Finansal özet", exact: true }).click();
    await expect(owner.getByRole("heading", { name: "Kayıtlı finans analizi", exact: true })).toBeVisible();
    const history = owner.getByRole("region", { name: "Tahsilat geçmişi", exact: true });
    await expect(history.getByRole("cell", { name: "₺6,25", exact: true })).toBeVisible();
    const changed = owner.waitForResponse((reply) => reply.url().includes("/ai/ai-financial-predictions") && new URL(reply.url()).searchParams.get("months") === "1");
    await owner.getByRole("combobox", { name: "Finans vade dönemi", exact: true }).selectOption("1");
    const financialReply = await changed; expect(financialReply.status()).toBe(200);
    const actual = (await financialReply.json()).data;
    expect(actual.collected_total).toBe("6.25"); expect(actual.forecast_available).toBe(false);
    expect(actual.monthly_forecast).toHaveLength(1); expect(actual.monthly_forecast[0].predicted_amount).toBeNull();
    await expect(owner.getByRole("region", { name: "Kayıtlı vade takvimi", exact: true }).getByRole("row")).toHaveCount(2);
    expect(await owner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await owner.screenshot({ path: "../output/recorded-finance-mobile-20261104.png", fullPage: true });
    expect(failures).toEqual([]);
  } finally { await context.close(); }
});

import { expect, test, type Page } from "./fixtures";

async function login(page: Page, role: string) {
  await page.goto("/login"); await page.getByLabel("E-posta adresi", { exact: true }).fill(`${role}@acceptance.example.com`);
  await page.getByLabel("Şifre", { exact: true }).fill("Acceptance-Only-2026!");
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
}

test("school class form saves teacher and active flag and clears only the primary assignment on mobile", async ({ page, browser }) => {
  await login(page, "admin"); await expect(page).toHaveURL(/\/platform$/);
  await page.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ hasText: "Kabul Test Okulu" }).getByRole("button", { name: "Kurum çalışma alanını aç", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sistem", exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/classes/new");
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.getByRole("combobox", { name: "Şube *", exact: true }).selectOption({ label: "Test Şubesi" });
  const name = `Öğretmen Atama ${Date.now()}`;
  await page.getByLabel("Sınıf adı *", { exact: true }).fill(name); await page.getByLabel("Sınıf kodu *", { exact: true }).fill("CLASS-CHECK");
  await page.getByLabel("Kontenjan *", { exact: true }).fill("20");
  await page.getByRole("searchbox", { name: "Öğretmen ara", exact: true }).fill("Teacher");
  await expect(page.getByRole("combobox", { name: "Öğretmen", exact: true })).toBeEnabled();
  await page.getByRole("combobox", { name: "Öğretmen", exact: true }).selectOption({ label: "Teacher Kabul" });
  await page.getByRole("checkbox", { name: "Sınıf aktif", exact: true }).uncheck();
  const created = page.waitForResponse((response) => response.url().endsWith("/api/classes") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Kaydet", exact: true }).click();
  const response = await created; expect(response.status()).toBe(200); const record = (await response.json()).data;
  expect(record.is_active).toBe(false); expect(record.teacher_name).toBe("Teacher Kabul"); expect(record.teacher_id).toBeTruthy();
  await expect(page).toHaveURL(/\/classes$/); await expect(page.getByRole("row").filter({ hasText: name })).toContainText("Teacher Kabul");
  await page.goto(`/classes/${record.id}/edit`); await expect(page.getByRole("combobox", { name: "Öğretmen", exact: true })).toHaveValue(record.teacher_id);
  await expect(page.getByRole("checkbox", { name: "Sınıf aktif", exact: true })).not.toBeChecked();
  await page.getByRole("checkbox", { name: "Sınıf aktif", exact: true }).check(); await page.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(page).toHaveURL(/\/classes$/);
  const context = await browser.newContext(); const teacher = await context.newPage();
  try {
    await login(teacher, "teacher"); await expect(teacher).toHaveURL(/\/teacher$/);
    await expect(teacher.getByText(name, { exact: true })).toBeVisible();
  } finally { await context.close(); }
  await page.goto(`/classes/${record.id}/edit`); await expect(page.getByRole("combobox", { name: "Öğretmen", exact: true })).toBeEnabled();
  await page.getByRole("combobox", { name: "Öğretmen", exact: true }).selectOption("");
  await page.getByRole("button", { name: "Kaydet", exact: true }).click(); await expect(page).toHaveURL(/\/classes$/);
  await page.goto(`/classes/${record.id}/edit`); await expect(page.getByRole("combobox", { name: "Öğretmen", exact: true })).toHaveValue("");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/class-registration-mobile-20261104.png", fullPage: true }); expect(failures).toEqual([]);
});

test("finance writer creates a debt through minimal student choices without organization branch or student directory access", async ({ page }) => {
  await login(page, "accountant"); await expect(page).toHaveURL(/\/finance\/debts$/);
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/finance/debts/new");
  await expect(page.getByRole("combobox", { name: "Kurum *", exact: true })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Şube *", exact: true })).toHaveCount(0);
  await page.getByRole("searchbox", { name: "Öğrenci ara", exact: true }).fill("KABUL-001");
  await expect(page.getByRole("combobox", { name: "Öğrenci *", exact: true })).toBeEnabled();
  await page.getByRole("combobox", { name: "Öğrenci *", exact: true }).selectOption({ label: "Deniz Kabul · KABUL-001" });
  await page.getByRole("combobox", { name: "Borç türü *", exact: true }).selectOption("EDUCATION");
  await page.getByLabel("Tutar *", { exact: true }).fill("125.50"); await page.getByLabel("Vade tarihi *", { exact: true }).fill("2026-12-01");
  const created = page.waitForResponse((response) => response.url().endsWith("/api/debts") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Kaydet", exact: true }).click(); const response = await created; expect(response.status()).toBe(200);
  const record = (await response.json()).data;
  await expect(page).toHaveURL(/\/finance\/debts$/); await page.goto(`/finance/debts/${record.id}/edit`);
  await expect(page.getByRole("combobox", { name: "Öğrenci *", exact: true })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Borç türü *", exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Tutar *", { exact: true })).toHaveValue("125.50");
  await page.getByLabel("Tutar *", { exact: true }).fill("130.75");
  const updated = page.waitForResponse((reply) => reply.url().endsWith(`/api/debts/${record.id}`) && reply.request().method() === "PUT");
  await page.getByRole("button", { name: "Kaydet", exact: true }).click(); expect((await updated).status()).toBe(200);
  await expect(page).toHaveURL(/\/finance\/debts$/); await page.goto(`/finance/debts/${record.id}/edit`);
  await expect(page.getByLabel("Tutar *", { exact: true })).toHaveValue("130.75"); expect(failures).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

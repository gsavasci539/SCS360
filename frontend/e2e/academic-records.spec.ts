import { expect, test, type Page } from "./fixtures";

async function login(page: Page, email: string, password: string) {
  await page.goto("/login"); await page.getByLabel("E-posta adresi", { exact: true }).fill(email);
  await page.getByLabel("Şifre", { exact: true }).fill(password); await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
}

test("real exam grades reach parent and chatbot while academic periods include zero without invented predictions", async ({ page, browser, request }) => {
  const suffix = Date.now(), name = `Akademik Okul ${suffix}`, password = "AcceptancePass1!";
  const signed = await request.post("/api/auth/login", { data: { email: "admin@acceptance.example.com", password: "Acceptance-Only-2026!" } }); expect(signed.status()).toBe(200);
  const root = { Authorization: `Bearer ${(await signed.json()).data.access_token}` };
  async function post(path: string, data: Record<string, unknown>, headers = root) {
    const result = await request.post(path, { data, headers }); expect(result.status(), await result.text()).toBe(200); return (await result.json()).data;
  }
  const plan = await post("/api/platform/plans", { code: `GRADE${suffix}`, name: `Not Paketi ${suffix}`, price: "100.00", branch_limit: 2, student_limit: 10, user_limit: 4 });
  const school = await post("/api/platform/tenants", { request_id: crypto.randomUUID(), name, plan_id: plan.id,
    owner_email: `grade-owner-${suffix}@acceptance.example.com`, owner_first_name: "Okul", owner_last_name: "Sahibi", owner_password: password });
  const auth = { ...root, "X-SCS360-Organization-Id": school.organization_id };
  const branch = await post("/api/branches", { organization_id: school.organization_id, name: "Not Şubesi" }, auth);
  const classroom = await post("/api/classes", { organization_id: school.organization_id, branch_id: branch.id, name: "Not Sınıfı", capacity: 20 }, auth);
  const child = await post("/api/students", { organization_id: school.organization_id, branch_id: branch.id, class_id: classroom.id, first_name: "Akademik", last_name: "Öğrenci" }, auth);
  const email = `grade-parent-${suffix}@acceptance.example.com`;
  const account = await post("/api/users", { first_name: "Akademik", last_name: "Veli", email, password }, auth);
  const profile = await request.get("/api/users/options", { headers: auth }); expect(profile.status()).toBe(200);
  const parentRole = (await profile.json()).data.roles.find((row: { slug: string; organization_id: string }) => row.slug === "parent" && row.organization_id === school.organization_id);
  expect(parentRole).toBeTruthy(); expect((await request.put(`/api/users/${account.id}/access`, { headers: auth, data: { role_ids: [parentRole.id], branch_ids: [] } })).status()).toBe(200);
  const contact = await post("/api/parents", { organization_id: school.organization_id, first_name: "Akademik", last_name: "Veli", receive_notifications: false }, auth);
  expect((await request.put(`/api/parents/${contact.id}/account`, { headers: auth, data: { user_id: account.id } })).status()).toBe(200);
  await post(`/api/students/${child.id}/parents`, { parent_id: contact.id }, auth);
  const today = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Istanbul" }).format(new Date());
  for (const [title, score, ago] of [["Sıfır not sınavı", 0, 1], ["Güncel sınav", 40, 0], ["Eski sınav", 80, 60]] as const) {
    const date = new Date(`${today}T12:00:00Z`); date.setUTCDate(date.getUTCDate() - ago);
    const exam = await post("/api/exams", { class_id: classroom.id, title, exam_type: "QUIZ", exam_date: date.toISOString().slice(0, 10), max_score: 80 }, auth);
    await post("/api/exams/bulk-grade-entry", { exam_id: exam.id, grades: [{ student_id: child.id, score }] }, auth);
  }
  await login(page, "admin@acceptance.example.com", "Acceptance-Only-2026!"); await expect(page).toHaveURL(/\/platform$/);
  await page.getByRole("region", { name: "Kurum üyelikleri", exact: true }).getByRole("row").filter({ hasText: name }).getByRole("button", { name: "Kurum çalışma alanını aç", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 }); const queries: string[] = [], failures: string[] = [];
  page.on("response", (reply) => { if (reply.url().includes("/api/ai/")) queries.push(new URL(reply.url()).pathname); if (reply.url().includes("/api/") && reply.status() >= 400) failures.push(`${reply.status()} ${new URL(reply.url()).pathname}`); });
  await page.goto("/ai-analytics"); await page.getByRole("button", { name: "Akademik özet", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Kayıtlı not analizi", exact: true })).toBeVisible();
  await expect(page.getByText("25", { exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Analiz dönemi", exact: true }).selectOption("90"); await expect(page.getByText("50", { exact: true })).toBeVisible();
  expect(queries.some((path) => /ai-(attendance|financial|parent|operational)/.test(path))).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/academic-summary-mobile-20261104.png", fullPage: true });
  await page.goto("/exams"); await expect(page.getByRole("cell", { name: "Sıfır not sınavı", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Yeni sınav", exact: true }).click();
  const editor = page.getByRole("dialog", { name: "Yeni sınav", exact: true });
  await editor.getByLabel("Sınav adı").fill("Panel yönetim sınavı");
  await editor.getByRole("combobox", { name: /^Sınıf/ }).selectOption(classroom.id);
  await editor.getByLabel("Sınav tarihi").fill(today); await editor.getByLabel("Başlangıç saati").fill("10:15");
  await editor.getByLabel("Tam puan").fill("80"); await editor.getByRole("button", { name: "Sınavı kaydet", exact: true }).click();
  const managedRow = page.getByRole("row").filter({ has: page.getByRole("cell", { name: "Panel yönetim sınavı", exact: true }) });
  await managedRow.getByRole("button", { name: "Notlar ve karne", exact: true }).click();
  await page.getByRole("spinbutton", { name: "Akademik Öğrenci notu", exact: true }).fill("20");
  await page.getByRole("button", { name: "Notları kaydet", exact: true }).click();
  await expect(page.getByText("Notlar kaydedildi.", { exact: true })).toBeVisible();
  await page.reload(); await managedRow.getByRole("button", { name: "Sınavı düzenle", exact: true }).click();
  const savedEditor = page.getByRole("dialog", { name: "Sınavı düzenle", exact: true });
  await expect(savedEditor.getByLabel("Tam puan")).toHaveValue("80"); await expect(savedEditor.getByLabel("Tam puan")).toHaveAttribute("readonly", "");
  await expect(savedEditor.getByLabel("Başlangıç saati")).toHaveValue("10:15"); await savedEditor.getByRole("button", { name: "Pencereyi kapat", exact: true }).click();
  await managedRow.getByRole("button", { name: "Notlar ve karne", exact: true }).click();
  await expect(page.getByRole("spinbutton", { name: "Akademik Öğrenci notu", exact: true })).toHaveValue("20");
  await page.getByRole("button", { name: "Karneler", exact: true }).click();
  const cards = page.getByRole("dialog", { name: "Akademik Öğrenci · Karneler", exact: true });
  await cards.getByLabel("Öğretmen yorumu", { exact: true }).fill("Panelden doğrulanmış dönem karnesi");
  await cards.getByRole("button", { name: "Karne taslağı oluştur", exact: true }).click();
  await expect(cards.getByText("1.75 / 4", { exact: true })).toBeVisible();
  await cards.getByRole("button", { name: "Veliye yayımla", exact: true }).click();
  await expect(cards.getByText("Karne veliye yayımlandı.", { exact: true })).toBeVisible();
  await cards.getByRole("button", { name: "Pencereyi kapat", exact: true }).click();
  await post("/api/exams", { class_id: classroom.id, title: "İptal kontrol sınavı", exam_type: "QUIZ", exam_date: today, max_score: 80 }, auth);
  await page.reload();
  const cancelledRow = page.getByRole("row").filter({ has: page.getByRole("cell", { name: "İptal kontrol sınavı", exact: true }) });
  await cancelledRow.getByRole("button", { name: "Sınavı iptal et", exact: true }).click();
  await page.getByRole("button", { name: "İptali onayla", exact: true }).click();
  await expect(cancelledRow.getByText("İptal", { exact: true })).toBeVisible();
  await managedRow.getByRole("button", { name: "Notlar ve karne", exact: true }).click();
  await expect(page.getByRole("spinbutton", { name: "Akademik Öğrenci notu", exact: true })).toHaveValue("20");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "../output/exam-management-mobile-20261104.png", fullPage: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } }); const parent = await context.newPage();
  try {
    await login(parent, email, password); await expect(parent).toHaveURL(/\/parent\/dashboard$/);
    parent.on("response", (reply) => { if (reply.url().includes("/api/") && reply.status() >= 400) failures.push(`${reply.status()} ${new URL(reply.url()).pathname}`); });
    await parent.getByRole("button", { name: "Chatbot'u aç", exact: true }).click();
    await parent.getByPlaceholder("Bir şey yazın...").fill("Notları göster");
    const answer = parent.waitForResponse((reply) => (reply.url().includes("/v1/chatbot/process-query") || reply.url().includes("/parent/chatbot")));
    await parent.getByRole("button", { name: "Mesaj gönder", exact: true }).click(); expect((await (await answer).json()).data.response_markdown).toContain("Sıfır not sınavı");
    await expect(parent).toHaveURL(/\/parent\/academic$/);
    await expect(parent.getByRole("cell", { name: "0 / 80", exact: true })).toBeVisible();
    const publishedCards = parent.getByRole("region", { name: "Yayımlanan karneler", exact: true });
    await expect(publishedCards.getByText("1.75 / 4", { exact: true })).toBeVisible();
    await expect(publishedCards.getByText("Öğretmen: Panelden doğrulanmış dönem karnesi", { exact: true })).toBeVisible();
    expect(await parent.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await parent.screenshot({ path: "../output/parent-exam-grades-mobile-20261104.png", fullPage: true });
    expect(failures).toEqual([]);
  } finally { await context.close(); }
});

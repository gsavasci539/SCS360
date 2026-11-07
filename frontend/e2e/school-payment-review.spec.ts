import { expect, test, type Page } from "./fixtures";
import type { APIRequestContext } from "@playwright/test";

type Auth = Record<string, string>;
async function data(request: APIRequestContext, path: string, auth: Auth, body?: Record<string, unknown>) {
  const response = body ? await request.post(path, { headers: auth, data: body }) : await request.get(path, { headers: auth });
  expect(response.status(), await response.text()).toBe(200);
  return (await response.json()).data;
}
async function login(request: APIRequestContext, name: string) {
  return data(request, "/api/auth/login", {}, { email: `${name}@acceptance.example.com`, password: "Acceptance-Only-2026!" });
}
async function pendingReview(page: Page, request: APIRequestContext) {
  const staff = await login(request, "accountant"), root = await login(request, "admin");
  const auth = { Authorization: `Bearer ${staff.access_token}` };
  const rootAuth = { Authorization: `Bearer ${root.access_token}`, "X-SCS360-Organization-Id": staff.user.organization_id };
  const suffix = crypto.randomUUID();
  const student = await data(request, "/api/students", rootAuth, { organization_id: staff.user.organization_id,
    branch_id: staff.user.branch_ids[0], first_name: "Online", last_name: `Kabul ${suffix.slice(0, 8)}` });
  const debt = await data(request, "/api/debts", auth, { student_id: student.id, debt_type: "EDUCATION",
    amount: "100.00", due_date: new Date().toISOString().slice(0, 10), description: `School review ${suffix}` });
  const checkout = await data(request, "/api/payments/iyzico/initialize", auth, { request_id: crypto.randomUUID(), debt_id: debt.id,
    amount: "25.00", currency: "TRY", buyer: { identityNumber: "ACCEPTANCE-ONLY", registrationAddress: "Acceptance billing address", city: "Istanbul", country: "Turkey" } });
  expect(checkout.status).toBe("PENDING");
  const cash = await data(request, "/api/payments", auth, { request_id: crypto.randomUUID(), debt_id: debt.id, amount: "85.00", payment_method: "CASH" });
  await page.goto("/login");
  await page.getByLabel("E-posta adresi", { exact: true }).fill("accountant@acceptance.example.com");
  await page.getByLabel("Şifre", { exact: true }).fill("Acceptance-Only-2026!");
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);
  // The hosted form never reaches iyzico: every provider navigation is intercepted.
  await page.route("https://**.iyzipay.com/**", async (route) => {
    const url = new URL(route.request().url()), token = url.pathname.split("/").pop() || "";
    expect(url.hostname).toBe("sandbox-api.iyzipay.com");
    expect(url.pathname).toMatch(/^\/scs360-acceptance-school\/school-browser-[0-9a-f-]+$/);
    expect(token).toBe(`school-browser-${checkout.id}`);
    await route.fulfill({ contentType: "text/html; charset=utf-8", body: `<html lang="tr"><meta charset="utf-8"><h1>Yalnız okul kabul testi</h1><form method="post" action="http://127.0.0.1:5016/api/payments/iyzico/callback?checkout_id=${checkout.id}"><input name="token" type="hidden" value="${token}"><button>İmzalı test sonucunu gönder</button></form></html>` });
  });
  await page.goto(checkout.checkout_url);
  await page.getByRole("button", { name: "İmzalı test sonucunu gönder", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/payment\\?checkout=${checkout.id}$`));
  const reviewPath = `/api/payments/iyzico/checkouts/${checkout.id}/review`;
  const review = await data(request, reviewPath, auth);
  expect(review.status).toBe("PAID_REVIEW"); expect(review.remaining_amount).toBe("15.00");
  expect(review.can_apply).toBe(false); expect(review.can_refund).toBe(true);
  return { auth, rootAuth, student, debt, cash, checkout, reviewPath };
}

async function modalBlocksChatbotPointers(page: Page, checkoutId: string) {
  const dialog = page.getByRole("dialog", { name: "Online ödeme incelemesi", exact: true });
  const fab = page.getByRole("button", { name: "Chatbot'u aç", exact: true });
  await expect(dialog).toBeVisible(); await expect(fab).toBeVisible();
  const fabBox = await fab.boundingBox(); expect(fabBox).not.toBeNull();
  const fabCenter = { x: fabBox!.x + fabBox!.width / 2, y: fabBox!.y + fabBox!.height / 2 };
  await expect.poll(() => page.evaluate(({ x, y }) => Boolean(document.elementFromPoint(x, y)?.closest(".modal-backdrop")), fabCenter)).toBe(true);
  await dialog.getByRole("button", { name: "Pencereyi kapat", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page).toHaveURL(/\/finance\/online-payments$/);
  await fab.click(); await expect(page.locator(".chatbot-container")).toBeVisible();
  // React Router's query-only history navigation preserves the open chat widget.
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/finance/online-payments\\?checkout=${checkoutId}$`));
  await expect(dialog).toBeVisible(); await expect(page.locator(".chatbot-container")).toBeVisible();
  const chatBox = await page.locator(".chatbot-container").boundingBox(); expect(chatBox).not.toBeNull();
  const chatCenter = { x: chatBox!.x + chatBox!.width / 2, y: chatBox!.y + chatBox!.height / 2 };
  await expect.poll(() => page.evaluate(({ x, y }) => Boolean(document.elementFromPoint(x, y)?.closest(".modal-backdrop")), chatCenter)).toBe(true);
}

test("native school review applies a signed captured payment after the conflicting cash receipt is cancelled", async ({ page, request }) => {
  test.skip(process.env.SCS360_ACCEPTANCE_SCHOOL_GATEWAY !== "1", "Requires the isolated, memory-only school gateway");
  const scenario = await pendingReview(page, request);
  await data(request, `/api/payments/${scenario.cash.payment_id}/cancel`, scenario.auth, { cancel_reason: "Conflicting test cash receipt corrected before online review" });
  expect(Number((await data(request, `/api/debts/${scenario.debt.id}`, scenario.auth)).paid_amount)).toBe(0);
  const failures: string[] = [];
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/finance/online-payments?checkout=${scenario.checkout.id}`);
  const dialog = page.getByRole("dialog", { name: "Online ödeme incelemesi", exact: true });
  await expect(dialog).toContainText("100.00 TRY");
  const form = dialog.getByRole("form", { name: "Okul ödemesi mutabakatı", exact: true });
  await form.getByLabel("Kontrol açıklaması", { exact: true }).fill("Signed provider capture checked; the conflicting cash receipt was cancelled.");
  const saved = page.waitForResponse((response) => response.url().endsWith(scenario.reviewPath) && response.request().method() === "POST");
  await form.getByRole("button", { name: "Doğrulanan ödemeyi borca işle", exact: true }).click();
  const response = await saved; expect(response.status()).toBe(200);
  const resolved = (await response.json()).data;
  expect(resolved.status).toBe("COMPLETED"); expect(resolved.payment_id).toBeTruthy(); expect(resolved.receipt_id).toBeTruthy();
  await expect(dialog.getByRole("status")).toContainText("Mutabakat isteğinin sonucu kaydedildi.");
  const ledger = await data(request, `/api/payments?student_id=${scenario.student.id}&status=ALL`, scenario.auth);
  expect(ledger.items).toHaveLength(2);
  expect(ledger.items.find((row: { id: string }) => row.id === scenario.cash.payment_id).cancelled).toBe(true);
  expect(ledger.items.filter((row: { cancelled: boolean }) => !row.cancelled)).toHaveLength(1);
  expect(Number((await data(request, `/api/debts/${scenario.debt.id}`, scenario.auth)).paid_amount)).toBe(25);
  expect(Number((await data(request, `/api/receipts/${resolved.receipt_id}`, scenario.rootAuth)).remaining_debt)).toBe(75);
  await page.reload(); await expect(dialog.getByRole("region", { name: "Mutabakat işlem geçmişi", exact: true })).toContainText("Borca işleme");
  await expect(dialog.getByRole("form")).toHaveCount(0);
  expect((await data(request, scenario.reviewPath, scenario.auth)).payment_id).toBe(resolved.payment_id);
  expect((await data(request, `/api/payments?student_id=${scenario.student.id}&status=ALL`, scenario.auth)).items).toHaveLength(2);
  await modalBlocksChatbotPointers(page, scenario.checkout.id);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/school-payment-review-apply-mobile.png", fullPage: true });
  expect(failures).toEqual([]);
});

test("native school review records an already performed full external refund without changing cash or online ledger", async ({ page, request }) => {
  test.skip(process.env.SCS360_ACCEPTANCE_SCHOOL_GATEWAY !== "1", "Requires the isolated, memory-only school gateway");
  const scenario = await pendingReview(page, request);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/finance/online-payments?checkout=${scenario.checkout.id}`);
  const dialog = page.getByRole("dialog", { name: "Online ödeme incelemesi", exact: true });
  await expect(dialog).toContainText("15.00 TRY");
  const form = dialog.getByRole("form", { name: "Okul ödemesi mutabakatı", exact: true });
  await expect(form.getByLabel("Mutabakat işlemi", { exact: true })).toHaveValue("REFUND_RECORDED");
  await form.getByLabel("Dış iade referansı", { exact: true }).fill(`FAKE-EXTERNAL-REFUND-${scenario.checkout.id}`);
  await expect(form.getByLabel("Tam iade tutarı", { exact: true })).toHaveValue("25.00");
  await expect(form.getByLabel("İade para birimi", { exact: true })).toHaveValue("TRY");
  const past = await page.evaluate(() => { const value = new Date(Date.now() - 60_000), pad = (part: number) => String(part).padStart(2, "0"); return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`; });
  await form.getByLabel("Gerçekleşen iade tarihi", { exact: true }).fill(past);
  await form.getByLabel("Kontrol açıklaması", { exact: true }).fill("Fake provider external full refund checked; no refund is sent by this screen.");
  const saved = page.waitForResponse((response) => response.url().endsWith(scenario.reviewPath) && response.request().method() === "POST");
  await form.getByRole("button", { name: "Dış iade kaydını kaydet", exact: true }).click();
  const response = await saved; expect(response.status()).toBe(200);
  const resolved = (await response.json()).data;
  expect(resolved.status).toBe("REFUNDED"); expect(resolved.payment_id).toBeNull(); expect(resolved.receipt_id).toBeNull();
  await page.reload(); await expect(dialog.getByRole("region", { name: "Mutabakat işlem geçmişi", exact: true })).toContainText("Dış iade kaydı");
  await expect(dialog.getByRole("form")).toHaveCount(0);
  const ledger = await data(request, `/api/payments?student_id=${scenario.student.id}&status=ALL`, scenario.auth);
  expect(ledger.items).toHaveLength(1); expect(ledger.items[0].id).toBe(scenario.cash.payment_id); expect(ledger.items[0].cancelled).toBe(false);
  expect(Number((await data(request, `/api/debts/${scenario.debt.id}`, scenario.auth)).paid_amount)).toBe(85);
  expect((await data(request, scenario.reviewPath, scenario.auth)).status).toBe("REFUNDED");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../output/school-payment-review-refund-mobile.png", fullPage: true });
});

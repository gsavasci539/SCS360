import { readFile } from "node:fs/promises";
import { expect, test } from "./fixtures";

test("teacher uses the scoped directory and private attachments on small screens", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-posta adresi" }).fill("teacher@acceptance.example.com");
  await page.getByLabel("Şifre", { exact: true }).fill("Acceptance-Only-2026!");
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  await page.goto("/teacher");
  await expect(page).toHaveURL(/\/teacher$/);
  await page.getByRole("button", { name: "Mesajlar", exact: true }).click();

  const pane = page.locator(".staff-student-chat");
  const branch = pane.getByRole("combobox", { name: "Şube", exact: true });
  await expect(branch.getByRole("option", { name: "Test Şubesi" })).toBeAttached();
  const branchId = await branch.selectOption({ label: "Test Şubesi" });
  await pane.getByRole("searchbox").fill("Deniz Kabul");
  const filtered = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname.endsWith("/teacher/chat-contacts") && url.searchParams.get("search") === "Deniz Kabul"
      && url.searchParams.get("branch_id") === branchId[0];
  });
  await pane.getByRole("button", { name: "Ara", exact: true }).click();
  expect((await filtered).ok()).toBe(true);
  const contact = pane.getByRole("button", { name: /Deniz Kabul.*Parent Kabul/ });
  await expect(contact).toBeVisible();
  expect(await pane.evaluate((node) => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
  await contact.click();
  await expect(pane.getByRole("heading", { name: "Deniz Kabul" })).toBeVisible();

  const name = "Kabul-belgesi.pdf";
  const bytes = Buffer.from("%PDF-1.4\nIsolated browser chat attachment");
  const upload = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return /\/api\/teacher\/chat\/[^/]+\/send-file$/.test(url.pathname) &&
      Boolean(url.searchParams.get("parent_id")) && url.searchParams.get("branch_id") === branchId[0];
  });
  await pane.getByLabel("Sohbet dosyası").setInputFiles({ name, mimeType: "application/pdf", buffer: bytes });
  await pane.getByRole("button", { name: "Gönder", exact: true }).click();
  expect((await upload).ok()).toBe(true);
  const stored = pane.getByRole("button", { name, exact: true });
  await expect(stored).toBeVisible();
  const download = page.waitForEvent("download");
  await stored.click();
  const file = await download;
  expect(file.suggestedFilename()).toBe(name);
  expect(await readFile(await file.path())).toEqual(bytes);

  await page.route(/\/api\/teacher\/chat\/[^/]+\/attachments\/[^?]+/, (route) =>
    route.fulfill({ contentType: "application/octet-stream", body: "%PDF-1.4\nCorrupt test bytes" }));
  const unexpectedDownloads: string[] = [];
  page.on("download", (item) => unexpectedDownloads.push(item.suggestedFilename()));
  await stored.click();
  await expect(pane.getByRole("alert")).toContainText("İndirilen dosya, kayıttaki SHA-256 özetiyle eşleşmiyor.");
  expect(unexpectedDownloads).toEqual([]);

  await page.setViewportSize({ width: 640, height: 360 });
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await pane.evaluate((node) => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
  await expect(pane.getByRole("button", { name: "Sohbeti kapat" })).toBeVisible();
});

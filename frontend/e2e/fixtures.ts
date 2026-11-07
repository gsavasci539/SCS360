import { test as base, expect } from "@playwright/test";
export type { Page } from "@playwright/test";
export { expect };
export const test = base.extend<{ independentLoginWindow: void }>({
  independentLoginWindow: [async ({ request }, use) => {
    const response = await request.post("/api/__acceptance/reset-limits");
    expect(response.ok()).toBe(true);
    await use();
  }, { auto: true }],
});

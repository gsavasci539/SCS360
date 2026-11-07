import { afterEach, expect, it, vi } from "vitest";
import { checkoutAmount, checkoutAttemptKey, checkoutResult, checkoutScope, clearSchoolCheckout, readSchoolCheckout, saveSchoolCheckout } from "../features/payment/schoolCheckoutAttempt";
import type { AuthUser } from "../types/api";

const debt = "00000000-0000-4000-8000-000000000001", nonce = "00000000-0000-4000-8000-000000000002";
const user: AuthUser = { id: "actor", organization_id: "school", first_name: "Test", last_name: "User", email: "test@example.invalid", is_super_admin: false, roles: [], permissions: [], branch_ids: ["b"] };
const attempt = { version: 1 as const, request_id: nonce, debt_id: debt, amount: "25.00", status: "INITIALIZING" as const };
afterEach(() => { sessionStorage.clear(); vi.restoreAllMocks(); });

it("separates recovery identities by actor, organization, purpose and debt", () => {
  const staff = checkoutScope(user, null, "staff"), parent = checkoutScope(user, null, "parent");
  expect(staff).not.toBe(parent);
  expect(checkoutScope({ ...user, id: "other" }, null, "staff")).not.toBe(staff);
  expect(checkoutScope({ ...user, organization_id: "other" }, null, "staff")).not.toBe(staff);
  expect(checkoutAttemptKey(staff, debt)).not.toBe(checkoutAttemptKey(staff, nonce));
  expect(checkoutScope({ ...user, is_super_admin: true }, null, "staff")).toBeNull();
  expect(checkoutScope({ ...user, is_super_admin: true }, { id: "school", name: "School", operatorId: "different" }, "staff")).toBeNull();
});

it("persists the UUID before initialize while excluding buyer identity, address and hosted secrets", () => {
  const key = checkoutAttemptKey(checkoutScope(user, null, "staff"), debt)!;
  saveSchoolCheckout(key, { ...attempt, buyer: { identityNumber: "PRIVATE_ID", registrationAddress: "PRIVATE_ADDRESS" }, checkout_url: "https://sandbox-api.iyzipay.com/?token=PRIVATE_TOKEN" } as typeof attempt);
  const raw = sessionStorage.getItem(key)!;
  expect(raw).not.toMatch(/buyer|PRIVATE|checkout_url|identityNumber|registrationAddress/);
  expect(readSchoolCheckout(key).attempt).toEqual(attempt);
});

it("does not silently discard corrupt or unavailable storage and mint a different attempt", () => {
  const key = checkoutAttemptKey(checkoutScope(user, null, "parent"), debt)!;
  sessionStorage.setItem(key, "corrupt"); expect(readSchoolCheckout(key).error).toContain("Yeni ödeme başlatmadan");
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("denied"); });
  expect(() => saveSchoolCheckout(key, attempt)).toThrow("saklanamadı");
});

it("cannot clear a different payment or accept a response with another checkout UUID", () => {
  const key = checkoutAttemptKey(checkoutScope(user, null, "staff"), debt)!;
  saveSchoolCheckout(key, attempt);
  expect(() => clearSchoolCheckout(key, debt)).toThrow("yeni ödeme açılmadı");
  expect(() => checkoutResult({ conversation_id: debt, status: "COMPLETED" }, nonce)).toThrow("eşleşmiyor");
  expect(checkoutAmount("0.01")).toBe("0.01"); expect(checkoutAmount("25")).toBe("25.00");
  for (const value of [0, "NaN", "Infinity", "1.001", "1e5", ""]) expect(checkoutAmount(value)).toBeNull();
});

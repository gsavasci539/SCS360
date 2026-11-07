import { describe, expect, it } from "vitest";
import { getHomePath } from "../lib/home";
import type { AuthUser } from "../types/api";

function userWith(role: string, permissions?: string[]): AuthUser {
  const defaults: Record<string, string[]> = { parent: ["parent.view_children"], teacher: ["teacher.view_classes"],
    accountant: ["finance.read"], canteen_staff: ["canteen.read"], manager: ["dashboard.read"] };
  return {
    id: "user-id",
    email: "user@example.com",
    first_name: "Test",
    last_name: "User",
    is_super_admin: false,
    organization_id: "org-id",
    roles: [{ id: `${role}-id`, name: role, slug: role }],
    permissions: permissions ?? defaults[role] ?? [],
    branch_ids: [],
  };
}

describe("giriş sonrası rol ana sayfası", () => {
  it("rol kaydı olmayan süper yöneticiyi yönetim paneline gönderir", () => {
    const user = { ...userWith("staff"), roles: [], is_super_admin: true };
    expect(getHomePath(user)).toBe("/platform");
  });
  it.each([
    ["parent", "/parent/dashboard"],
    ["teacher", "/teacher"],
    ["accountant", "/finance/debts"],
    ["canteen_staff", "/canteen/sales"],
    ["manager", "/dashboard"],
  ])("%s rolünü kendi çalışma alanına yönlendirir", (role, path) => {
    expect(getHomePath(userWith(role))).toBe(path);
  });

  it("tekil öğrenci yetkisini çoğul korumalı öğrenci yoluna eşler", () => {
    expect(getHomePath(userWith("custom", ["student.read"]))).toBe("/students");
  });

  it("çok rollü bir veliyi her zaman veli çalışma alanına gönderir", () => {
    const user = userWith("administrator", ["dashboard.read"]);
    user.roles.unshift({ id: "parent-id", name: "parent", slug: "parent" });
    user.permissions.push("parent.view_children");
    expect(getHomePath(user)).toBe("/parent/dashboard");
  });

  it("erişimi olmayan kullanıcıyı yetkisiz sayfasına yönlendirir", () => {
    expect(getHomePath(userWith("staff"))).toBe("/forbidden");
  });

  it.each([
    ["teacher", ["exam.write"], "/exams"],
    ["accountant", ["finance.write"], "/finance/payments/new"],
    ["cashier", ["finance.write"], "/finance/payments/new"],
    ["cashier", ["finance.collect_payment"], "/finance/payments/new"],
  ])("%s için yetkisi kaldırılmış başlangıç yerine erişilebilir çalışma sayfasını seçer", (role, permissions, path) => {
    expect(getHomePath(userWith(role, permissions))).toBe(path);
  });
});

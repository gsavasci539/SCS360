import { createRoutesFromChildren, matchRoutes } from "react-router-dom";
import { isValidElement } from "react";
import { describe, expect, it } from "vitest";
import App from "../App";
import { navigation } from "../config/navigation";
import { hasPermission } from "../stores/auth";
import type { AuthUser } from "../types/api";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

describe("menü ve sayfa yetkisi sözleşmesi", () => {
  const routes = createRoutesFromChildren(App().props.children);
  it("aynı sayfa menüde tek bağlantı olarak tanımlıdır", () => {
    const paths = navigation.flatMap((section) => section.items.map((item) => item.path));
    expect(paths.filter((path, index) => paths.indexOf(path) !== index)).toEqual([]);
  });
  it("ekranlardaki sabit bağlantılar kayıtlı bir sayfaya gider", () => {
    const root = join(process.cwd(), "src");
    const missing: string[] = [];
    for (const file of readdirSync(root, { recursive: true, withFileTypes: true })) {
      if (!file.isFile() || !file.name.endsWith(".tsx") || file.parentPath.includes("test")) continue;
      const source = readFileSync(join(file.parentPath, file.name), "utf8");
      for (const match of source.matchAll(/\b(to|detailBase)="(\/[^"?#]*)"/g)) {
        const target = match[1] === "detailBase" ? `${match[2]}/test-record-id` : match[2];
        const matched = matchRoutes(routes, target);
        if (!matched || matched.at(-1)?.route.path === "*") missing.push(`${file.name}: ${target}`);
      }
    }
    expect(missing).toEqual([]);
  });
  for (const item of navigation.flatMap((section) => section.items)) {
    it(`${item.path} menüde görünen kullanıcıya açılır`, () => {
      const matches = matchRoutes(routes, item.path);
      expect(matches, `Kayıtsız menü adresi: ${item.path}`).not.toBeNull();
      expect(matches?.at(-1)?.route.path).not.toBe("*");
      const user: AuthUser = {
        id: "contract-user", email: "contract@example.test", first_name: "Test", last_name: "User",
        is_super_admin: item.permission === "super_admin", organization_id: "org",
        roles: [], permissions: item.permission ? [item.permission] : [], branch_ids: [],
      };
      for (const match of matches || []) {
        const element = match.route.element;
        if (!isValidElement<{ permission?: string }>(element)) continue;
        if (element.props.permission) {
          expect(hasPermission(user, element.props.permission),
            `${item.path}: menü=${item.permission}, sayfa=${element.props.permission}`).toBe(true);
        }
      }
    });
  }
});

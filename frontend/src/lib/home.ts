import { hasPermission } from "../stores/auth";
import type { AuthUser } from "../types/api";

const roleHomePaths: Record<string, string> = {
  parent: "/parent/dashboard",
  teacher: "/teacher",
  accountant: "/finance/debts",
  canteen: "/canteen/sales",
  canteen_staff: "/canteen/sales",
  manager: "/dashboard",
  administrator: "/dashboard",
  branch_manager: "/dashboard",
  org_admin: "/dashboard",
  owner: "/dashboard",
  super_admin: "/dashboard",
};

const rolePriority = [
  "parent",
  "teacher",
  "accountant",
  "canteen_staff",
  "canteen",
  "manager",
  "administrator",
  "branch_manager",
  "org_admin",
  "owner",
  "super_admin",
];

const homePermissions: Record<string, string> = {
  "/parent/dashboard": "parent.view_children", "/teacher": "teacher.view_classes",
  "/finance/debts": "finance.read", "/canteen/sales": "canteen.read", "/dashboard": "dashboard.read",
};

const permissionHomePaths: Array<[string, string]> = [
  ["parent.view_children", "/parent/dashboard"],
  ["finance.read", "/finance/debts"],
  ["finance.write", "/finance/payments/new"],
  ["finance.collect_payment", "/finance/payments/new"],
  ["canteen.read", "/canteen/sales"],
  ["attendance.read", "/attendance"],
  ["students.read", "/students"],
  ["library.read", "/library"],
  ["daily_reports.read", "/daily-reports"],
  ["academic.read", "/timetable"],
  ["exam.read", "/exams"],
  ["exam.write", "/exams"],
  ["health.read", "/health"],
  ["guidance.read", "/guidance"],
  ["bus.read", "/transport"],
  ["tutoring.read", "/tutoring"],
  ["clubs.read", "/clubs"],
  ["payroll.read", "/payroll"],
  ["inventory.read", "/inventory"],
  ["survey.read", "/surveys"],
  ["consent.read", "/consents"],
  ["report.read", "/reports"],
  ["settings.read", "/settings"],
  ["dashboard.read", "/dashboard"],
];

/**
 * Select the first page a user can meaningfully use after authentication.
 * Explicit role landing pages take precedence over shared permissions: a
 * parent with reporting permissions still opens the parent portal, for example.
 */
export function getHomePath(user: AuthUser | null | undefined): string {
  if (!user) return "/login";
  if (user.is_super_admin) return "/platform";
  if (user.organization_access?.restricted) return "/subscription";

  const roleSlugs = new Set(user.roles.map((role) => role.slug.toLowerCase()));
  for (const roleSlug of rolePriority) {
    if (!roleSlugs.has(roleSlug)) continue;
    const path = roleHomePaths[roleSlug];
    if (path && hasPermission(user, homePermissions[path])) return path;
  }

  const permissionPath = permissionHomePaths.find(([permission]) => hasPermission(user, permission));
  return permissionPath?.[1] ?? "/forbidden";
}

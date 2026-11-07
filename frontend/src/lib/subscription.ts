import type { OrganizationAccess } from "../types/api";

const states = new Set(["PLATFORM", "LEGACY", "ACTIVE", "GRACE", "PAST_DUE", "SUSPENDED", "UNCONFIGURED", "UNASSIGNED", "REVIEW_REQUIRED", "NOT_STARTED", "PENDING_PAYMENT"]);
export function isOrganizationAccess(value: unknown): value is OrganizationAccess {
  if (!value || typeof value !== "object") return false;
  const data = value as Record<string, unknown>;
  return typeof data.status === "string" && states.has(data.status) && typeof data.restricted === "boolean"
    && data.billing_path === "/subscription" && (data.warning === null || typeof data.warning === "string")
    && (data.period_end === null || typeof data.period_end === "string") && (data.grace_end === null || typeof data.grace_end === "string")
    && (data.days_remaining === null || (typeof data.days_remaining === "number" && Number.isInteger(data.days_remaining) && data.days_remaining >= 0));
}

export function subscriptionAccessFromError(value: unknown): OrganizationAccess | null {
  if (!value || typeof value !== "object") return null;
  const errors = (value as { errors?: unknown }).errors;
  if (!Array.isArray(errors)) return null;
  for (const error of errors) {
    if (error && typeof error === "object" && error.code === "SUBSCRIPTION_REQUIRED" && isOrganizationAccess(error.access)) return error.access;
  }
  return null;
}

export function packagePrice(amount: unknown, currency: unknown = "TRY") {
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: String(currency), minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(amount || 0));
}

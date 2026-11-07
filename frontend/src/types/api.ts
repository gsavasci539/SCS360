export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  errors?: unknown[];
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Role { id: string; name: string; slug: string }

export interface OrganizationAccess {
  status: "PLATFORM" | "LEGACY" | "ACTIVE" | "GRACE" | "PAST_DUE" | "SUSPENDED" | "UNCONFIGURED" | "UNASSIGNED" | "REVIEW_REQUIRED" | "NOT_STARTED" | "PENDING_PAYMENT";
  restricted: boolean;
  warning: string | null;
  period_end: string | null;
  grace_end: string | null;
  billing_path: "/subscription";
  days_remaining: number | null;
}

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  status?: string;
  is_super_admin: boolean;
  organization_id: string | null;
  roles: Role[];
  permissions: string[];
  branch_ids: string[];
  last_login_at?: string;
  organization_access?: OrganizationAccess;
}

export interface AuthPayload {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

export type RecordValue = string | number | boolean | null | undefined | Record<string, unknown>[];
export type DataRecord = Record<string, RecordValue> & { id: string };

export interface SelectOption { label: string; value: string }

export interface FieldConfig {
  name: string;
  label: string;
  type?: "text" | "email" | "password" | "number" | "date" | "textarea" | "select" | "checkbox";
  required?: boolean;
  placeholder?: string;
  options?: SelectOption[];
  optionSource?: string;
  searchable?: boolean;
  optionLabel?: string;
  optionValue?: string;
  min?: number;
  step?: number;
  full?: boolean;
  hideOnEdit?: boolean;
  defaultValue?: string | boolean | number;
}

export interface ColumnConfig {
  key: string;
  label: string;
  type?: "text" | "status" | "date" | "money" | "person" | "roles" | "capacity";
  subKey?: string;
}

export interface ResourceConfig {
  key: string;
  title: string;
  singular: string;
  description: string;
  endpoint: string;
  permissionRead?: string;
  permissionWrite?: string;
  columns: ColumnConfig[];
  fields: FieldConfig[];
  filters?: SelectOption[];
  detailPath?: string;
  listPath?: string;
  parentOnly?: boolean;
}

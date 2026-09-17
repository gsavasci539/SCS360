import type { Paginated } from "../types/api";

export function toArray<T>(data: T[] | Paginated<T> | null | undefined): T[] {
  if (Array.isArray(data)) return data;
  return Array.isArray(data?.items) ? data.items : [];
}

export function toPaginated<T>(data: T[] | Paginated<T> | null | undefined, fallbackPageSize = 20): Paginated<T> {
  if (Array.isArray(data)) {
    return {
      items: data,
      total: data.length,
      page: 1,
      page_size: data.length || fallbackPageSize,
      total_pages: 1,
    };
  }

  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total: Number(data?.total || 0),
    page: Number(data?.page || 1),
    page_size: Number(data?.page_size || fallbackPageSize),
    total_pages: Math.max(1, Number(data?.total_pages || 1)),
  };
}

export function textValue(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") return fallback;
  return String(value);
}

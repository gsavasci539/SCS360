import { useEffect, useState } from "react";
import { useController, type Control } from "react-hook-form";
import { Field } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, FieldConfig, Paginated } from "../../types/api";

type Choice = { id: string; name: string };
type Values = Record<string, string | number | boolean>;

export function ResourceChoice({ field, control, organizationId, branchId, studentId }: {
  field: FieldConfig; control: Control<Values>; organizationId?: string; branchId?: string; studentId?: string;
}) {
  const { field: input, fieldState } = useController({ control, name: field.name,
    rules: { required: field.required ? `${field.label} seçin` : false } });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [rows, setRows] = useState<Choice[]>([]);
  const [selected, setSelected] = useState<Choice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const value = input.value ? String(input.value) : "";

  useEffect(() => {
    const controller = new AbortController();
    const delay = setTimeout(() => {
      setLoading(true); setError("");
      api.get<ApiResponse<Paginated<Choice> & { selected?: Choice | null }>>(field.optionSource!, {
        params: { page, page_size: 50, search: search || undefined, selected_id: value || undefined,
          organization_id: organizationId, branch_id: branchId, student_id: studentId },
        signal: controller.signal,
      }).then(({ data }) => {
        if (controller.signal.aborted) return;
        setRows(data.data.items); setPages(data.data.total_pages || 1); setSelected(data.data.selected || null);
      }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 200);
    return () => { clearTimeout(delay); controller.abort(); };
  }, [field.optionSource, page, search, value, organizationId, branchId, studentId, retry]);

  const choices = selected && !rows.some((row) => row.id === selected.id) ? [selected, ...rows] : rows;
  return <div className={field.full ? "field field-full" : "field"}>
    <label>{field.label} ara<input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Ad veya numara ile arayın" /></label>
    <Field label={field.label} required={field.required} error={fieldState.error?.message}>
      <select {...input} value={value} disabled={loading || Boolean(error)} aria-busy={loading}>
        <option value="">Seçiniz</option>
        {value && !choices.some((row) => row.id === value) && <option value={value}>Mevcut seçim</option>}
        {choices.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
      </select>
    </Field>
    {loading && <span role="status">Seçenekler yükleniyor…</span>}
    {error && <div role="alert">{error} <button type="button" className="btn btn-secondary" onClick={() => setRetry((count) => count + 1)}>Tekrar dene</button></div>}
    {pages > 1 && <div className="pagination" aria-label={`${field.label} seçenek sayfaları`}>
      <button type="button" className="btn btn-secondary" disabled={loading || page <= 1} onClick={() => setPage((count) => count - 1)}>Önceki</button>
      <span>{page} / {pages}</span>
      <button type="button" className="btn btn-secondary" disabled={loading || page >= pages} onClick={() => setPage((count) => count + 1)}>Sonraki</button>
    </div>}
  </div>;
}

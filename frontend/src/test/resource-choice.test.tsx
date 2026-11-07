import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { afterEach, expect, it, vi } from "vitest";
import { ResourceChoice } from "../features/resources/ResourceChoice";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "Seçenekler yüklenemedi" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("arama ve sayfa değişince sayfa dışındaki mevcut öğrenci seçimini korur ve kaydeder", async () => {
  vi.mocked(api.get).mockImplementation(async (_path, options) => {
    const page = Number((options?.params as Record<string, unknown> | undefined)?.page || 1);
    return { data: { data: { items: [{ id: `page-${page}`, name: `Sayfa ${page} öğrencisi` }], total_pages: 3,
      selected: { id: "selected-outside-page", name: "Mevcut Öğrenci · 0101" } } } };
  });
  const save = vi.fn();
  function Form() {
    const { control, handleSubmit } = useForm<Record<string, string | number | boolean>>({ defaultValues: { student_id: "selected-outside-page" } });
    return <form onSubmit={handleSubmit(save)}><ResourceChoice control={control} field={{ name: "student_id", label: "Öğrenci", required: true, searchable: true, optionSource: "/debts/student-options" }} /><button>Kaydet</button></form>;
  }
  render(<Form />);
  const select = await screen.findByRole("combobox", { name: /^Öğrenci/ });
  await waitFor(() => expect(select).toBeEnabled());
  expect(select).toHaveValue("selected-outside-page");
  expect(screen.getByRole("option", { name: "Mevcut Öğrenci · 0101" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/debts/student-options", expect.objectContaining({ params: expect.objectContaining({ page: 2, selected_id: "selected-outside-page" }) })));
  fireEvent.change(screen.getByRole("searchbox", { name: "Öğrenci ara" }), { target: { value: "başka öğrenci" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/debts/student-options", expect.objectContaining({ params: expect.objectContaining({ page: 1, search: "başka öğrenci", selected_id: "selected-outside-page" }) })));
  expect(select).toHaveValue("selected-outside-page");
  fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
  await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ student_id: "selected-outside-page" }), expect.anything()));
});

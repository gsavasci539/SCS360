import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { DataTable } from "../components/DataTable";

afterEach(cleanup);
function table(values: Record<string, unknown>) {
  return render(<MemoryRouter><DataTable rows={[{ id: "branch", ...values }]} columns={[{ key: "capacity", label: "Kapasite", type: "capacity" }]}
    search="" onSearch={() => {}} page={1} totalPages={1} total={1} onPage={() => {}} /></MemoryRouter>);
}
it("sunucunun gerçek öğrenci sayısını doluluk yerine gösterir", () => {
  const view = table({ student_count: 12, occupancy: 0, capacity: 20 });
  expect(screen.getByText("12 / 20")).toBeInTheDocument();
  expect(view.container.querySelector(".progress span")).toHaveStyle({ width: "60%" });
});
it("gerçek sıfır öğrenci sayısını korur", () => {
  table({ student_count: 0, occupancy: 8, capacity: 20 }); expect(screen.getByText("0 / 20")).toBeInTheDocument();
});
it("gelmeyen öğrenci sayısını sıfır uydurmaz", () => {
  table({ capacity: 20 }); expect(screen.getByText("— / 20")).toBeInTheDocument();
});
it("kontenjan girilmemişse sıfıra bölerek doluluk göstermez", () => {
  const view = table({ student_count: 12, capacity: 0 }); expect(screen.getByText("12 öğrenci")).toBeInTheDocument();
  expect(screen.getByText("Kontenjan belirtilmemiş")).toBeInTheDocument(); expect(view.container.querySelector(".progress")).toBeNull();
});

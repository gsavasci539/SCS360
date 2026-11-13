import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { LibraryPage } from "../features/operations/OperationPages";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("does not offer an undeliverable library reminder", async () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => ({ data: { data: path === "/library/books" ? [] : [{
    id: "recorded-loan", book_title: "Recorded book", student_name: "Recorded student", class_name: "Class A",
    due_date: "2026-11-20", status: "BORROWED",
  }] } }) as never);
  render(<MemoryRouter><ToastProvider><LibraryPage /></ToastProvider></MemoryRouter>);
  await screen.findByText("Recorded book");
  expect(screen.getByRole("button", { name: "İade Al" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /hatırlat/i })).not.toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

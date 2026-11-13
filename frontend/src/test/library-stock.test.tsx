import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { LibraryPage } from "../features/resources/LibraryPage";
import { getAnalysis } from "../lib/analysis";
import { api } from "../lib/api";
import { ToastProvider } from "../components/Toast";

vi.mock("../lib/analysis", () => ({ getAnalysis: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

async function open(available: number) {
  vi.mocked(api.get).mockResolvedValue({ data: { success: true, data: [{ id: "recorded-book", title: "Recorded catalog title", author: "Recorded author", category: "Category", total_copies: 10, available_copies: available, available_count: 999 }] } });
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { recommendations: [] } } } as never);
  render(<MemoryRouter><ToastProvider><LibraryPage /></ToastProvider></MemoryRouter>);
  await screen.findByText("Recorded catalog title");
}

it("renders the canonical available_copies in the row and catalog summary", async () => {
  await open(7);
  const row = screen.getByText("Recorded catalog title").closest("tr")!;
  expect(within(row).getByText("7")).toBeInTheDocument();
  expect(within(screen.getByText("Mevcut", { selector: "div" }).parentElement!).getByText("7")).toBeInTheDocument();
  expect(screen.queryByText("999")).not.toBeInTheDocument();
});

it("preserves a real zero without using the obsolete field or issuing writes", async () => {
  await open(0);
  expect(within(screen.getByText("Recorded catalog title").closest("tr")!).getByText("0")).toBeInTheDocument();
  expect(within(screen.getByText("Mevcut", { selector: "div" }).parentElement!).getByText("0")).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
  expect(api.delete).not.toHaveBeenCalled();
});

it("uses the paginated API envelope and resets to page one for server search", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { success: true, data: {
    items: [{ id: "recorded-book", title: "Secret catalog title", author: "Recorded author", category: "Category", total_copies: 10, available_copies: 7 }],
    total: 21, page: 1, page_size: 20, total_pages: 2,
  } } });
  vi.mocked(getAnalysis).mockResolvedValue({ data: { success: true, data: { recommendations: [] } } } as never);
  render(<MemoryRouter><ToastProvider><LibraryPage /></ToastProvider></MemoryRouter>);
  await screen.findByText("Secret catalog title");
  fireEvent.change(screen.getByRole("textbox", { name: "Listede ara" }), { target: { value: "secret" } });
  await waitFor(() => expect(api.get).toHaveBeenLastCalledWith("/library/books", expect.objectContaining({
    params: expect.objectContaining({ page: 1, page_size: 20, limit: 20, skip: 0, search: "secret" }),
  })));
});

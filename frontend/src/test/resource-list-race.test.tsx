import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/Toast";
import { ResourceListPage } from "../features/resources/ResourcePages";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { get: vi.fn() }, apiMessage: () => "İstek tamamlanamadı" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
it("geç eski kurum listesi şube sayfasındaki yeni yanıtı ezmez", async () => {
  let finish!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementation(async (path) => path === "/organizations" ? await new Promise((resolve) => { finish = resolve; })
    : { data: { data: [{ id: "new", name: "Güncel şube", student_count: 0, capacity: 10 }] } });
  const page = (resourceKey: string) => <MemoryRouter><ToastProvider><ResourceListPage resourceKey={resourceKey} /></ToastProvider></MemoryRouter>;
  const view = render(page("organizations")); await waitFor(() => expect(finish).toBeDefined());
  const config = vi.mocked(api.get).mock.calls[0][1];
  view.rerender(page("branches")); expect(await screen.findByText("Güncel şube")).toBeInTheDocument();
  expect(config?.signal?.aborted).toBe(true);
  await act(async () => { finish({ data: { data: [{ id: "old", name: "Eski kurum" }] } }); });
  expect(screen.queryByText("Eski kurum")).not.toBeInTheDocument(); expect(screen.getByText("Güncel şube")).toBeInTheDocument();
});

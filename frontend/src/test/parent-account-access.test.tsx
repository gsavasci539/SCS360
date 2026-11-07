import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ParentAccountAccess } from "../features/parent/ParentAccountAccess";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() }, apiMessage: () => "Bağlantı kaydedilemedi" }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("arama veya geç yüklenen seçenek mevcut veli hesabını istemeden silmez", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { user_id: "current", users: [] } } }); vi.mocked(api.put).mockResolvedValue({ data: { data: {} } });
  render(<MemoryRouter><ParentAccountAccess parentId="parent" /></MemoryRouter>);
  const select = await screen.findByRole("combobox", { name: "Bağlanacak giriş hesabı" });
  await waitFor(() => expect(select).toHaveValue("current"));
  fireEvent.change(screen.getByLabelText("Veli hesabı ara"), { target: { value: "Başka isim" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2)); expect(select).toHaveValue("current");
  fireEvent.click(screen.getByRole("button", { name: "Giriş hesabı bağlantısını kaydet" }));
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/parents/parent/account", { user_id: "current" }));
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "../src/App";
import { AuthProvider } from "../src/auth";

const session = {
  accessToken: "bearer-token",
  user: { id: 1, email: "demo@conciliador.local" },
  expiresAt: Date.now() + 60_000,
};

function json(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderConsolidated() {
  localStorage.setItem("conciliador.session", JSON.stringify(session));
  window.history.pushState({}, "", "/consolidated");
  return render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
}

describe("consolidated movements and receipts", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.spyOn(window, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/catalog/sources")) {
        return json(url.includes("COMPROBANTE")
          ? { total: 1, items: [{ id: 3, code: "ARCA", name: "ARCA", type: "COMPROBANTE" }] }
          : { total: 1, items: [{ id: 1, code: "BANCO_NACION", name: "Banco Nación", type: "MOVIMIENTO" }] });
      }
      if (url.includes("/records?") && url.includes("type=COMPROBANTE")) {
        return json({
          page: 1,
          page_size: 25,
          total: 1,
          items: [{
            record_id: 20,
            type: "COMPROBANTE",
            source: { id: 3, code: "ARCA", name: "ARCA" },
            batch_id: 8,
            external_id: "00004567",
            date: "2026-11-22",
            amount: "153499.99",
            currency: "ARS",
            description: "76543210987654",
            state: "CONCILIADO",
            reconciled: true,
          }],
        });
      }
      return json({
        page: 1,
        page_size: 25,
        total: 1,
        items: [{
          record_id: 10,
          type: "MOVIMIENTO",
          source: { id: 1, code: "BANCO_NACION", name: "Banco Nación" },
          batch_id: 7,
          external_id: "BNA-001",
          date: "2026-11-20",
          amount: "125000.00",
          currency: "ARS",
          description: "Cobro factura",
          state: "PENDIENTE",
          reconciled: false,
        }],
      });
    });
  });

  afterEach(() => cleanup());

  it("renders both tabs and consolidated record columns", async () => {
    const user = userEvent.setup();
    renderConsolidated();

    expect(await screen.findByRole("heading", { name: "Movimientos y comprobantes" })).toBeInTheDocument();
    expect(await screen.findByText("BNA-001")).toBeInTheDocument();
    expect(screen.getByText("Cobro factura")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Conciliado" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Comprobantes" }));

    expect(await screen.findByText("00004567")).toBeInTheDocument();
    expect(screen.getByLabelText("Entidad")).toBeInTheDocument();
    expect(screen.getByText("153499.99")).toBeInTheDocument();
  });

  it("preserves independent full state for each tab and across remounts", async () => {
    const user = userEvent.setup();
    const rendered = renderConsolidated();
    await screen.findByText("BNA-001");

    await user.selectOptions(screen.getByLabelText("Banco"), "1");
    await user.selectOptions(screen.getByLabelText("Conciliado"), "true");
    fireEvent.change(screen.getByLabelText("Desde"), { target: { value: "2026-11-01" } });
    await user.selectOptions(screen.getByLabelText("Filas por página"), "50");
    await user.click(screen.getByRole("button", { name: "Referencia" }));
    await user.click(screen.getByRole("tab", { name: "Comprobantes" }));
    await screen.findByText("00004567");
    await user.selectOptions(screen.getByLabelText("Entidad"), "3");
    await user.selectOptions(screen.getByLabelText("Conciliado"), "false");

    await user.click(screen.getByRole("tab", { name: "Movimientos" }));
    expect(screen.getByLabelText("Banco")).toHaveValue("1");
    expect(screen.getByLabelText("Conciliado")).toHaveValue("true");
    expect(screen.getByLabelText("Desde")).toHaveValue("2026-11-01");
    expect(screen.getByLabelText("Filas por página")).toHaveValue("50");

    await waitFor(() => {
      const persisted = JSON.parse(localStorage.getItem("conciliador.consolidated.1")!);
      expect(persisted.tabs.MOVIMIENTO).toMatchObject({
        sourceId: "1",
        reconciled: "true",
        from: "2026-11-01",
        pageSize: 50,
        sortBy: "reference",
      });
      expect(persisted.tabs.COMPROBANTE).toMatchObject({ sourceId: "3", reconciled: "false" });
    });

    rendered.unmount();
    renderConsolidated();
    expect(await screen.findByLabelText("Banco")).toHaveValue("1");
    expect(screen.getByLabelText("Conciliado")).toHaveValue("true");
    expect(screen.getByLabelText("Desde")).toHaveValue("2026-11-01");
  });
});

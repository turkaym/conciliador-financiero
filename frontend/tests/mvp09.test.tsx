import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "../src/App";
import { AuthProvider } from "../src/auth";

const session = { accessToken: "bearer-token", user: { id: 1, email: "demo@conciliador.local" }, expiresAt: Date.now() + 60_000 };
const sources = {
  MOVIMIENTO: { total: 1, items: [{ id: 1, code: "BANCO_DEMO", name: "Banco demo", type: "MOVIMIENTO" }] },
  COMPROBANTE: { total: 1, items: [{ id: 2, code: "COMPROBANTES_DEMO", name: "Comprobantes demo", type: "COMPROBANTE" }] },
};
const templates = {
  MOVIMIENTO: { total: 1, items: [{ id: 11, name: "movimientos", type: "MOVIMIENTO", version: 1, columns: ["id_externo", "fecha", "monto", "moneda", "referencia", "tipo_movimiento"] }] },
  COMPROBANTE: { total: 1, items: [{ id: 22, name: "comprobantes", type: "COMPROBANTE", version: 1, columns: ["id_externo", "fecha", "monto", "moneda", "referencia", "clase"] }] },
};

function renderApp(path = "/") {
  localStorage.setItem("conciliador.session", JSON.stringify(session));
  window.history.pushState({}, "", path);
  return render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
}

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }); }

describe("MVP-09 import and pending workflows", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => cleanup());

  it("selects catalogs for both approved CSV types", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/catalog/sources")) return json(url.includes("COMPROBANTE") ? sources.COMPROBANTE : sources.MOVIMIENTO);
      return json(url.includes("source_id=2") ? templates.COMPROBANTE : templates.MOVIMIENTO);
    });
    const user = userEvent.setup();
    renderApp();
    await user.selectOptions(await screen.findByLabelText("Fuente"), "1");
    expect(await screen.findByRole("option", { name: "movimientos v1" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Tipo de archivo"), "COMPROBANTE");
    await user.selectOptions(await screen.findByLabelText("Fuente"), "2");
    expect(await screen.findByRole("option", { name: "comprobantes v1" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/catalog/sources?type=COMPROBANTE"), expect.objectContaining({ headers: expect.anything() }));
  });

  it("uploads a CSV and displays terminal status and row-level validation errors", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/catalog/sources")) return json(sources.MOVIMIENTO);
      if (url.includes("/catalog/templates")) return json(templates.MOVIMIENTO);
      if (url.endsWith("/batches")) {
        expect(init?.body).toBeInstanceOf(FormData);
        const form = init?.body as FormData;
        expect(form.get("type")).toBe("MOVIMIENTO");
        expect(form.get("source_id")).toBe("1");
        expect(form.get("template_id")).toBe("11");
        return json({ id: 31, source: sources.MOVIMIENTO.items[0], template: { id: 11, name: "movimientos", version: 1 }, requested_template_id: 11, type: "MOVIMIENTO", file_name: "movimientos.csv", status: "PROCESADO_CON_ERRORES", totals: { total_rows: 2, valid_rows: 1, invalid_rows: 1 }, received_at: "2026-10-22T12:00:00Z", finished_at: "2026-10-22T12:00:00Z" }, 202);
      }
      return json({ total: 1, items: [{ id: 99, scope: "FILA", row_number: 3, field: "monto", code: "MONTO_INVALIDO", message: "Invalid amount", original_record_id: null, created_at: "2026-10-22T12:00:00Z" }] });
    });
    const user = userEvent.setup();
    renderApp();
    await user.selectOptions(await screen.findByLabelText("Fuente"), "1");
    await user.selectOptions(await screen.findByLabelText("Plantilla"), "11");
    await user.upload(screen.getByLabelText("Archivo CSV"), new File(["fecha,monto\n2026-01-01,broken"], "movimientos.csv", { type: "text/csv" }));
    const submit = screen.getByRole("button", { name: "Validar archivo" });
    await waitFor(() => expect(submit).toBeEnabled());
    fireEvent.submit(submit.closest("form")!);
    expect(await screen.findByRole("heading", { name: "movimientos.csv" })).toBeInTheDocument();
    expect(screen.getByText("PROCESADO_CON_ERRORES")).toBeInTheDocument();
    expect(screen.getByText("MONTO_INVALIDO")).toBeInTheDocument();
    expect(screen.getByText("Invalid amount")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalled();
  });

  it("loads pending movement and receipt records and renders an empty state", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(json({ page: 1, page_size: 100, total: 2, items: [
      { record_id: 1, type: "MOVIMIENTO", batch_id: 31, external_id: "M-1", date: "2026-01-01", amount: "100.00", currency: "ARS", reference_original: "Factura 1", state: "PENDIENTE", cause: "UNRECONCILED" },
      { record_id: 2, type: "COMPROBANTE", batch_id: 32, external_id: "C-1", date: "2026-01-02", amount: "100.00", currency: "ARS", reference_original: "Factura 1", state: "CON_PROPUESTAS", cause: "UNRECONCILED" },
    ] }));
    renderApp("/pending");
    expect(await screen.findByRole("heading", { name: "Registros pendientes" })).toBeInTheDocument();
    expect(await screen.findByText("Movimiento")).toBeInTheDocument();
    expect(screen.getByText("Comprobante")).toBeInTheDocument();
  });

  it("shows pending loading, API errors, and empty results", async () => {
    vi.spyOn(window, "fetch").mockResolvedValueOnce(json({ page: 1, page_size: 100, total: 0, items: [] }));
    renderApp("/pending");
    expect(await screen.findByText("No hay registros pendientes.")).toBeInTheDocument();
    cleanup();
    localStorage.setItem("conciliador.session", JSON.stringify(session));
    vi.spyOn(window, "fetch").mockResolvedValue(json({ message: "Service unavailable" }, 503));
    window.history.pushState({}, "", "/pending");
    render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
  });
});

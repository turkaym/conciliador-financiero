import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "../src/App";
import { AuthProvider } from "../src/auth";

const session = { accessToken: "bearer-token", user: { id: 1, email: "demo@conciliador.local" }, expiresAt: Date.now() + 60_000 };
const movement = { record_id: 1, batch_id: 31, source_id: 1, source_name: "Banco Nación", external_id: "MOV-1", date: "2026-01-01", amount: "100.00", currency: "ARS", reference_original: "Factura 1" };
const receipt = { record_id: 2, batch_id: 32, source_id: 2, source_name: "ARCA", external_id: "REC-1", date: "2026-01-02", amount: "100.00", currency: "ARS", reference_original: "Factura 1" };
const summary = { id: 7, status: "GENERADA", movement_id: 1, receipt_id: 2, exact_match: true, reference_score: "1.0000", day_difference: 1, rule_version: "v1", normalizer_version: "v1", movement, receipt };
const movementCandidate = { record_id: 1, type: "MOVIMIENTO", source: { id: 1, code: "BANCO_NACION", name: "Banco Nación" }, batch_id: 31, external_id: "MOV-1", date: "2026-01-01", amount: "100.00", currency: "ARS", description: "Factura 1", state: "PENDIENTE", reconciled: false };
const receiptCandidate = { record_id: 2, type: "COMPROBANTE", source: { id: 2, code: "ARCA", name: "ARCA" }, batch_id: 32, external_id: "REC-1", date: "2026-01-02", amount: "100.00", currency: "ARS", description: "Factura 1", state: "PENDIENTE", reconciled: false };
const reconciliation = { id: 5, status: "ACTIVA", proposal_id: 7, movement, receipt, confirmed_by: 1, confirmed_at: "2026-01-03T12:00:00Z", reversal: null };

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }); }
function renderProposals() {
  localStorage.setItem("conciliador.session", JSON.stringify(session));
  window.history.pushState({}, "", "/proposals");
  return render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
}

describe("proposal workspace", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => cleanup());

  function mockApi() {
    return vi.spyOn(window, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/catalog/sources?type=MOVIMIENTO")) return json({ total: 1, items: [{ id: 1, code: "BANCO_NACION", name: "Banco Nación", type: "MOVIMIENTO" }] });
      if (url.includes("/catalog/sources?type=COMPROBANTE")) return json({ total: 1, items: [{ id: 2, code: "ARCA", name: "ARCA", type: "COMPROBANTE" }] });
      if (url.endsWith("/proposals/sync")) return json({ generated_count: 0, proposal_ids: [] });
      if (url.includes("/proposals?")) return json({ page: 1, page_size: 100, total: 1, items: [summary] });
      if (url.includes("/records?") && url.includes("type=MOVIMIENTO")) return json({ page: 1, page_size: 25, total: 1, items: [movementCandidate] });
      if (url.includes("/records?") && url.includes("type=COMPROBANTE")) return json({ page: 1, page_size: 25, total: 1, items: [receiptCandidate] });
      if (url.includes("/reconciliations/export.csv?")) return new Response("conciliacion_id,debe,haber\n5,100.00,0.00");
      if (url.includes("/reconciliations?")) return json({ page: 1, page_size: 100, total: 1, items: [reconciliation] });
      if (url.endsWith("/reconciliations/manual")) {
        expect(init?.body).toBe(JSON.stringify({ movement_id: 1, receipt_id: 2 }));
        return json({ proposal: { id: 8, status: "CONFIRMADA" }, reconciliation: { id: 6, status: "ACTIVA" } });
      }
      if (url.endsWith("/reconciliations/5/reverse")) return json({ id: 5, status: "REVERTIDA", reversal: { reason: "Asignación incorrecta" }, generated_proposals: [] });
      return json({ proposal: { id: 7, status: "CONFIRMADA" }, reconciliation: { id: 5, status: "ACTIVA" } });
    });
  }

  it("shows automatic movement and receipt side by side and confirms inline", async () => {
    const fetchMock = mockApi();
    const user = userEvent.setup();
    renderProposals();

    expect(await screen.findByText("Banco Nación · Lote #31")).toBeInTheDocument();
    expect(screen.getByText("ARCA · Lote #32")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/proposals/sync"), expect.objectContaining({ method: "POST" }));
    await user.click(screen.getByRole("button", { name: "Buscar coincidencias" }));
    expect(await screen.findByText("No se detectaron nuevas coincidencias.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Conciliar" }));

    expect(await screen.findByText(/Conciliación #5 creada/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/proposals/7/confirm"), expect.objectContaining({ method: "POST" }));
  });

  it("filters, selects and confirms a persistent manual pair", async () => {
    const fetchMock = mockApi();
    const user = userEvent.setup();
    renderProposals();
    await user.click(await screen.findByRole("tab", { name: "Manual" }));

    await user.selectOptions(screen.getByLabelText("Banco"), "1");
    await user.type(screen.getAllByLabelText("Referencia")[0], "MOV-1");
    await user.click(screen.getByRole("button", { name: "Buscar movimientos" }));
    const radios = await screen.findAllByRole("radio");
    await user.click(radios[0]);
    await user.click(radios[1]);
    await user.click(screen.getByRole("button", { name: "Confirmar conciliación manual" }));

    expect(await screen.findByText(/Conciliación manual #6 creada/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/reconciliations/manual"), expect.objectContaining({ method: "POST" }));
    await waitFor(() => {
      const persisted = JSON.parse(localStorage.getItem("conciliador.proposals.1")!);
      expect(persisted.activeTab).toBe("manual");
      expect(persisted.filters.MOVIMIENTO).toMatchObject({ sourceId: "1", reference: "MOV-1" });
    });
  });

  it("persists audit filters, downloads the extract and removes reversed reconciliations", async () => {
    const fetchMock = mockApi();
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:audit");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderProposals();
    await user.click(await screen.findByRole("tab", { name: "Auditoría" }));

    expect(await screen.findByText("Conciliación #5")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Banco"), "1");
    await user.selectOptions(screen.getByLabelText("Entidad"), "2");
    await user.selectOptions(screen.getByLabelText("Origen"), "MANUAL");
    await user.type(screen.getByLabelText("Conciliada desde"), "2026-01-01");
    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/movement_source_id=1.*receipt_source_id=2.*origin=MANUAL/), expect.anything()));
    await user.click(screen.getByRole("button", { name: "Descargar asiento CSV" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/reconciliations/export.csv?"), expect.objectContaining({ headers: { Authorization: "Bearer bearer-token" } })));
    expect(createObjectURL).toHaveBeenCalled();
    expect(anchorClick).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:audit");

    await user.type(screen.getByLabelText("Motivo para deshacer"), "Asignación incorrecta");
    await user.click(screen.getByRole("button", { name: "Deshacer conciliación" }));

    expect(await screen.findByText("Conciliación #5 revertida.")).toBeInTheDocument();
    expect(screen.queryByText("Conciliación #5")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/reconciliations/5/reverse"), expect.objectContaining({ method: "POST" }));
    await waitFor(() => {
      const persisted = JSON.parse(localStorage.getItem("conciliador.proposals.1")!);
      expect(persisted.auditFilters).toMatchObject({ movementSourceId: "1", receiptSourceId: "2", origin: "MANUAL", confirmedFrom: "2026-01-01" });
    });
  });
});

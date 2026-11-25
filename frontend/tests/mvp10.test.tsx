import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "../src/App";
import { AuthProvider } from "../src/auth";

const session = { accessToken: "bearer-token", user: { id: 1, email: "demo@conciliador.local" }, expiresAt: Date.now() + 60_000 };
const proposalDetail = {
  id: 7, status: "GENERADA", evaluation_fingerprint: "sha256:test", created_at: "2026-10-22T12:00:00Z",
  movement: { record_id: 1, batch_id: 31, date: "2026-01-01", amount: "100.00", currency: "ARS", reference_original: "Factura 1" },
  receipt: { record_id: 2, batch_id: 32, date: "2026-01-02", amount: "100.00", currency: "ARS", reference_original: "Factura 1" },
  ranking: { exact_match: true, reference_score: "1.0000", day_difference: 1, normalizer_version: "v1", rule_version: "v1", movement_normalized: "factura 1", receipt_normalized: "factura 1", movement_tokens: ["factura", "1"], receipt_tokens: ["factura", "1"] },
  origin: { type: "BATCH", batch_id: 31 }, decision: null,
};

function renderApp(path: string) {
  localStorage.setItem("conciliador.session", JSON.stringify(session));
  window.history.pushState({}, "", path);
  return render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
}

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }); }

describe("MVP-10 proposal, history, and reversal workflows", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => cleanup());

  it("loads proposals, opens detail, confirms once, and refreshes into a reconciliation", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/proposals?page")) return json({ page: 1, page_size: 25, total: 1, items: [{ id: 7, status: "GENERADA", movement_id: 1, receipt_id: 2, exact_match: true, reference_score: "1.0000", day_difference: 1, rule_version: "v1", normalizer_version: "v1" }] });
      if (url.endsWith("/proposals/7")) return json(proposalDetail);
      return json({ proposal: { id: 7, status: "CONFIRMADA", decided_by: 1, decided_at: "2026-10-22T12:01:00Z" }, reconciliation: { id: 8, status: "ACTIVA" } });
    });
    const user = userEvent.setup();
    renderApp("/proposals");
    expect(await screen.findByRole("heading", { name: "Propuestas" })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: /Propuesta #7/ }));
    expect((await screen.findAllByText("Factura 1")).length).toBe(2);
    await user.click(screen.getByRole("button", { name: "Confirmar propuesta" }));
    expect(await screen.findByText(/conciliación #8/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/proposals/7/confirm"), expect.objectContaining({ method: "POST" }));
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/proposals/7/confirm"))).toHaveLength(1);
  });

  it("rejects with a reason and prevents duplicate pending submissions", async () => {
    let resolveReject!: (value: Response) => void;
    const rejectResponse = new Promise<Response>((resolve) => { resolveReject = resolve; });
    vi.spyOn(window, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/proposals?page")) return json({ page: 1, page_size: 25, total: 1, items: [{ id: 7, status: "GENERADA", movement_id: 1, receipt_id: 2, exact_match: true, reference_score: "1.0000", day_difference: 1, rule_version: "v1", normalizer_version: "v1" }] });
      if (url.endsWith("/proposals/7")) return json(proposalDetail);
      return rejectResponse;
    });
    const user = userEvent.setup();
    renderApp("/proposals/7");
    await screen.findByRole("button", { name: "Rechazar propuesta" });
    await user.type(screen.getByLabelText("Motivo del rechazo"), "Referencia incorrecta");
    const reject = screen.getByRole("button", { name: "Rechazar propuesta" });
    await user.click(reject);
    await user.click(reject);
    expect(reject).toBeDisabled();
    resolveReject(json({ id: 7, status: "RECHAZADA", reason: "Referencia incorrecta", decided_by: 1, decided_at: "2026-10-22T12:01:00Z" }));
    expect(await screen.findByText(/Propuesta rechazada/)).toBeInTheDocument();
  });

  it("loads history and reconciliation detail, reverses with a reason, and handles stale conflicts", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/history?page")) return json({ page: 1, page_size: 25, total: 1, items: [{ id: 10, event_type: "CONFIRMADA", target: { type: "RECONCILIATION", id: 8 }, actor: 1, reason: null, data: {}, occurred_at: "2026-10-22T12:00:00Z" }] });
      if (url.endsWith("/reconciliations/8")) return json({ id: 8, status: "ACTIVA", proposal_id: 7, movement: { record_id: 1, date: "2026-01-01", amount: "100.00", currency: "ARS" }, receipt: { record_id: 2, date: "2026-01-02", amount: "100.00", currency: "ARS" }, confirmed_by: 1, confirmed_at: "2026-10-22T12:00:00Z", reversal: null });
      return json({ message: "La conciliación ya fue revertida.", code: "RECONCILIATION_NOT_ACTIVE" }, 409);
    });
    const user = userEvent.setup();
    renderApp("/history");
    await user.click(await screen.findByRole("link", { name: /Conciliación #8/ }));
    expect(await screen.findByRole("heading", { name: "Detalle de conciliación" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Motivo de la reversión"), "Ajuste manual");
    await user.click(screen.getByRole("button", { name: "Solicitar reversión" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La conciliación ya fue revertida.");
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/reconciliations/8/reverse"), expect.objectContaining({ method: "POST" }));
  });

  it("logs out on an expired API session and protects the views", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(json({ message: "Token expired" }, 401));
    renderApp("/proposals");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument());
    expect(localStorage.getItem("conciliador.session")).toBeNull();
  });
});

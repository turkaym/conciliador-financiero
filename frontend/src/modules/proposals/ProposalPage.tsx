import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  api,
  ApiError,
  type CatalogSource,
  type ConsolidatedItem,
  type ImportType,
  type ProposalDetail,
  type ProposalRecord,
  type ProposalSummary,
  type ReconciliationDetail,
} from "../../api";
import { useAuth } from "../../auth";

function useApiFailure() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  return (reason: unknown, setError: (value: string) => void) => {
    if (reason instanceof ApiError && reason.status === 401) { logout(); navigate("/login", { replace: true }); return; }
    setError(reason instanceof Error ? reason.message : "No se pudo completar la operación.");
  };
}

export function ProposalPage() {
  const { session } = useAuth();
  const storageKey = `conciliador.proposals.${session!.user.id}`;
  const [workspace, setWorkspace] = useState<ProposalWorkspace>(() => loadWorkspace(storageKey));
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [candidates, setCandidates] = useState<Record<ImportType, ConsolidatedItem[]>>({ MOVIMIENTO: [], COMPROBANTE: [] });
  const [sources, setSources] = useState<Record<ImportType, CatalogSource[]>>({ MOVIMIENTO: [], COMPROBANTE: [] });
  const [reconciliations, setReconciliations] = useState<ReconciliationDetail[]>([]);
  const [reversalReasons, setReversalReasons] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState<number | "manual" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const fail = useApiFailure();

  function patchWorkspace(patch: Partial<ProposalWorkspace>) {
    setWorkspace((current) => ({ ...current, ...patch }));
  }

  function patchFilters(type: ImportType, patch: Partial<ManualFilters>) {
    setWorkspace((current) => ({
      ...current,
      filters: { ...current.filters, [type]: { ...current.filters[type], ...patch } },
    }));
  }

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(workspace));
  }, [storageKey, workspace]);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getSources(session!.accessToken, "MOVIMIENTO"),
      api.getSources(session!.accessToken, "COMPROBANTE"),
    ]).then(([movements, receipts]) => {
      if (active) setSources({ MOVIMIENTO: movements.items, COMPROBANTE: receipts.items });
    }).catch((reason) => fail(reason, setError));
    return () => { active = false; };
  }, [session]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const request = workspace.activeTab === "automatic"
      ? api.getProposals(session!.accessToken).then((result) => { if (active) setProposals(result.items); })
      : workspace.activeTab === "audit"
        ? api.getReconciliations(session!.accessToken).then((result) => { if (active) setReconciliations(result.items); })
        : Promise.all((["MOVIMIENTO", "COMPROBANTE"] as ImportType[]).map((type) => {
          const filters = workspace.filters[type];
          return api.getConsolidatedRecords(session!.accessToken, {
            type,
            sourceId: filters.sourceId ? Number(filters.sourceId) : undefined,
            batchId: filters.batchId ? Number(filters.batchId) : undefined,
            reconciled: false,
            amount: filters.amount || undefined,
            amountTolerance: filters.amount ? filters.tolerance || "0" : undefined,
            reference: filters.reference || undefined,
            from: filters.from || undefined,
            to: filters.to || undefined,
            page: 1,
            pageSize: 25,
            sortBy: "date",
            sortOrder: "desc",
          }).then((result) => ({ type, items: result.items }));
        })).then((results) => {
          if (active) setCandidates(Object.fromEntries(results.map((result) => [result.type, result.items])) as Record<ImportType, ConsolidatedItem[]>);
        });
    request.catch((reason) => fail(reason, setError)).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session, workspace.activeTab, refresh]);

  async function confirmAutomatic(proposalId: number) {
    setSubmitting(proposalId); setError(null);
    try {
      const result = await api.confirmProposal(session!.accessToken, proposalId);
      setProposals((current) => current.filter((proposal) => proposal.id !== proposalId));
      setFeedback(`Propuesta conciliada. Conciliación #${result.reconciliation.id} creada.`);
    } catch (reason) { fail(reason, setError); } finally { setSubmitting(null); }
  }

  async function confirmManual() {
    if (!workspace.selectedMovement || !workspace.selectedReceipt) return;
    setSubmitting("manual"); setError(null);
    try {
      const result = await api.confirmManualReconciliation(session!.accessToken, workspace.selectedMovement, workspace.selectedReceipt);
      patchWorkspace({ selectedMovement: null, selectedReceipt: null });
      setFeedback(`Conciliación manual #${result.reconciliation.id} creada.`);
      setRefresh((value) => value + 1);
    } catch (reason) { fail(reason, setError); } finally { setSubmitting(null); }
  }

  async function reverse(item: ReconciliationDetail) {
    const reason = reversalReasons[item.id]?.trim();
    if (!reason) return;
    setSubmitting(item.id); setError(null);
    try {
      await api.reverseReconciliation(session!.accessToken, item.id, reason);
      setReconciliations((current) => current.map((entry) => entry.id === item.id ? { ...entry, status: "REVERTIDA", reversal: { reason, actor: session!.user.id, occurred_at: new Date().toISOString() } } : entry));
      setFeedback(`Conciliación #${item.id} revertida.`);
    } catch (reasonValue) { fail(reasonValue, setError); } finally { setSubmitting(null); }
  }

  const selectedMovement = candidates.MOVIMIENTO.find((item) => item.record_id === workspace.selectedMovement);
  const selectedReceipt = candidates.COMPROBANTE.find((item) => item.record_id === workspace.selectedReceipt);

  return <section aria-labelledby="proposals-title"><p className="eyebrow">Revisión operativa</p><h2 id="proposals-title">Propuestas</h2><p className="muted">Confirmá sugerencias automáticas, armá pares manuales o auditá conciliaciones existentes.</p>
    <div className="tabs" role="tablist" aria-label="Flujos de propuestas">
      <ProposalTab label="Automáticas" selected={workspace.activeTab === "automatic"} onClick={() => patchWorkspace({ activeTab: "automatic" })} />
      <ProposalTab label="Manual" selected={workspace.activeTab === "manual"} onClick={() => patchWorkspace({ activeTab: "manual" })} />
      <ProposalTab label="Auditoría" selected={workspace.activeTab === "audit"} onClick={() => patchWorkspace({ activeTab: "audit" })} />
    </div>
    {loading && <p className="loading" role="status">Cargando propuestas...</p>}{error && <p className="error" role="alert">{error}</p>}{feedback && <p className="success" role="status">{feedback}</p>}

    {!loading && !error && workspace.activeTab === "automatic" && <>
      {proposals.length === 0 && <p className="empty" role="status">No hay propuestas automáticas para revisar.</p>}
      <div className="proposal-list">{proposals.map((proposal) => <article className="proposal-pair" key={proposal.id}>
        <div className="proposal-pair-heading"><div><strong>Propuesta #{proposal.id}</strong><span>{proposal.exact_match ? "Coincidencia exacta" : `Referencia ${proposal.reference_score}`} · {Math.abs(proposal.day_difference)} día(s)</span></div><Link to={`/proposals/${proposal.id}`}>Ver detalle o rechazar</Link></div>
        <div className="comparison-grid"><PairRecord title="Movimiento" record={proposal.movement} /><PairRecord title="Comprobante" record={proposal.receipt} /></div>
        <button type="button" onClick={() => void confirmAutomatic(proposal.id)} disabled={submitting !== null}>Conciliar</button>
      </article>)}</div>
    </>}

    {!loading && !error && workspace.activeTab === "manual" && <>
      <div className="manual-columns">
        <CandidatePanel title="Movimientos" entityLabel="Banco" type="MOVIMIENTO" sources={sources.MOVIMIENTO} filters={workspace.filters.MOVIMIENTO} items={candidates.MOVIMIENTO} selected={workspace.selectedMovement} onFilters={(patch) => patchFilters("MOVIMIENTO", patch)} onSearch={() => setRefresh((value) => value + 1)} onSelect={(recordId) => patchWorkspace({ selectedMovement: recordId })} />
        <CandidatePanel title="Comprobantes" entityLabel="Entidad" type="COMPROBANTE" sources={sources.COMPROBANTE} filters={workspace.filters.COMPROBANTE} items={candidates.COMPROBANTE} selected={workspace.selectedReceipt} onFilters={(patch) => patchFilters("COMPROBANTE", patch)} onSearch={() => setRefresh((value) => value + 1)} onSelect={(recordId) => patchWorkspace({ selectedReceipt: recordId })} />
      </div>
      <div className="manual-confirmation"><h3>Par seleccionado</h3>
        {selectedMovement && selectedReceipt ? <><div className="comparison-grid"><CandidateSummary title="Movimiento" item={selectedMovement} /><CandidateSummary title="Comprobante" item={selectedReceipt} /></div><p className="muted">Diferencia de monto: {Math.abs(Number(selectedMovement.amount) - Number(selectedReceipt.amount)).toFixed(2)} ARS · Diferencia de fecha: {Math.abs((Date.parse(selectedMovement.date) - Date.parse(selectedReceipt.date)) / 86_400_000)} día(s).</p><button type="button" onClick={() => void confirmManual()} disabled={submitting !== null}>Confirmar conciliación manual</button></> : <p className="empty">Seleccioná un movimiento y un comprobante.</p>}
      </div>
    </>}

    {!loading && !error && workspace.activeTab === "audit" && <>
      {reconciliations.length === 0 && <p className="empty" role="status">No hay conciliaciones para auditar.</p>}
      <div className="proposal-list">{reconciliations.map((item) => <article className="proposal-pair" key={item.id}>
        <div className="proposal-pair-heading"><div><strong>Conciliación #{item.id}</strong><span>{item.status} · {new Date(item.confirmed_at).toLocaleString("es-AR")}</span></div></div>
        <div className="comparison-grid"><PairRecord title="Movimiento" record={item.movement} /><PairRecord title="Comprobante" record={item.receipt} /></div>
        {item.status === "ACTIVA" ? <div className="audit-action"><label htmlFor={`reversal-${item.id}`}>Motivo para deshacer</label><input id={`reversal-${item.id}`} value={reversalReasons[item.id] ?? ""} onChange={(event) => setReversalReasons((current) => ({ ...current, [item.id]: event.target.value }))} /><button type="button" onClick={() => void reverse(item)} disabled={submitting !== null || !reversalReasons[item.id]?.trim()}>Deshacer conciliación</button></div> : <p className="muted">Revertida: {String(item.reversal?.reason ?? "Sin motivo")}</p>}
      </article>)}</div>
    </>}
  </section>;
}

type ProposalTabName = "automatic" | "manual" | "audit";
interface ManualFilters { sourceId: string; from: string; to: string; amount: string; tolerance: string; reference: string; batchId: string }
interface ProposalWorkspace { activeTab: ProposalTabName; filters: Record<ImportType, ManualFilters>; selectedMovement: number | null; selectedReceipt: number | null }
const defaultFilters: ManualFilters = { sourceId: "", from: "", to: "", amount: "", tolerance: "0", reference: "", batchId: "" };
function defaultWorkspace(): ProposalWorkspace { return { activeTab: "automatic", filters: { MOVIMIENTO: { ...defaultFilters }, COMPROBANTE: { ...defaultFilters } }, selectedMovement: null, selectedReceipt: null }; }
function loadWorkspace(key: string): ProposalWorkspace {
  try {
    const stored = JSON.parse(localStorage.getItem(key) ?? "null") as Partial<ProposalWorkspace> | null;
    if (!stored || !["automatic", "manual", "audit"].includes(stored.activeTab ?? "")) return defaultWorkspace();
    return { ...defaultWorkspace(), ...stored, filters: { MOVIMIENTO: { ...defaultFilters, ...stored.filters?.MOVIMIENTO }, COMPROBANTE: { ...defaultFilters, ...stored.filters?.COMPROBANTE } } };
  } catch { return defaultWorkspace(); }
}
function ProposalTab({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) { return <button type="button" role="tab" aria-selected={selected} onClick={onClick}>{label}</button>; }

function PairRecord({ title, record }: { title: string; record: ProposalRecord }) {
  return <article className="pair-record"><h3>{title}</h3><strong>{record.amount} {record.currency}</strong><span>{record.date}</span><span>{record.source_name} · Lote #{record.batch_id}</span><span>{record.external_id || record.reference_original || "Sin referencia"}</span></article>;
}

function CandidateSummary({ title, item }: { title: string; item: ConsolidatedItem }) {
  return <article className="pair-record"><h3>{title}</h3><strong>{item.amount} {item.currency}</strong><span>{item.date}</span><span>{item.source.name} · Lote #{item.batch_id}</span><span>{item.external_id || item.description || "Sin referencia"}</span></article>;
}

function CandidatePanel({ title, entityLabel, type, sources, filters, items, selected, onFilters, onSearch, onSelect }: { title: string; entityLabel: string; type: ImportType; sources: CatalogSource[]; filters: ManualFilters; items: ConsolidatedItem[]; selected: number | null; onFilters: (patch: Partial<ManualFilters>) => void; onSearch: () => void; onSelect: (recordId: number) => void }) {
  const suffix = type === "MOVIMIENTO" ? "movimiento" : "comprobante";
  return <section className="candidate-panel" aria-labelledby={`candidates-${suffix}`}><h3 id={`candidates-${suffix}`}>{title}</h3>
    <div className="candidate-filters">
      <label>{entityLabel}<select value={filters.sourceId} onChange={(event) => onFilters({ sourceId: event.target.value })}><option value="">Todos</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
      <label>Desde<input type="date" value={filters.from} max={filters.to || undefined} onChange={(event) => onFilters({ from: event.target.value })} /></label>
      <label>Hasta<input type="date" value={filters.to} min={filters.from || undefined} onChange={(event) => onFilters({ to: event.target.value })} /></label>
      <label>Monto<input type="number" min="0.01" step="0.01" value={filters.amount} onChange={(event) => onFilters({ amount: event.target.value })} /></label>
      <label>Tolerancia<input type="number" min="0" step="0.01" value={filters.tolerance} onChange={(event) => onFilters({ tolerance: event.target.value })} /></label>
      <label>Referencia<input value={filters.reference} onChange={(event) => onFilters({ reference: event.target.value })} /></label>
      <label>Lote<input type="number" min="1" step="1" value={filters.batchId} onChange={(event) => onFilters({ batchId: event.target.value })} /></label>
      <button type="button" onClick={onSearch}>Buscar {suffix === "movimiento" ? "movimientos" : "comprobantes"}</button>
    </div>
    <div className="candidate-list">{items.length === 0 ? <p className="empty">Sin candidatos.</p> : items.map((item) => <label className={`candidate-row ${selected === item.record_id ? "selected" : ""}`} key={item.record_id}><input type="radio" name={`candidate-${suffix}`} checked={selected === item.record_id} onChange={() => onSelect(item.record_id)} /><span><strong>{item.amount} {item.currency}</strong><small>{item.date} · {item.source.name} · Lote #{item.batch_id}</small><small>{item.external_id || item.description || "Sin referencia"}</small></span></label>)}</div>
  </section>;
}

export function ProposalDetailPage() {
  const { proposalId } = useParams();
  const { session } = useAuth();
  const navigate = useNavigate();
  const fail = useApiFailure();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => { api.getProposal(session!.accessToken, Number(proposalId)).then(setProposal).catch((value) => fail(value, setError)).finally(() => setLoading(false)); }, [session, proposalId]);
  async function decide(action: "confirm" | "reject") {
    setSubmitting(true); setError(null);
    try {
      if (action === "confirm") { const result = await api.confirmProposal(session!.accessToken, Number(proposalId)); setFeedback(`Propuesta confirmada. Conciliación #${result.reconciliation.id} creada.`); setProposal((current) => current ? { ...current, status: "CONFIRMADA" } : current); }
      else { const result = await api.rejectProposal(session!.accessToken, Number(proposalId), reason); setFeedback(`Propuesta rechazada: ${result.reason}`); setProposal((current) => current ? { ...current, status: "RECHAZADA" } : current); }
    } catch (value) { fail(value, setError); } finally { setSubmitting(false); }
  }
  if (loading) return <p className="loading" role="status">Cargando propuesta...</p>;
  if (!proposal) return <p className="error" role="alert">No se encontró la propuesta.</p>;
  const closed = proposal.status !== "GENERADA";
  return <section aria-labelledby="proposal-title"><Link to="/proposals">← Volver a propuestas</Link><p className="eyebrow">Detalle de propuesta</p><h2 id="proposal-title">Propuesta #{proposal.id}</h2><p className="status-card">Estado: {proposal.status}</p>
    <div className="comparison-grid"><Record title="Movimiento" record={proposal.movement} /><Record title="Comprobante" record={proposal.receipt} /></div>
    <p className="muted">Coincidencia de referencia: {proposal.ranking.reference_score}. Diferencia de fechas: {proposal.ranking.day_difference} día(s).</p>
    {!closed && <div className="decision-panel"><button type="button" onClick={() => void decide("confirm")} disabled={submitting}>Confirmar propuesta</button><label htmlFor="rejection-reason">Motivo del rechazo</label><input id="rejection-reason" value={reason} onChange={(event) => setReason(event.target.value)} required /><button type="button" onClick={() => void decide("reject")} disabled={submitting || !reason.trim()}>Rechazar propuesta</button></div>}
    {feedback && <p className="success" role="status">{feedback}</p>}{error && <p className="error" role="alert">{error}</p>}
    {feedback?.includes("Conciliación #") && <button type="button" onClick={() => navigate("/history")}>Ver historial</button>}
  </section>;
}

function Record({ title, record }: { title: string; record: ProposalDetail["movement"] }) { return <article className="result-card"><h3>{title}</h3><dl><div><dt>Fecha</dt><dd>{record.date}</dd></div><div><dt>Importe</dt><dd>{record.amount} {record.currency}</dd></div><div><dt>Referencia</dt><dd>{record.reference_original || "Sin referencia"}</dd></div></dl></article>; }

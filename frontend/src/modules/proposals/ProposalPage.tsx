import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, type ProposalDetail, type ProposalSummary } from "../../api";
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
  const [items, setItems] = useState<ProposalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fail = useApiFailure();
  useEffect(() => { api.getProposals(session!.accessToken).then((result) => setItems(result.items)).catch((reason) => fail(reason, setError)).finally(() => setLoading(false)); }, [session]);
  return <section aria-labelledby="proposals-title"><p className="eyebrow">Revisión operativa</p><h2 id="proposals-title">Propuestas</h2><p className="muted">Revisá las coincidencias sugeridas antes de confirmar una conciliación.</p>
    {loading && <p className="loading" role="status">Cargando propuestas...</p>}{error && <p className="error" role="alert">{error}</p>}
    {!loading && !error && items.length === 0 && <p className="empty" role="status">No hay propuestas para revisar.</p>}
    {!loading && !error && items.length > 0 && <div className="table-wrap"><table><caption className="sr-only">Propuestas disponibles</caption><thead><tr><th>Propuesta</th><th>Coincidencia</th><th>Días</th><th>Estado</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><Link to={`/proposals/${item.id}`}>Propuesta #{item.id}</Link></td><td>{item.exact_match ? "Exacta" : "Por referencia"} ({item.reference_score})</td><td>{item.day_difference}</td><td>{item.status}</td></tr>)}</tbody></table></div>}
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

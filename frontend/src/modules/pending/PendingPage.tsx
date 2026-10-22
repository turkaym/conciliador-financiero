import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type PendingItem } from "../../api";
import { useAuth } from "../../auth";

export function PendingPage() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<PendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPending(session!.accessToken).then((result) => setItems(result.items)).catch((reason) => {
      if (reason instanceof ApiError && reason.status === 401) { logout(); navigate("/login", { replace: true }); return; }
      setError(reason instanceof Error ? reason.message : "No se pudieron cargar los pendientes.");
    }).finally(() => setLoading(false));
  }, [session, logout, navigate]);

  return <section aria-labelledby="pending-title"><p className="eyebrow">Bandeja operativa</p><h2 id="pending-title">Registros pendientes</h2><p className="muted">Movimientos y comprobantes todavía disponibles para conciliación.</p>
    {loading && <p className="loading" role="status">Cargando pendientes...</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!loading && !error && items.length === 0 && <p className="empty" role="status">No hay registros pendientes.</p>}
    {!loading && !error && items.length > 0 && <div className="table-wrap"><table><caption className="sr-only">Registros pendientes</caption><thead><tr><th>Tipo</th><th>Fecha</th><th>Importe</th><th>Referencia</th><th>Estado</th></tr></thead><tbody>{items.map((item) => <tr key={item.record_id}><td>{item.type === "MOVIMIENTO" ? "Movimiento" : "Comprobante"}</td><td>{item.date}</td><td>{item.amount} {item.currency}</td><td>{item.reference_original || item.external_id || "Sin referencia"}</td><td>{item.state}</td></tr>)}</tbody></table></div>}
  </section>;
}

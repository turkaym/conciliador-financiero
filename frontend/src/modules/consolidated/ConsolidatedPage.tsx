import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  ApiError,
  type CatalogSource,
  type ConsolidatedItem,
  type ImportType,
} from "../../api";
import { useAuth } from "../../auth";

type SortField = "date" | "amount" | "source" | "reference" | "batch" | "reconciled";
type SortOrder = "asc" | "desc";
type ReconciledFilter = "" | "true" | "false";

interface TabState {
  sourceId: string;
  from: string;
  to: string;
  reconciled: ReconciledFilter;
  page: number;
  pageSize: number;
  sortBy: SortField;
  sortOrder: SortOrder;
}

interface PersistedState {
  activeTab: ImportType;
  tabs: Record<ImportType, TabState>;
}

const defaultTabState: TabState = {
  sourceId: "",
  from: "",
  to: "",
  reconciled: "",
  page: 1,
  pageSize: 25,
  sortBy: "date",
  sortOrder: "desc",
};

function defaultState(): PersistedState {
  return {
    activeTab: "MOVIMIENTO",
    tabs: {
      MOVIMIENTO: { ...defaultTabState },
      COMPROBANTE: { ...defaultTabState },
    },
  };
}

function loadState(key: string): PersistedState {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? "null") as Partial<PersistedState> | null;
    if (!value || !value.tabs || !["MOVIMIENTO", "COMPROBANTE"].includes(value.activeTab ?? "")) {
      return defaultState();
    }
    return {
      activeTab: value.activeTab as ImportType,
      tabs: {
        MOVIMIENTO: { ...defaultTabState, ...value.tabs.MOVIMIENTO },
        COMPROBANTE: { ...defaultTabState, ...value.tabs.COMPROBANTE },
      },
    };
  } catch {
    return defaultState();
  }
}

export function ConsolidatedPage() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const storageKey = `conciliador.consolidated.${session!.user.id}`;
  const [viewState, setViewState] = useState<PersistedState>(() => loadState(storageKey));
  const [sources, setSources] = useState<Record<ImportType, CatalogSource[]>>({
    MOVIMIENTO: [],
    COMPROBANTE: [],
  });
  const [items, setItems] = useState<ConsolidatedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeTab = viewState.activeTab;
  const tabState = viewState.tabs[activeTab];

  function handleApiError(reason: unknown) {
    if (reason instanceof ApiError && reason.status === 401) {
      logout();
      navigate("/login", { replace: true });
      return;
    }
    setError(reason instanceof Error ? reason.message : "No se pudo cargar el consolidado.");
  }

  function updateTab(patch: Partial<TabState>, resetPage = false) {
    setViewState((current) => ({
      ...current,
      tabs: {
        ...current.tabs,
        [current.activeTab]: {
          ...current.tabs[current.activeTab],
          ...patch,
          ...(resetPage ? { page: 1 } : {}),
        },
      },
    }));
  }

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(viewState));
  }, [storageKey, viewState]);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getSources(session!.accessToken, "MOVIMIENTO"),
      api.getSources(session!.accessToken, "COMPROBANTE"),
    ])
      .then(([movements, receipts]) => {
        if (active) {
          setSources({ MOVIMIENTO: movements.items, COMPROBANTE: receipts.items });
        }
      })
      .catch(handleApiError);
    return () => { active = false; };
  }, [session, logout, navigate]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api.getConsolidatedRecords(session!.accessToken, {
      type: activeTab,
      sourceId: tabState.sourceId ? Number(tabState.sourceId) : undefined,
      reconciled: tabState.reconciled ? tabState.reconciled === "true" : undefined,
      from: tabState.from || undefined,
      to: tabState.to || undefined,
      page: tabState.page,
      pageSize: tabState.pageSize,
      sortBy: tabState.sortBy,
      sortOrder: tabState.sortOrder,
    })
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setTotal(result.total);
        const lastPage = Math.max(1, Math.ceil(result.total / tabState.pageSize));
        if (tabState.page > lastPage) updateTab({ page: lastPage });
      })
      .catch(handleApiError)
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [activeTab, tabState, session, logout, navigate]);

  function changeSort(sortBy: SortField) {
    updateTab({
      sortBy,
      sortOrder: tabState.sortBy === sortBy && tabState.sortOrder === "asc" ? "desc" : "asc",
    }, true);
  }

  const pageCount = Math.max(1, Math.ceil(total / tabState.pageSize));
  const entityLabel = activeTab === "MOVIMIENTO" ? "Banco" : "Entidad";

  return <section aria-labelledby="consolidated-title">
    <p className="eyebrow">Vista consolidada</p>
    <h2 id="consolidated-title">Movimientos y comprobantes</h2>
    <p className="muted">Consultá todos los registros válidos importados y su estado de conciliación.</p>

    <div className="tabs" role="tablist" aria-label="Tipo de consolidado">
      <button type="button" role="tab" aria-selected={activeTab === "MOVIMIENTO"} onClick={() => setViewState((current) => ({ ...current, activeTab: "MOVIMIENTO" }))}>Movimientos</button>
      <button type="button" role="tab" aria-selected={activeTab === "COMPROBANTE"} onClick={() => setViewState((current) => ({ ...current, activeTab: "COMPROBANTE" }))}>Comprobantes</button>
    </div>

    <div className="consolidated-filters" aria-label={`Filtros de ${activeTab === "MOVIMIENTO" ? "movimientos" : "comprobantes"}`}>
      <label>{entityLabel}
        <select value={tabState.sourceId} onChange={(event) => updateTab({ sourceId: event.target.value }, true)}>
          <option value="">Todos</option>
          {sources[activeTab].map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
        </select>
      </label>
      <label>Conciliado
        <select value={tabState.reconciled} onChange={(event) => updateTab({ reconciled: event.target.value as ReconciledFilter }, true)}>
          <option value="">Todos</option>
          <option value="true">Sí</option>
          <option value="false">No</option>
        </select>
      </label>
      <label>Desde
        <input type="date" value={tabState.from} max={tabState.to || undefined} onChange={(event) => updateTab({ from: event.target.value }, true)} />
      </label>
      <label>Hasta
        <input type="date" value={tabState.to} min={tabState.from || undefined} onChange={(event) => updateTab({ to: event.target.value }, true)} />
      </label>
      <button className="secondary-button" type="button" onClick={() => updateTab({ sourceId: "", reconciled: "", from: "", to: "" }, true)}>Limpiar filtros</button>
    </div>

    {loading && <p className="loading" role="status">Cargando consolidado...</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!loading && !error && items.length === 0 && <p className="empty" role="status">No hay registros para los filtros seleccionados.</p>}
    {!loading && !error && items.length > 0 && <div className="table-wrap consolidated-table"><table>
      <caption className="sr-only">Consolidado de {activeTab === "MOVIMIENTO" ? "movimientos" : "comprobantes"}</caption>
      <thead><tr>
        <SortableHeader label="Fecha" field="date" state={tabState} onSort={changeSort} />
        <SortableHeader label={entityLabel} field="source" state={tabState} onSort={changeSort} />
        <SortableHeader label="Referencia" field="reference" state={tabState} onSort={changeSort} />
        <th>Descripción</th>
        <SortableHeader label="Monto" field="amount" state={tabState} onSort={changeSort} />
        <th>Moneda</th>
        <SortableHeader label="Lote" field="batch" state={tabState} onSort={changeSort} />
        <SortableHeader label="Conciliado" field="reconciled" state={tabState} onSort={changeSort} />
      </tr></thead>
      <tbody>{items.map((item) => <tr key={item.record_id}>
        <td>{item.date}</td><td>{item.source.name}</td><td>{item.external_id || "—"}</td><td>{item.description || "—"}</td>
        <td>{item.amount}</td><td>{item.currency}</td><td>{item.batch_id}</td><td><span className={`reconciled-pill ${item.reconciled ? "yes" : "no"}`}>{item.reconciled ? "Sí" : "No"}</span></td>
      </tr>)}</tbody>
    </table></div>}

    <div className="pagination-bar">
      <label>Filas por página
        <select value={tabState.pageSize} onChange={(event) => updateTab({ pageSize: Number(event.target.value) }, true)}>
          {[10, 25, 50, 100].map((size) => <option key={size} value={size}>{size}</option>)}
        </select>
      </label>
      <span>Página {tabState.page} de {pageCount} · {total} registros</span>
      <div><button type="button" className="secondary-button" disabled={tabState.page <= 1} onClick={() => updateTab({ page: tabState.page - 1 })}>Anterior</button><button type="button" className="secondary-button" disabled={tabState.page >= pageCount} onClick={() => updateTab({ page: tabState.page + 1 })}>Siguiente</button></div>
    </div>
  </section>;
}

function SortableHeader({ label, field, state, onSort }: { label: string; field: SortField; state: TabState; onSort: (field: SortField) => void }) {
  const active = state.sortBy === field;
  return <th aria-sort={active ? (state.sortOrder === "asc" ? "ascending" : "descending") : "none"}>
    <button className="sort-button" type="button" onClick={() => onSort(field)}>{label}{active ? (state.sortOrder === "asc" ? " ↑" : " ↓") : ""}</button>
  </th>;
}

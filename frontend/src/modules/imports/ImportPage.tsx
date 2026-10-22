import { useEffect, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type BatchResponse, type CatalogSource, type CatalogTemplate, type ImportType, type ValidationErrorItem } from "../../api";
import { useAuth } from "../../auth";

const typeLabels: Record<ImportType, string> = { MOVIMIENTO: "Movimientos bancarios", COMPROBANTE: "Comprobantes" };

export function ImportPage() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [type, setType] = useState<ImportType>("MOVIMIENTO");
  const [sources, setSources] = useState<CatalogSource[]>([]);
  const [templates, setTemplates] = useState<CatalogTemplate[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [errors, setErrors] = useState<ValidationErrorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleApiError(reason: unknown) {
    if (reason instanceof ApiError && reason.status === 401) {
      logout();
      navigate("/login", { replace: true });
      return;
    }
    setError(reason instanceof Error ? reason.message : "No se pudo completar la operación.");
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setSources([]);
    setTemplates([]);
    setSourceId("");
    setTemplateId("");
    api.getSources(session!.accessToken, type)
      .then((result) => { if (active) setSources(result.items); })
      .catch(handleApiError)
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [type, session, logout, navigate]);

  useEffect(() => {
    if (!sourceId) return;
    let active = true;
    setTemplates([]);
    setTemplateId("");
    api.getTemplates(session!.accessToken, Number(sourceId), type)
      .then((result) => { if (active) setTemplates(result.items); })
      .catch(handleApiError);
    return () => { active = false; };
  }, [sourceId, type, session, logout, navigate]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !sourceId || !templateId) return;
    setSubmitting(true);
    setError(null);
    setBatch(null);
    setErrors([]);
    try {
      const result = await api.submitBatch(session!.accessToken, { sourceId: Number(sourceId), templateId: Number(templateId), type, file });
      setBatch(result);
      const validation = await api.getBatchErrors(session!.accessToken, result.id);
      setErrors(validation.items);
    } catch (reason) {
      handleApiError(reason);
    } finally {
      setSubmitting(false);
    }
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) { setFile(event.target.files?.[0] ?? null); }

  return <section aria-labelledby="import-title">
    <p className="eyebrow">Carga controlada</p>
    <h2 id="import-title">Importar archivos</h2>
    <p className="muted">Elegí el catálogo aprobado y enviá el CSV. La validación de negocio se ejecuta en la API.</p>
    <form className="import-form" onSubmit={handleSubmit}>
      <label htmlFor="import-type">Tipo de archivo</label>
      <select id="import-type" value={type} onChange={(event) => setType(event.target.value as ImportType)}>
        <option value="MOVIMIENTO">{typeLabels.MOVIMIENTO}</option>
        <option value="COMPROBANTE">{typeLabels.COMPROBANTE}</option>
      </select>
      <label htmlFor="source">Fuente</label>
      <select id="source" value={sourceId} onChange={(event) => setSourceId(event.target.value)} disabled={loading || sources.length === 0} required>
        <option value="">{loading ? "Cargando fuentes..." : "Seleccioná una fuente"}</option>
        {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
      </select>
      <label htmlFor="template">Plantilla</label>
      <select id="template" value={templateId} onChange={(event) => setTemplateId(event.target.value)} disabled={!sourceId || templates.length === 0} required>
        <option value="">{templates.length ? "Seleccioná una plantilla" : "Seleccioná una fuente primero"}</option>
        {templates.map((template) => <option key={template.id} value={template.id}>{template.name} v{template.version}</option>)}
      </select>
      {templates[0] && <p className="field-hint">Columnas aprobadas: {templates[0].columns.join(", ")}</p>}
      <label htmlFor="csv-file">Archivo CSV</label>
      <input id="csv-file" type="file" accept=".csv,text/csv" onChange={handleFile} required />
      <button type="submit" disabled={submitting || !file || !sourceId || !templateId}>{submitting ? "Procesando..." : "Validar archivo"}</button>
    </form>
    {error && <p className="error" role="alert">{error}</p>}
    {batch && <BatchResult batch={batch} errors={errors} />}
  </section>;
}

function BatchResult({ batch, errors }: { batch: BatchResponse; errors: ValidationErrorItem[] }) {
  return <section className="result-card" aria-labelledby="batch-result-title">
    <div className="result-heading"><div><p className="eyebrow">Resultado del lote</p><h3 id="batch-result-title">{batch.file_name}</h3></div><strong className="status-pill">{batch.status}</strong></div>
    <dl className="totals"><div><dt>Total</dt><dd>{batch.totals.total_rows}</dd></div><div><dt>Válidas</dt><dd>{batch.totals.valid_rows}</dd></div><div><dt>Inválidas</dt><dd>{batch.totals.invalid_rows}</dd></div></dl>
    {errors.length > 0 ? <div className="table-wrap"><h4>Errores de validación</h4><table><caption className="sr-only">Errores encontrados en {batch.file_name}</caption><thead><tr><th>Fila</th><th>Campo</th><th>Código</th><th>Detalle</th></tr></thead><tbody>{errors.map((item) => <tr key={item.id}><td>{item.row_number ?? "Lote"}</td><td>{item.field ?? "-"}</td><td>{item.code}</td><td>{item.message}</td></tr>)}</tbody></table></div> : <p className="success" role="status">No se encontraron errores de validación.</p>}
  </section>;
}

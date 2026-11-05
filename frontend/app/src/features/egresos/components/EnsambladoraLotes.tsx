import { useEffect, useState, useMemo } from "react";
import { useEgresosStore } from "@/store/useEgresosStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2, Layers, Landmark } from "lucide-react";
import api from "@/api/axios";
import { toast } from "react-toastify";
import { formatCurrency } from "@/lib/utils";
import type { CuentaBancaria } from "@/features/bancos/types";

interface Proveedor {
  id: number;
  razon_social: string;
}

export default function EnsambladoraLotes() {
  // 🌟 FIX CORE: Importamos 'exportarLote' para accionar la descarga automática
  const { ordenes, isLoading, fetchOrdenes, fetchLotes, exportarLote } = useEgresosStore();
  const entidadActiva = useAuthStore((state) => state.entidadActiva);

  const [provMap, setProvMap] = useState<Record<number, string>>({});
  const [cuentasBancarias, setCuentasBancarias] = useState<CuentaBancaria[]>([]);
  const [isLoadingMaestros, setIsLoadingMaestros] = useState(true);

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [cuentaSeleccionadaId, setCuentaSeleccionadaId] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const ordenesAptas = useMemo(() => {
    return ordenes.filter(o => {
      const estado = String(o.estado_orden).toUpperCase();
      return estado === 'AUTORIZADA' || estado === 'BORRADOR' || estado === 'FACTURA_ASIGNADA';
    });
  }, [ordenes]);

  useEffect(() => {
    if (!entidadActiva?.id) return;

    let isMounted = true;
    const initData = async () => {
      try {
        await fetchOrdenes(true);
        const headers = { 'x-entity-id': entidadActiva.id };

        const [resProv, resCuentas] = await Promise.all([
          api.get('/v1/pagos/proveedores', { headers }),
          api.get('/v1/bancos/cuentas', { headers })
        ]);

        if (isMounted) {
          const pMap: Record<number, string> = {};
          resProv.data.forEach((p: Proveedor) => pMap[p.id] = p.razon_social);
          setProvMap(pMap);
          setCuentasBancarias(resCuentas.data);
        }
      } catch (error) {
        console.error("Error cargando Maestros en Hub Bancario:", error);
      } finally {
        if (isMounted) setIsLoadingMaestros(false);
      }
    };
    initData();
    return () => { isMounted = false; };
  }, [fetchOrdenes, entidadActiva?.id]);

  const toggleSelection = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleAll = () => {
    if (selectedIds.size === ordenesAptas.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(ordenesAptas.map(o => o.id)));
  };

  const selectedOrders = useMemo(() => ordenesAptas.filter(o => selectedIds.has(o.id)), [ordenesAptas, selectedIds]);
  const totalAmount = useMemo(() => selectedOrders.reduce((sum, o) => sum + Number(o.monto_estimado), 0), [selectedOrders]);

  const handleEnsamblarLote = async () => {
    if (selectedIds.size === 0) return;
    if (!cuentaSeleccionadaId) return toast.warning("Debes seleccionar la cuenta.");
    if (!entidadActiva?.id) return;

    setIsSubmitting(true);
    try {
      // 🌟 FIX FASE 6: Autogeneración de Idempotency Key
      const idempotencyKey = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString() + Math.random().toString(36).substring(2);

      const res = await api.post('/v1/pagos/lotes/ensamblaje-bancario', {
        cuenta_tesoreria_id: parseInt(cuentaSeleccionadaId),
        ordenes_ids: Array.from(selectedIds)
      }, {
        headers: {
          'x-entity-id': entidadActiva.id,
          'Idempotency-Key': idempotencyKey
        }
      });

      // No disparamos "éxito" prematuro. Intentamos bajar el TXT.
      await exportarLote(res.data.id);

      toast.success("¡Lote Bancario ensamblado y archivo descargado!");
      setSelectedIds(new Set());
      setCuentaSeleccionadaId("");

    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || "Fallo crítico en la generación.");
    } finally {
      // 🌟 FIX RACE CONDITION: Pase lo que pase, refrescamos la UI
      await fetchOrdenes(true);
      await fetchLotes();
      setIsSubmitting(false);
    }
  };

  if (isLoadingMaestros && ordenes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-slate-200 bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <Layers className="h-5 w-5 text-indigo-600" /> Ensamblaje Interbanking
          </h3>
          <p className="text-sm text-slate-500">Agrupá órdenes autorizadas y descargá el archivo bancario.</p>
        </div>
        {ordenesAptas.length > 0 && (
          <button type="button" onClick={toggleAll} className="text-sm font-semibold text-indigo-600 hover:text-indigo-700">
            {selectedIds.size === ordenesAptas.length ? "Quitar selección" : "Seleccionar todas"}
          </button>
        )}
      </div>

      {ordenesAptas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center text-sm text-slate-500">
          No hay órdenes aptas para ensamblar.
        </div>
      ) : (
        <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
          {ordenesAptas.map((orden) => (
            <label key={orden.id} className="flex cursor-pointer items-center gap-3 p-4 hover:bg-slate-50">
              <input
                type="checkbox"
                checked={selectedIds.has(orden.id)}
                onChange={() => toggleSelection(orden.id)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold text-slate-800">{orden.codigo_trazabilidad}</p>
                <p className="truncate text-xs text-slate-500">{provMap[orden.proveedor_id] || `Proveedor #${orden.proveedor_id}`}</p>
              </div>
              <span className="text-sm font-bold text-slate-800">{formatCurrency(orden.monto_estimado, orden.moneda)}</span>
            </label>
          ))}
        </div>
      )}

      <div className="grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <label className="mb-1.5 flex items-center gap-1 text-xs font-bold uppercase text-slate-500">
            <Landmark className="h-4 w-4" /> Cuenta bancaria de origen
          </label>
          <select
            value={cuentaSeleccionadaId}
            onChange={(event) => setCuentaSeleccionadaId(event.target.value)}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="">Seleccionar cuenta...</option>
            {cuentasBancarias.map((cuenta) => (
              <option key={cuenta.id} value={cuenta.id}>{cuenta.banco} - {cuenta.numero_cuenta} ({cuenta.moneda})</option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={handleEnsamblarLote}
          disabled={selectedIds.size === 0 || !cuentaSeleccionadaId || isSubmitting || isLoading}
          className="inline-flex h-11 items-center justify-center rounded-md bg-indigo-600 px-5 text-sm font-bold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Generar lote ({formatCurrency(totalAmount, 'ARS')})
        </button>
      </div>
    </div>
  );
}

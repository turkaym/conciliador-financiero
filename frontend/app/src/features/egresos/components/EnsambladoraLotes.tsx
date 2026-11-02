import { useEffect, useState, useMemo } from "react";
import { useEgresosStore } from "@/store/useEgresosStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2, Layers, Landmark } from "lucide-react";
import api from "@/api/axios";
import { toast } from "react-toastify";

export default function EnsambladoraLotes() {
  // 🌟 FIX CORE: Importamos 'exportarLote' para accionar la descarga automática
  const { ordenes, isLoading, fetchOrdenes, fetchLotes, exportarLote } = useEgresosStore();
  const entidadActiva = useAuthStore((state: any) => state.entidadActiva);

  const [provMap, setProvMap] = useState<Record<number, string>>({});
  const [cuentasBancarias, setCuentasBancarias] = useState<any[]>([]);
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
          resProv.data.forEach((p: any) => pMap[p.id] = p.razon_social);
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
}
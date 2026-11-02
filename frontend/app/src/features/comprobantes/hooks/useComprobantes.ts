import api from '@/api/axios';
import { useAuthStore } from '@/store/useAuthStore';
import { extractApiError } from '@/lib/utils';
import type { Comprobante, ComprobanteCreatePayload } from '../types';
import { useState, useCallback, useEffect } from 'react';

const PAGE_SIZE = 50;

export interface ComprobanteFilters {
  clase_documento?: string;
  tipo_operacion?: string;
  estado?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  cuit_receptor?: string;
}

export const useComprobantes = () => {
  const { entidadActiva } = useAuthStore();

  const [comprobantes, setComprobantes] = useState<Comprobante[]>([]);
  const [remitosPendientes, setRemitosPendientes] = useState<Comprobante[]>([]);

  // 🌟 FIX TRAZABILIDAD: Nuevo estado para facturas asociables (Notas de Crédito/Débito)
  const [facturasAsociables, setFacturasAsociables] = useState<Comprobante[]>([]);

  const [hasMore, setHasMore] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSyncingAfip, setIsSyncingAfip] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const [cajasDisponibles, setCajasDisponibles] = useState<{id: number, nombre: string}[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [globalMessage, setGlobalMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [syncFeedback, setSyncFeedback] = useState<{ active: boolean, text: string } | null>(null);

  const showGlobalMessage = useCallback((type: 'success' | 'error', text: string) => {
    setGlobalMessage({ type, text });
    setTimeout(() => setGlobalMessage(null), 5000);
  }, []);

  const getSecureHeaders = useCallback(() => {
    if (!entidadActiva) throw new Error("No hay entidad activa en contexto");
    return { 'X-Entity-ID': entidadActiva.id.toString() };
  }, [entidadActiva]);

  const fetchComprobantes = useCallback(async (page: number = 0, filters: ComprobanteFilters = {}) => {
    if (!entidadActiva) return;

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const skip = page * PAGE_SIZE;

      const activeFilters = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v != null && v !== "" && v !== "ALL")
      );

      const response = await api.get<Comprobante[]>("/v1/comprobantes/", {
        headers: getSecureHeaders(),
        params: { skip, limit: PAGE_SIZE, ...activeFilters }
      });

      setComprobantes(prev => page === 0 ? response.data : [...prev, ...response.data]);
      setHasMore(response.data.length === PAGE_SIZE);
    } catch (error) {
      console.error("Error al cargar la lista:", error);
      showGlobalMessage('error', extractApiError(error, "Error de red al cargar los comprobantes."));
    } finally {
      setIsLoading(false);
    }
  }, [entidadActiva, getSecureHeaders, showGlobalMessage]);

  const fetchRemitosPendientes = useCallback(async (cuit?: string) => {
    if (!entidadActiva || !cuit || cuit.length < 11) {
        setRemitosPendientes([]);
        return;
    }

    try {
      const response = await api.get<Comprobante[]>("/v1/comprobantes/", {
        headers: getSecureHeaders(),
        params: { clase_documento: 'REMITO', cuit_receptor: cuit }
      });
      const pendientes = response.data.filter((c) => c.estado !== 'FACTURADO');
      setRemitosPendientes(pendientes);
    } catch (error) {
      console.error("Error al buscar remitos:", error);
    }
  }, [entidadActiva, getSecureHeaders]);

  // 🌟 FIX FASE D: Ruteo inteligente del CUIT según el flujo comercial
  const fetchFacturasParaAsociar = useCallback(async (cuit?: string, tipoOperacion: string = "VENTA") => {
    if (!entidadActiva || !cuit || cuit.length < 11) {
      setFacturasAsociables([]);
      return;
    }

    try {
      const params: any = {
        tipo_operacion: tipoOperacion,
        clase_documento: "FACTURA"
      };

      // Si es VENTA, el cliente es el receptor. Si es COMPRA, el proveedor es el emisor.
      if (tipoOperacion === "VENTA") {
        params.cuit_receptor = cuit;
      } else {
        params.cuit_emisor = cuit;
      }

      const response = await api.get<Comprobante[]>("/v1/comprobantes/", {
        headers: getSecureHeaders(),
        params
      });

      // Ordenamiento cronológico inverso (más recientes primero)
      const facturas = response.data.sort((a, b) => new Date(b.fecha_emision).getTime() - new Date(a.fecha_emision).getTime());
      setFacturasAsociables(facturas);
    } catch (error) {
      console.error("Error al buscar facturas para asociar:", error);
    }
  }, [entidadActiva, getSecureHeaders]);

  const fetchCajasB2C = useCallback(async () => {
    if (!entidadActiva) return;
    try {
      const response = await api.get<any[]>('/v1/bancos/cuentas', { headers: getSecureHeaders() });
      const cajasOperativas = response.data.filter(c => !c.is_virtual_clearing);

      setCajasDisponibles(cajasOperativas.map(c => ({
        id: c.id,
        nombre: c.banco || c.nombre || "Caja/Cuenta sin nombre"
      })));

    } catch (error) {
      console.error("Error al cargar cajas operativas:", error);
    }
  }, [entidadActiva, getSecureHeaders]);

  useEffect(() => {
    fetchCajasB2C();
  }, [fetchCajasB2C]);

  const createComprobante = async (payload: Omit<ComprobanteCreatePayload, 'entidad_id'> | any) => {
    if (!entidadActiva) return false;

    setIsSaving(true);
    setErrorMsg(null);
    try {
      const finalPayload: ComprobanteCreatePayload = {
        ...payload,
        entidad_id: entidadActiva.id
      };

      const idempotencyKey = crypto.randomUUID();

      await api.post("/v1/comprobantes/", finalPayload, {
        headers: {
          ...getSecureHeaders(),
          'Idempotency-Key': idempotencyKey
        }
      });

      showGlobalMessage('success', "Comprobante emitido e ingresado al orquestador AFIP.");
      return true;
    } catch (error: any) {
      if (error.response?.status === 409) {
        setErrorMsg("Este comprobante ya existe en la base de datos.");
      } else {
        setErrorMsg(extractApiError(error, "Error de validación matemática o de integridad."));
      }
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const deleteComprobante = async (id: number) => {
    if (!entidadActiva || deletingId) return false;
    setDeletingId(id);
    const previousComprobantes = [...comprobantes];
    setComprobantes(prev => prev.filter(c => c.id !== id));

    try {
      await api.delete(`/v1/comprobantes/${id}`, {
        headers: getSecureHeaders()
      });
      showGlobalMessage('success', "Comprobante anulado correctamente.");
      return true;
    } catch (error: any) {
      setComprobantes(previousComprobantes);
      showGlobalMessage('error', extractApiError(error, "Fallo al anular el documento (Posible bloqueo por CAE activo)."));
      return false;
    } finally {
      setDeletingId(null);
    }
  };

  const syncAfip = async (puntoVenta: number = 1, tipoCbte: number = 1, activeFilters: ComprobanteFilters = {}) => {
    if (!entidadActiva?.has_afip_credentials) return;

    setIsSyncingAfip(true);
    setSyncFeedback(null);

    try {
      await api.post('/v1/comprobantes/sync-afip',
        { punto_venta: puntoVenta, tipo_cbte: tipoCbte },
        { headers: getSecureHeaders() }
      );

      setSyncFeedback({
        active: true,
        text: "Sincronizando con AFIP en segundo plano. Buscando nuevas facturas..."
      });

      setTimeout(() => { fetchComprobantes(0, activeFilters); }, 5000);
      setTimeout(() => {
        fetchComprobantes(0, activeFilters);
        setSyncFeedback(null);
      }, 12000);

    } catch (error: any) {
      const msg = extractApiError(error, "Fallo al iniciar sincronización con AFIP.");
      setErrorMsg(msg);
    } finally {
      setIsSyncingAfip(false);
    }
  };

  const clearData = useCallback(() => {
    setComprobantes([]);
    setRemitosPendientes([]);
    setFacturasAsociables([]);
    setHasMore(true);
    setErrorMsg(null);
  }, []);

  return {
    comprobantes, remitosPendientes, facturasAsociables, isLoading, isSaving, cajasDisponibles, isSyncingAfip, deletingId, hasMore,
    errorMsg, setErrorMsg, globalMessage, syncFeedback,
    fetchComprobantes, fetchRemitosPendientes, fetchFacturasParaAsociar, createComprobante, deleteComprobante, syncAfip, clearData
  };
};
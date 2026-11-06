import { useState, useCallback } from 'react';
import api from '@/api/axios';
import { useAuthStore } from '@/store/useAuthStore';
import { extractApiError } from '@/lib/utils';

// ==========================================
// INTERFACES (Contratos DTO estrictos)
// ==========================================
export interface IncompleteInvoice {
  // 🌟 FIX POLIMORFISMO: El ID ahora es string para soportar CBT-X u OP-Y
  id: string;
  numero_formateado: string;
  razon_social: string;
  fecha: string | null;
  monto: number;
  moneda: string;
  clase_documento: string | null;
}

export interface IncompleteMovement {
  id: number;
  fecha: string | null;
  referencia: string;
  concepto: string;
  monto: number;
  moneda: string;
}

export interface ConciliacionStatusResponse {
  tenant: string;
  entidad_id: number;
  summary: { matched_count: number; ar_pending: number; ap_pending: number; };
  pendings: {
    ar: { invoices: IncompleteInvoice[]; bank_movements: IncompleteMovement[]; };
    ap: { invoices: IncompleteInvoice[]; bank_movements: IncompleteMovement[]; };
  };
}

export interface HistoryComprobanteDetail {
  id: string;
  numero: number;
  numero_formateado: string;
  monto_total: number;
  monto_aplicado: number;
}

export interface HistoryMovementDetail {
  id: number;
  concepto: string;
  monto_total: number;
  monto_aplicado: number;
}

export interface HistoryMatch {
  id: number;
  asiento_id: number | null;
  score: number;
  metodo: string;
  comprobantes: HistoryComprobanteDetail[];
  movimientos: HistoryMovementDetail[];
}

export interface HistoryResponse {
  items: HistoryMatch[];
  total: number;
  limit: number;
  offset: number;
}

export interface RetencionSufridaPayload {
  tipo_impuesto: string;
  jurisdiccion: string;
  monto_impuesto: number;
  numero_certificado: string;
}

interface ManualMatchPayload {
  comprobantes_ids: string[];
  movimientos_ids: number[];
  ajustes_fiscales?: RetencionSufridaPayload[];
}

// ==========================================
// HOOK ZUSTAND-AWARE
// ==========================================
export const useConciliacion = () => {
  const [data, setData] = useState<ConciliacionStatusResponse | null>(null);
  const [historyData, setHistoryData] = useState<HistoryResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { entidadActiva, tenant_id } = useAuthStore();

  const fetchStatus = useCallback(async (limit: number = 100, offset: number = 0) => {
    if (!entidadActiva?.id || !tenant_id) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get<ConciliacionStatusResponse>(`/v1/matching/status/${tenant_id}`, {
        params: { entidad_id: entidadActiva.id, limit, offset }
      });
      setData(response.data);
    } catch (err) {
      setError(extractApiError(err, 'Error al obtener el estado de conciliación.'));
    } finally {
      setIsLoading(false);
    }
  }, [entidadActiva?.id, tenant_id]);

  const fetchHistory = useCallback(async (limit: number = 50, offset: number = 0) => {
    if (!entidadActiva?.id || !tenant_id) return;
    setIsLoading(true);
    try {
      const response = await api.get<HistoryResponse>(`/v1/matching/history/${tenant_id}`, {
        params: { entidad_id: entidadActiva.id, limit, offset }
      });
      setHistoryData(response.data);
    } catch (err) {
      setError(extractApiError(err, 'Error al obtener el historial forense.'));
    } finally {
      setIsLoading(false);
    }
  }, [entidadActiva?.id, tenant_id]);

  const triggerAutoMatch = async () => {
    if (!entidadActiva?.id || !tenant_id) return;
    setIsProcessing(true);
    setError(null);
    try {
      await api.post(`/v1/matching/run/${tenant_id}?entidad_id=${entidadActiva.id}`);
      await fetchStatus();
      await fetchHistory();
      return true;
    } catch (err) {
      setError(extractApiError(err, 'Falló la ejecución del motor automático.'));
      return false;
    } finally {
      setIsProcessing(false);
    }
  };

  // 🌟 FIX POLIMORFISMO: comprobantesIds viaja obligatoriamente como array de strings al backend
  const triggerManualMatch = async (
    movimientosIds: number[],
    comprobantesIds: string[],
    ajustesFiscales?: RetencionSufridaPayload[]
  ) => {
    if (!tenant_id) return false;
    setIsProcessing(true);
    setError(null);
    try {
      const payload: ManualMatchPayload = {
        comprobantes_ids: comprobantesIds,
        movimientos_ids: movimientosIds
      };

      if (ajustesFiscales && ajustesFiscales.length > 0) {
        payload.ajustes_fiscales = ajustesFiscales;
      }

      await api.post(`/v1/matching/manual-match/${tenant_id}`, payload);
      await fetchStatus();
      await fetchHistory();
      return true;
    } catch (err) {
      setError(extractApiError(err, 'Falló la vinculación manual. Verifique la matemática del ajuste fiscal o recargue los saldos.'));
      return false;
    } finally {
      setIsProcessing(false);
    }
  };

  const triggerUnmatch = async (matchId: number) => {
    if (!tenant_id) return false;
    setIsProcessing(true);
    setError(null);
    try {
      await api.post(`/v1/matching/unmatch/${tenant_id}?match_id=${matchId}`);
      await fetchStatus();
      await fetchHistory();
      return true;
    } catch (err) {
      setError(extractApiError(err, 'No se pudo deshacer la conciliación. Puede estar bloqueada fiscalmente.'));
      return false;
    } finally {
      setIsProcessing(false);
    }
  };

  return {
    data,
    historyData,
    isLoading,
    isProcessing,
    error,
    fetchStatus,
    fetchHistory,
    triggerAutoMatch,
    triggerManualMatch,
    triggerUnmatch
  };
};

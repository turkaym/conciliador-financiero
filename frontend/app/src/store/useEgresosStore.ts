import { create } from 'zustand';
import api from '@/api/axios';
import { useAuthStore } from '@/store/useAuthStore';
import { toast } from "react-toastify";

// 🌟 FIX CORE: Interface para blindar las respuestas de error de Axios
export interface ApiError {
  response?: {
    data?: {
      detail?: string;
    } | Blob;
    headers?: Record<string, string>;
  };
  message?: string;
}

// ==========================================
// INTERFACES LOGÍSTICAS
// ==========================================
export interface OrdenPago {
  id: number;
  codigo_trazabilidad: string;
  concepto_id: number;
  proveedor_id: number;
  monto_estimado: number;
  moneda: string;
  estado_orden: string;
  requiere_comprobante_fiscal: boolean;
  comprobante_interno_url?: string;
  created_at: string;
  creado_por_id?: string;
}

// ==========================================
// INTERFACES FINANCIERAS (DRILL-DOWN FSM)
// ==========================================
export interface LoteOrdenPagoMin {
  id: number;
  codigo_trazabilidad: string;
  monto_estimado: number;
  creado_por_id?: string;
  comprobante_interno_url?: string;
}

export interface LotePagoDetalle {
  id: number;
  orden_pago_id?: number;
  monto_asignado_ars: number;
  orden_pago?: LoteOrdenPagoMin;
}

export interface LotePago {
  id: number;
  codigo_lote: string;
  monto_total_lote: number;
  estado_lote: string;
  detalles?: LotePagoDetalle[];
}

export interface LotePagoDetalleCreate {
  orden_pago_id?: number | null;
  comprobante_id?: number | null;
  monto_asignado_moneda_origen: number;
  monto_asignado_ars: number;
  tipo_cambio_aplicado?: number;
}

export interface LotePagoCreate {
  moneda_pago: string;
  monto_total_lote: number;
  detalles: LotePagoDetalleCreate[];
}

// ==========================================
// STORE STATE
// ==========================================
interface EgresosState {
  ordenes: OrdenPago[];
  lotes: LotePago[];
  isLoading: boolean;

  filtros: {
    fecha_inicio: string;
    fecha_fin: string;
    q: string;
    codigo_trazabilidad: string;
    concepto_id: string;
    monto_min: string;
    monto_max: string;
  };

  paginacion: {
    page: number;
    limit: number;
    hasMore: boolean;
  };

  setOrdenes: (ordenes: OrdenPago[]) => void;
  setLotes: (lotes: LotePago[]) => void;
  setLoading: (status: boolean) => void;
  setFiltros: (filtros: Partial<EgresosState['filtros']>) => void;
  setPaginacion: (page: number) => void;
  destroyState: () => void;

  fetchOrdenes: (resetPage?: boolean) => Promise<void>;
  fetchLotes: () => Promise<void>;
  crearLote: (payload: LotePagoCreate) => Promise<LotePago>;
  solicitarAutorizacionLote: (lote_id: number) => Promise<void>;
  autorizarLote: (lote_id: number, cuenta_bancaria_id: number) => Promise<void>;
  exportarLote: (lote_id: number) => Promise<void>;
  liquidarOrdenIndividual: (orden_id: number, cuenta_tesoreria_id: number) => Promise<void>;
}

const today = new Date();
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(today.getDate() - 30);

const defaultFiltros = {
  fecha_inicio: thirtyDaysAgo.toISOString().split('T')[0],
  fecha_fin: today.toISOString().split('T')[0],
  q: '',
  codigo_trazabilidad: '',
  concepto_id: '',
  monto_min: '',
  monto_max: '',
};

const defaultPaginacion = {
  page: 1,
  limit: 50,
  hasMore: true
};

export const useEgresosStore = create<EgresosState>((set, get) => ({
  ordenes: [],
  lotes: [],
  isLoading: false,
  filtros: defaultFiltros,
  paginacion: defaultPaginacion,

  setOrdenes: (ordenes) => set({ ordenes }),
  setLotes: (lotes) => set({ lotes }),
  setLoading: (status) => set({ isLoading: status }),

  setFiltros: (nuevosFiltros) => set((state) => ({
    filtros: { ...state.filtros, ...nuevosFiltros },
    paginacion: { ...state.paginacion, page: 1, hasMore: true }
  })),

  setPaginacion: (page) => set((state) => ({
    paginacion: { ...state.paginacion, page }
  })),

  destroyState: () => set({
    ordenes: [],
    lotes: [],
    isLoading: false,
    filtros: defaultFiltros,
    paginacion: defaultPaginacion
  }),

  fetchOrdenes: async (resetPage = false) => {
    if (get().isLoading) return;

    const entidadId = useAuthStore.getState().entidadActiva?.id;
    if (!entidadId) return;

    const { filtros, paginacion } = get();
    const currentPage = resetPage ? 1 : paginacion.page;

    const fInicio = new Date(filtros.fecha_inicio);
    const fFin = new Date(filtros.fecha_fin);
    const diffTime = Math.abs(fFin.getTime() - fInicio.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays > 180) {
      alert("🛑 El rango máximo de consulta permitido es de 180 días.");
      return;
    }

    if (resetPage) set({ paginacion: { ...paginacion, page: 1 } });
    set({ isLoading: true });

    try {
      const params = new URLSearchParams();
      Object.entries(filtros).forEach(([key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          params.append(key, String(value));
        }
      });

      const offset = (currentPage - 1) * paginacion.limit;
      params.append('offset', String(offset));
      params.append('limit', String(paginacion.limit));

      const { data } = await api.get('/v1/pagos/ordenes', {
        params,
        headers: { 'x-entity-id': String(entidadId) }
      });

      set((state) => ({
        ordenes: data,
        paginacion: {
          ...state.paginacion,
          hasMore: data.length === state.paginacion.limit
        }
      }));

    } catch (error: unknown) {
      console.error("Error en búsqueda de órdenes:", error);
    } finally {
      set({ isLoading: false });
    }
  },

  fetchLotes: async () => {
    if (get().isLoading) return;
    const entidadId = useAuthStore.getState().entidadActiva?.id;
    if (!entidadId) return;

    set({ isLoading: true });
    try {
      const { data } = await api.get('/v1/pagos/lotes', { headers: { 'x-entity-id': String(entidadId) } });
      set({ lotes: data });
    } catch (error: unknown) {
      console.error("Error al obtener lotes:", error);
    } finally {
      set({ isLoading: false });
    }
  },

  crearLote: async (payload: LotePagoCreate) => {
    if (get().isLoading) throw new Error("Operación en progreso");
    const entidadId = useAuthStore.getState().entidadActiva?.id;
    if (!entidadId) throw new Error("No hay entidad activa");

    set({ isLoading: true });
    try {
      const { data } = await api.post('/v1/pagos/lotes', payload, { headers: { 'x-entity-id': String(entidadId) } });
      const idsEnsamblados = payload.detalles.map(d => d.orden_pago_id);

      set((state) => ({
        lotes: [data, ...state.lotes],
        ordenes: state.ordenes.filter(o => !idsEnsamblados.includes(o.id))
      }));
      return data;
    } catch (error: unknown) {
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  solicitarAutorizacionLote: async (lote_id: number) => {
    if (get().isLoading) return;
    const entidadId = useAuthStore.getState().entidadActiva?.id;
    if (!entidadId) return;

    set({ isLoading: true });
    try {
      const { data } = await api.patch(`/v1/pagos/lotes/${lote_id}/solicitar-autorizacion`, {}, { headers: { 'x-entity-id': String(entidadId) } });
      set((state) => ({
        lotes: state.lotes.map(l => l.id === lote_id ? data : l)
      }));
    } catch (error: unknown) {
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  autorizarLote: async (lote_id: number, cuenta_bancaria_id: number) => {
    if (get().isLoading) return;
    const entidadId = useAuthStore.getState().entidadActiva?.id;
    if (!entidadId) return;

    set({ isLoading: true });
    try {
      const { data } = await api.patch(
        `/v1/pagos/lotes/${lote_id}/autorizar`,
        { cuenta_bancaria_id },
        { headers: { 'x-entity-id': String(entidadId) } }
      );

      set((state) => ({
        lotes: state.lotes.map(l => l.id === lote_id ? data : l)
      }));
    } catch (error: unknown) {
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  exportarLote: async (loteId: number) => {
    try {
      const state = useAuthStore.getState();
      const response = await api.get(`/v1/pagos/lotes/${loteId}/exportar-interbanking`, {
        responseType: 'blob',
        headers: { 'x-entity-id': String(state.entidadActiva?.id) }
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      const contentDisposition = response.headers['content-disposition'];
      let fileName = `interbanking_lote_${loteId}.txt`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match.length === 2) fileName = match[1];
      }

      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (error: unknown) {
      const err = error as ApiError;
      let errorMessage = "Fallo al intentar generar el archivo bancario.";

      if (err.response && err.response.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          errorMessage = json.detail || errorMessage;
        } catch (e) {
          // Fallback silencioso al mensaje por defecto
        }
      } else if (err.response?.data && typeof err.response.data === 'object' && 'detail' in err.response.data) {
        errorMessage = String(err.response.data.detail);
      }

      throw new Error(errorMessage);
    }
  },

  liquidarOrdenIndividual: async (orden_id: number, cuenta_tesoreria_id: number) => {
    const state = get();
    if (state.isLoading) return;

    const entidadId = useAuthStore.getState().entidadActiva?.id;
    if (!entidadId) return;

    set({ isLoading: true });
    try {
      const idempotencyKey = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString() + Math.random().toString(36).substring(2);

      await api.post(
        `/v1/pagos/ordenes/${orden_id}/liquidar-individual`,
        { cuenta_tesoreria_id },
        {
          headers: {
            'x-entity-id': String(entidadId),
            'Idempotency-Key': idempotencyKey
          }
        }
      );
      setTimeout(() => state.fetchOrdenes(false), 100);
    } catch (error: unknown) {
      throw error;
    } finally {
      set({ isLoading: false });
    }
  }
}));
import { fetchWithBackoff } from '@/lib/resilience';
import { useState, useCallback, useRef, useEffect } from 'react';
import api from '@/api/axios';
import { useAuthStore } from '@/store/useAuthStore';
import { extractApiError } from '@/lib/utils';
import type {
  CuentaBancaria,
  CuentaBancariaCreate,
  MovimientoBancario,
  MovimientoBancarioCreate
} from '../types';

const PAGE_SIZE = 50;

interface MovimientosPaginadosResponse {
  items: MovimientoBancario[];
  total_count: number;
  page: number;
  has_more: boolean;
}

export interface XRayColumn {
  index: number;
  header: string;
  inferred_type: string;
  sample_values: string[];
}

export interface XRayResponse {
  status: string;
  start_row: number;
  inferred_mapping: Record<string, number>;
  columns: XRayColumn[];
}

// 🌟 FIX TIPADO (PASO 8): Contrato estricto para eventos SSE
export interface TaskProgressEvent {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'PROCESSING' | 'SUCCESS' | 'FAILURE' | 'REVOKED';
  progress?: number;
  message?: string;
  result?: TaskProgressData;
  error?: string;
  meta?: TaskProgressData;
}

interface TaskProgressData {
  progress?: number;
  message?: string;
  insertados?: number;
}

interface PresignedUploadResponse {
  upload_url: string;
  form_fields: Record<string, string>;
  object_name: string;
}

interface ResolutionPayload {
  registro_id: number;
  tipo_registro: "MOVIMIENTO" | "SOLICITUD";
  accion: 'aprobar' | 'rechazar';
  motivo_rechazo?: string;
}

export const useBancos = () => {
  const [proveedoresClearing, setProveedoresClearing] = useState<{id: number, razon_social: string, cuit: string}[]>([]);
  const [cuentas, setCuentas] = useState<CuentaBancaria[]>([]);
  const [isLoadingCuentas, setIsLoadingCuentas] = useState<boolean>(false);
  const [errorCuentas, setErrorCuentas] = useState<string | null>(null);

  const [movimientos, setMovimientos] = useState<MovimientoBancario[]>([]);
  const [isLoadingMovs, setIsLoadingMovs] = useState<boolean>(false);
  const [hasMoreMovs, setHasMoreMovs] = useState<boolean>(true);
  const [totalMovimientos, setTotalMovimientos] = useState<number>(0);
  const [errorMovs, setErrorMovs] = useState<string | null>(null);

  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [globalMessage, setGlobalMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const entidadActiva = useAuthStore((state) => state.entidadActiva);
  const entidadId = entidadActiva?.id;

  const eventSourceRef = useRef<EventSource | null>(null);
  const retryTimeoutsRef = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

  const scheduleTimeout = useCallback((callback: () => void, delay: number) => {
    const timeoutId = setTimeout(() => {
      retryTimeoutsRef.current.delete(timeoutId);
      callback();
    }, delay);
    retryTimeoutsRef.current.add(timeoutId);
  }, []);

  useEffect(() => {
    const retryTimeouts = retryTimeoutsRef.current;
    return () => {
      retryTimeouts.forEach(clearTimeout);
      retryTimeouts.clear();
      if (eventSourceRef.current) {
         eventSourceRef.current.close();
         eventSourceRef.current = null;
      }
    };
  }, [entidadId]);

  const showMessage = useCallback((text: string, type: 'success' | 'error') => {
    setGlobalMessage({ text, type });
    setTimeout(() => setGlobalMessage(null), 5000);
  }, []);

  // ==========================================
  // MÉTODOS: MOVIMIENTOS Y CONCILIACIÓN
  // ==========================================
  const fetchMovimientos = useCallback(async (cuentaId: string | number, page: number = 0) => {
    if (!entidadId || !cuentaId) return;
    setIsLoadingMovs(true);
    setErrorMovs(null);
    try {
      const skip = page * PAGE_SIZE;
      const response = await api.get<MovimientosPaginadosResponse>('/v1/bancos/movimientos', {
        params: { cuenta_id: cuentaId, skip, limit: PAGE_SIZE }
      });
      const { items, total_count, has_more } = response.data;
      setMovimientos((prev) => page === 0 ? items : [...prev, ...items]);
      setHasMoreMovs(has_more);
      setTotalMovimientos(total_count);
    } catch (err) {
      setErrorMovs(extractApiError(err, 'Error de red al obtener movimientos.'));
    } finally {
      setIsLoadingMovs(false);
    }
  }, [entidadId]);

  // ==========================================
  // FLUJO ENTERPRISE: PRE-SIGNED POST & SSE
  // ==========================================

  // 🌟 FIX TIPADO: Desechamos el 'any'
  const lastProgressUpdateRef = useRef(0);
  const handleProgressUpdate = useCallback((data: { progress: number; message: string }, cuentaId?: string | number) => {
    const now = Date.now();
    if (now - lastProgressUpdateRef.current < 250) return;
    lastProgressUpdateRef.current = now;

    if (cuentaId && data.progress !== undefined) {
      setCuentas(prev => prev.map(c =>
        c.id === Number(cuentaId)
          ? { ...c, progress: data.progress, status_msg: data.message }
          : c
      ));
    }
  }, []);

  // 🌟 FIX REDES (PASO 8): Exponential Backoff inyectado nativamente
  const listenToTaskStream = useCallback(async (taskId: string, cuentaId?: string | number, retryCount: number = 0) => {
    setIsPolling(true);
    try {
      const authRes = await api.post<{ sse_token: string }>('/v1/auth/sse-token');
      const sseToken = authRes.data.sse_token;
      const baseURL = api.defaults.baseURL || "http://localhost:80";

      if (eventSourceRef.current) {
          eventSourceRef.current.close();
      }

      eventSourceRef.current = new EventSource(`${baseURL}/v1/status/stream/${taskId}?token=${sseToken}`);

      eventSourceRef.current.onmessage = (event) => {
        if (event.data === "heartbeat") return;
        const data: TaskProgressEvent = JSON.parse(event.data); // Tipado estricto

        if (data.status === 'PROCESSING' || data.status === 'PENDING') {
          const currentProgress = data.progress ?? data.result?.progress ?? data.meta?.progress ?? 0;
          const currentMessage = data.message ?? data.result?.message ?? data.meta?.message ?? 'Procesando registros...';

          handleProgressUpdate({ progress: currentProgress, message: currentMessage }, cuentaId);
          return;
        }

        if (data.status === 'SUCCESS') {
          if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
          }
          setIsPolling(false);

          if (cuentaId) {
            setCuentas(prev => prev.map(c => c.id === Number(cuentaId) ? { ...c, is_syncing: false, progress: 100 } : c));
            fetchMovimientos(cuentaId, 0);
          }

          const insertados = data.result?.insertados;
          showMessage(insertados !== undefined
            ? `Proceso completado: ${insertados} registros normalizados.`
            : `⚠️ La tarea finalizó pero no devolvió resultados.`,
            insertados !== undefined ? "success" : "error");

        } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          setIsPolling(false);

          if (cuentaId) {
            setCuentas(prev => prev.map(c => c.id === Number(cuentaId) ? { ...c, is_syncing: false, progress: 0 } : c));
          }

          const rawError = data.error || 'Fallo inesperado durante el procesamiento';
          if (data.status === 'REVOKED' || rawError.toLowerCase().includes('terminated')) {
             setErrorMovs(`🛑 Cancelado: El proceso fue detenido y revertido.`);
          } else {
             showMessage(rawError, "error");
             setErrorMovs(`⚠️ Rechazado: ${rawError}`);
          }
        }
      };

      eventSourceRef.current.onerror = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }

        // 🌟 Lógica de Reconexión Exponencial (Máx 4 intentos)
        if (retryCount < 4) {
           const timeout = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s, 8s
           console.warn(`⚠️ Microcorte SSE. Reconectando en ${timeout}ms... (Intento ${retryCount + 1}/4)`);
           scheduleTimeout(() => listenToTaskStream(taskId, cuentaId, retryCount + 1), timeout);
        } else {
           setIsPolling(false);
           showMessage('Se perdió la conexión en vivo con el servidor. Revisá la tabla más tarde.', 'error');
        }
      };

    } catch (error) {
      setIsPolling(false);
      showMessage('No se pudo establecer el canal seguro (SSE).', 'error');
    }
  }, [showMessage, fetchMovimientos, handleProgressUpdate, scheduleTimeout]);

  const uploadToVault = async (file: File): Promise<string> => {
      // 🌟 FIX 1: Defensa contra archivos muertos (0 bytes) creados manualmente por el SO.
      if (file.size === 0) {
          throw new Error("El archivo que intentás subir está vacío (0 bytes). Verificá que contenga los datos del extracto.");
      }

      const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      const presignedRes = await api.get<PresignedUploadResponse>(`/v1/ingesta/upload-url`, {
        params: { modulo: "bancos", extension: ext }
      });
      const { upload_url, form_fields, object_name } = presignedRes.data;

      let minioRes;

      const isPutUrl = upload_url.includes("X-Amz-Signature") || !form_fields || Object.keys(form_fields).length === 0;

      if (isPutUrl) {
          minioRes = await fetch(upload_url, {
              method: "PUT",
              body: file,
              headers: { "Content-Type": file.type || "application/octet-stream" }
          });
      } else {
          const minioFormData = new FormData();

          minioFormData.append("key", object_name);

          // 🌟 FIX 2: Añadimos SOLO los campos estrictamente autorizados por la política criptográfica del Backend.
          Object.entries(form_fields).forEach(([k, v]) => {
            if (k !== "key") {
                minioFormData.append(k, v as string);
            }
          });

          // REGLA DE ORO S3/MINIO: El archivo físico debe ser estrictamente el ÚLTIMO campo adjuntado.
          minioFormData.append("file", file, file.name);

          minioRes = await fetch(upload_url, { method: "POST", body: minioFormData });
      }

      if (!minioRes.ok) {
          const errorText = await minioRes.text();
          console.error("🔥 [STORAGE_ERROR] Falla en la bóveda:", errorText);
          throw new Error("El archivo fue rechazado por el servidor de almacenamiento. Verificá que el formato sea válido.");
      }

      return object_name;
  };

  const procesarPreVuelo = async (file: File): Promise<{ objectName: string, analysis: XRayResponse } | null> => {
    if (!entidadId) return null;
    setIsLoadingMovs(true);
    setErrorMovs(null);
    try {
      const objectName = await uploadToVault(file);
      const res = await api.get<XRayResponse>('/v1/bancos/ingesta/analyze-format', {
          params: { object_name: objectName }
      });
      return { objectName, analysis: res.data };
    } catch(err: unknown) {
      setErrorMovs(`⚠️ ${extractApiError(err, 'Fallo al analizar la estructura del archivo.')}`);
      return null;
    } finally {
      setIsLoadingMovs(false);
    }
  };

  const confirmarIngesta = async (
    cuentaId: string | number,
    cuentaContableId: number,
    objectName: string,
    parserCode: string,
    columnMapping?: Record<string, number>
  ) => {
    setIsLoadingMovs(true);
    setErrorMovs(null);
    try {
      const confirmRes = await fetchWithBackoff(`/v1/bancos/cuentas/${cuentaId}/importar/confirm`, {
        cuenta_contable_id: cuentaContableId, // 🌟 Viaja al backend
        object_name: objectName,
        parser_code: parserCode,
        column_mapping: columnMapping
      });

      if (confirmRes && (confirmRes.status === 202 || confirmRes.data?.task_id)) {
        const taskId = confirmRes.data.task_id;
        showMessage("Archivo encolado. Escuchando eventos en vivo...", "success");

        listenToTaskStream(taskId, cuentaId);

        setCuentas(prev => prev.map(c => c.id === Number(cuentaId) ? {
          ...c, is_syncing: true, last_task_id: taskId
        } : c));

        scheduleTimeout(() => {
          if (eventSourceRef.current && eventSourceRef.current.readyState !== 2) fetchCuentas();
        }, 15000);
        return true;
      }
      throw new Error("Respuesta inválida del orquestador.");
    } catch (err: unknown) {
      setErrorMovs(`⚠️ ${extractApiError(err, 'Fallo crítico al confirmar el procesamiento.')}`);
      return false;
    } finally {
      setIsLoadingMovs(false);
    }
  };

  const uploadExtracto = async (cuentaId: string | number, cuentaContableId: number, parserCode: string, file: File) => {
      try {
          setIsLoadingMovs(true);
          setErrorMovs(null);
          const objectName = await uploadToVault(file);
          return await confirmarIngesta(cuentaId, cuentaContableId, objectName, parserCode);
       } catch (err: unknown) {
          setErrorMovs(`⚠️ ${extractApiError(err, 'Fallo crítico al subir el archivo.')}`);
          setIsLoadingMovs(false);
          return false;
      }
  };

  // ==========================================
  // MÉTODOS: CUENTAS Y CREACIÓN
  // ==========================================
  const fetchCuentas = useCallback(async (onLoaded?: (loadedCuentas: CuentaBancaria[]) => void) => {
    if (!entidadId) return;
    setIsLoadingCuentas(true);
    setErrorCuentas(null);

    // 🌟 FIX STATE BLEEDING: Vaciamos la memoria instantáneamente
    // para evitar que la UI intente leer datos de la empresa anterior.
    setCuentas([]);

    try {
      const response = await api.get<CuentaBancaria[]>('/v1/bancos/cuentas');
      setCuentas(response.data);
      onLoaded?.(response.data);

      const cuentaEnProceso = response.data.find(c => c.is_syncing === true && c.last_task_id);
      if (cuentaEnProceso) {
        listenToTaskStream(cuentaEnProceso.last_task_id!, cuentaEnProceso.id);
      }
    } catch (err) {
      setErrorCuentas(extractApiError(err, 'Error de conexión al obtener cuentas.'));
    } finally {
      setIsLoadingCuentas(false);
    }
  }, [entidadId, listenToTaskStream]);

  const fetchProveedoresClearing = useCallback(async () => {
    if (!entidadId) return;
    try {
      const response = await api.get<Array<{ id: number; razon_social: string; cuit: string }>>('/v1/bancos/proveedores-clearing'); // 🌟 FIX: URL corregida para coincidir con el backend
      setProveedoresClearing(response.data);
    } catch (err) {
      console.error("No se pudieron cargar los proveedores", err);
    }
  }, [entidadId]);

  const createCuenta = async (data: CuentaBancariaCreate) => {
    if (!entidadId) {
      setErrorCuentas('No hay una entidad activa para realizar esta acción.');
      return false;
    }
    setIsLoadingCuentas(true);
    setErrorCuentas(null);
    try {
      const payload = { ...data, saldo_actual: data.saldo_actual.toString() };
      const response = await api.post<CuentaBancaria>('/v1/bancos/cuentas', payload);
      setCuentas((prev) => [...prev, response.data]);
      showMessage("Cuenta bancaria vinculada exitosamente.", "success");
      return true;
    } catch (err) {
      setErrorCuentas(extractApiError(err, 'Error al crear la cuenta bancaria.'));
      return false;
    } finally {
      setIsLoadingCuentas(false);
    }
  };

  const createMovimiento = async (data: MovimientoBancarioCreate) => {
    if (!entidadId) return false;
    setIsLoadingMovs(true);
    setErrorMovs(null);
    try {
      const payload = { ...data, monto: data.monto.toString() };
      const response = await api.post<MovimientoBancario>('/v1/bancos/movimientos', payload);
      setMovimientos((prev) => [response.data, ...prev]);
      showMessage("Movimiento registrado con éxito.", "success");
      return true;
    } catch (err) {
      setErrorMovs(`⚠️ ${extractApiError(err, 'Ocurrió un error inesperado al registrar.')}`);
      return false;
    } finally {
      setIsLoadingMovs(false);
    }
  };

  // ==========================================
  // 🛡️ FASE 7.8 & 2.2: RESOLUCIÓN 4-OJOS CON JSON TYPE-SAFE
  // ==========================================
  const resolverAprobacion = async (
    registroId: number,
    tipoRegistro: "MOVIMIENTO" | "SOLICITUD",
    accion: 'aprobar' | 'rechazar',
    motivoRechazo?: string
  ) => {
    if (!entidadId) return false;
    setIsLoadingMovs(true);
    setErrorMovs(null);
    try {
      // 🌟 FIX ARQUITECTURA: Generación de llave única en el cliente para evitar el Doble-Tap
      const idempotencyKey = crypto.randomUUID();

      // 🌟 FIX FASE 2.2: Payload estructurado estricto (Desacople de URL)
      const payload: ResolutionPayload = {
        registro_id: registroId,
        tipo_registro: tipoRegistro,
        accion
      };

      // 🌟 FIX FEEDBACK LOOP: Si es rechazo, inyectamos el motivo obligatorio
      if (accion === 'rechazar' && motivoRechazo) {
          payload.motivo_rechazo = motivoRechazo;
      }

      // 🌟 FIX FASE 2.2: Endpoint genérico, el enrutamiento ahora es interno en el Backend vía JSON
      await api.post(`/v1/bancos/movimientos/resolucion`,
        payload,
        { headers: { 'Idempotency-Key': idempotencyKey } }
      );

      showMessage(`Transacción ${accion === 'aprobar' ? 'aprobada' : 'rechazada'} exitosamente.`, "success");
      return true;
    } catch (err: unknown) {
      setErrorMovs(`⚠️ ${extractApiError(err, 'Fallo al procesar la autorización.')}`);
      return false;
    } finally {
      setIsLoadingMovs(false);
    }
  };

  // 🌟 FIX ESTADO (PASO 7): Condicionar apagado a éxito transaccional
  const cancelarIngesta = useCallback(async (cuentaId: string | number) => {
    const cuenta = cuentas.find(c => c.id === Number(cuentaId));

    if (!cuenta || !cuenta.last_task_id) {
       console.error("No se encontró una tarea en curso para esta cuenta.");
       return false;
    }

    try {
      // 1. Esperamos confirmación estricta del backend primero
      await api.delete(`/v1/bancos/cuentas/importar/cancel/${cuenta.last_task_id}`);

      // 2. Solo si el backend responde 200 OK, procedemos a apagar la UI
      if (eventSourceRef.current) {
         eventSourceRef.current.close();
         eventSourceRef.current = null;
      }
      setIsPolling(false);

      setCuentas(prev => prev.map(c => c.id === Number(cuentaId) ? { ...c, is_syncing: false } : c));
      showMessage("Ingesta abortada. Cambios revertidos por seguridad.", "success");
      return true;
    } catch (err: unknown) {
      // Si falla la red, el spinner sigue girando para no desincronizar la UI con la realidad
      showMessage(extractApiError(err, 'No se pudo abortar el proceso en el motor.'), "error");
      return false;
    }
  }, [cuentas, showMessage]);

  const clearMovimientos = useCallback(() => {
    setMovimientos([]);
    setHasMoreMovs(true);
    setTotalMovimientos(0);
  }, []);

  return {
    cuentas, movimientos, isLoadingCuentas, isLoadingMovs, isPolling, hasMoreMovs, errorCuentas, errorMovs, globalMessage, totalMovimientos, proveedoresClearing,
    fetchCuentas, createCuenta, fetchMovimientos, createMovimiento, clearMovimientos, setErrorCuentas, setErrorMovs,
    uploadExtracto, cancelarIngesta,
    procesarPreVuelo, confirmarIngesta, resolverAprobacion, fetchProveedoresClearing
  };
};

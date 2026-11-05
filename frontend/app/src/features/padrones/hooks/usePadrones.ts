import { useState, useCallback, useRef, useEffect } from 'react';
import api from '@/api/axios';
import { extractApiError } from '@/lib/utils';
import { fetchWithBackoff } from '@/lib/resilience';
import { useAuthStore } from '@/store/useAuthStore';
import type { AxiosResponse } from 'axios';

export interface HistorialIngesta {
  id: number;
  jurisdiccion: string;
  periodo: string;
  nombre_archivo: string;
  estado: 'PROCESANDO' | 'EXITO' | 'FALLO';
  registros_insertados: number;
  mensaje_error?: string;
  tarea_celery_id: string | null;
  iniciado_el: string;
  finalizado_el: string | null;
}

interface HistorialIngestaResponse extends Omit<HistorialIngesta, 'mensaje_error'> {
  mensaje_error: string | null;
}

export interface PadronFiscalInfo {
  cuit: string;
  jurisdiccion: string;
  periodo: string;
  alicuota_retencion: number;
  alicuota_percepcion: number;
  coeficiente_riesgo: number | null;
}

interface MultipartPart {
  part_number: number;
  object_name: string;
  upload_url: string;
}

interface MultipartUploadPlan {
  final_object_name: string;
  parts: MultipartPart[];
}

interface PresignedUpload {
  upload_url: string;
  form_fields: Record<string, string>;
  object_name: string;
}

interface IngestionAccepted {
  status: 'ACCEPTED';
  task_id: string;
  message: string;
}

interface SseTokenResponse {
  sse_token: string;
}

interface RegistryTaskStatus {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'PROCESSING' | 'SUCCESS' | 'FAILURE' | 'REVOKED';
  progress?: number;
  message?: string;
  result?: { status: 'success'; insertados: number };
  error?: string;
}

const asyncPool = async <Item, Result>(poolLimit: number, array: Item[], iteratorFn: (item: Item) => Promise<Result>) => {
  const ret: Promise<Result>[] = [];
  const executing = new Set<Promise<Result>>();
  for (const item of array) {
    const p = Promise.resolve().then(() => iteratorFn(item));
    ret.push(p);
    if (poolLimit <= array.length) {
      executing.add(p);
      void p.finally(() => executing.delete(p));
      if (executing.size >= poolLimit) {
        await Promise.race(executing);
      }
    }
  }
  return Promise.all(ret);
};

export const usePadrones = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [globalMessage, setGlobalMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [statusMsg, setStatusMsg] = useState<string>('');

  const [historial, setHistorial] = useState<HistorialIngesta[]>([]);
  const [isFetchingHistorial, setIsFetchingHistorial] = useState<boolean>(false);
  const [searchResult, setSearchResult] = useState<PadronFiscalInfo | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  const entidadActiva = useAuthStore(state => state.entidadActiva);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
         eventSourceRef.current.close();
         eventSourceRef.current = null;
      }
    };
  }, []);

  const showMessage = useCallback((text: string, type: 'success' | 'error') => {
    setGlobalMessage({ text, type });
    setTimeout(() => setGlobalMessage(null), 5000);
  }, []);

  const fetchHistorial = useCallback(async () => {
    if (!entidadActiva?.id) return;
    setIsFetchingHistorial(true);
    try {
      const res = await api.get<HistorialIngestaResponse[]>('/v1/padrones/historial', {
        headers: { 'x-entity-id': entidadActiva.id }
      });
      setHistorial(res.data.map((row) => ({
        ...row,
        mensaje_error: row.mensaje_error ?? undefined
      })));
    } catch {
      showMessage("No se pudo sincronizar el monitor de ingestas.", "error");
    } finally {
      setIsFetchingHistorial(false);
    }
  }, [entidadActiva?.id, showMessage]);

  const buscarCuit = async (cuit: string, jurisdiccion: string, periodo: string) => {
    if (!entidadActiva?.id) return;
    setIsSearching(true);
    setSearchResult(null);
    try {
      const res = await api.get<PadronFiscalInfo>(`/v1/padrones/consulta/${cuit}`, {
        params: { jurisdiccion, periodo },
        headers: { 'x-entity-id': entidadActiva.id }
      });
      setSearchResult(res.data);
      showMessage("Registro fiscal encontrado en base de datos.", "success");
    } catch (err: unknown) {
      const msg = extractApiError(err, "CUIT no encontrado en el padrón especificado.");
      showMessage(msg, "error");
    } finally {
      setIsSearching(false);
    }
  };

  const lastProgressUpdateRef = useRef(0);
  const handleProgressUpdate = useCallback((data: RegistryTaskStatus) => {
    const now = Date.now();
    if (now - lastProgressUpdateRef.current < 250) return;
    lastProgressUpdateRef.current = now;
    setProgress(data.progress || 0);
    setStatusMsg(data.message || 'Procesando...');
  }, []);

  const listenToTaskStream = useCallback(async (taskId: string) => {
    setIsPolling(true);
    setErrorMsg(null);
    setProgress(100);
    setStatusMsg('Completado');

    try {
      const authRes = await api.post<SseTokenResponse>('/v1/auth/sse-token');
      const sseToken = authRes.data.sse_token;
      const baseURL = api.defaults.baseURL || "http://localhost:80";

      if (eventSourceRef.current) {
          eventSourceRef.current.close();
      }

      eventSourceRef.current = new EventSource(`${baseURL}/v1/status/stream/${taskId}?token=${sseToken}`);

      eventSourceRef.current.onmessage = (event) => {
        if (event.data === "heartbeat") return;
        const data: RegistryTaskStatus = JSON.parse(event.data);

        if (data.status === 'PROCESSING') {
          handleProgressUpdate(data);
          return;
        }

        if (data.status === 'SUCCESS') {
          if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
          }
          setIsPolling(false);
          const insertados = data.result?.insertados;
          showMessage(`Proceso completado: ${insertados} registros normalizados.`, "success");
          fetchHistorial();

        } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
          if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
          }
          setProgress(0);
          setStatusMsg('');
          setIsPolling(false);
          const mensajeError = data.error || 'Fallo inesperado';

          if (data.status === 'REVOKED' || mensajeError.toLowerCase().includes('terminated')) {
             setErrorMsg(`🛑 Cancelado: El proceso fue detenido.`);
          } else {
             setErrorMsg(`⚠️ Rechazado: ${mensajeError}`);
             showMessage(mensajeError, "error");
          }
          fetchHistorial();
        }
      };

      eventSourceRef.current.onerror = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        setIsPolling(false);
        showMessage('Interrupción de red en el seguimiento en vivo.', 'error');
        fetchHistorial();
      };

    } catch (error) {
      setIsPolling(false);
      showMessage('Error de conexión SSE.', 'error');
    }
  }, [showMessage, handleProgressUpdate, fetchHistorial]);

  const uploadPadron = async (jurisdiccion: string, periodo: string, file: File): Promise<boolean> => {
    if (!entidadActiva?.id) return false;
    setIsLoading(true);
    setErrorMsg(null);

    const periodoNormalizado = periodo.replace("-", "");

    try {
      const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      const fileSizeMB = file.size / (1024 * 1024);
      const isMultipart = fileSizeMB > 20;

      if (isMultipart) {
        const CHUNK_SIZE = 5 * 1024 * 1024;
        const totalParts = Math.ceil(file.size / CHUNK_SIZE);

        showMessage(`Preparando subida de archivo masivo (${fileSizeMB.toFixed(1)}MB en ${totalParts} partes)...`, "success");

        const initRes: AxiosResponse<MultipartUploadPlan> = await fetchWithBackoff(`/v1/ingesta/multipart/urls`, {
           modulo: "padrones",
           extension: ext,
           total_parts: totalParts
        });

        const { final_object_name, parts } = initRes.data;

        let partsUploaded = 0;
        const uploadTask = async (partInfo: MultipartPart) => {
           const start = (partInfo.part_number - 1) * CHUNK_SIZE;
           const end = Math.min(start + CHUNK_SIZE, file.size);
           const chunk = new Blob([file.slice(start, end)]);

           const res = await fetch(partInfo.upload_url, {
             method: 'PUT',
             body: chunk
           });

           if (!res.ok) {
               throw new Error(`Fallo al subir el fragmento ${partInfo.part_number}`);
           }

           partsUploaded++;
           return partInfo.object_name;
        };

        const sourceObjects = await asyncPool(3, parts, uploadTask);

        showMessage("Ensamblando partes en el servidor...", "success");

        const confirmRes: AxiosResponse<IngestionAccepted> = await fetchWithBackoff(`/v1/padrones/ingesta/multipart/confirm`, {
           jurisdiccion: jurisdiccion,
           periodo: periodoNormalizado,
           final_object_name: final_object_name,
           source_objects: sourceObjects
         }, { headers: { 'x-entity-id': entidadActiva.id } });

        if (confirmRes && (confirmRes.status === 202 || confirmRes.data?.task_id)) {
           showMessage("Padrón consolidado y encolado.", "success");
           fetchHistorial();
           listenToTaskStream(confirmRes.data.task_id);
           return true;
        }

        throw new Error("Respuesta inusual del orquestador multipart.");

      } else {
        const presignedRes = await api.get<PresignedUpload>(`/v1/ingesta/upload-url`, {
          params: { modulo: "padrones", extension: ext }
        });
        const { upload_url, form_fields, object_name } = presignedRes.data;

        const minioFormData = new FormData();
        minioFormData.append("key", object_name);
        Object.entries(form_fields).forEach(([k, v]) => {
          if (k !== "key") minioFormData.append(k, v as string);
        });
        minioFormData.append("file", file);

        const minioRes = await fetch(upload_url, { method: "POST", body: minioFormData });

        if (!minioRes.ok) {
            throw new Error("El Vault de seguridad rechazó el archivo.");
        }

        const confirmFormData = new FormData();
        confirmFormData.append("object_name", object_name);
        confirmFormData.append("jurisdiccion", jurisdiccion);
        confirmFormData.append("periodo", periodoNormalizado);

        const confirmRes = await api.post<IngestionAccepted>(`/v1/padrones/ingesta/confirm`, confirmFormData, {
          headers: {
            'x-entity-id': entidadActiva.id,
            'Content-Type': 'multipart/form-data'
          }
        });

        if (confirmRes && (confirmRes.status === 202 || confirmRes.data?.task_id)) {
          showMessage("Padrón encolado. Iniciando normalización...", "success");
          fetchHistorial();
          listenToTaskStream(confirmRes.data.task_id);
          return true;
        }

        throw new Error(`Respuesta inusual del orquestador: HTTP ${confirmRes?.status}`);
      }

    } catch (err: unknown) {
      setErrorMsg(`⚠️ ${extractApiError(err, 'Fallo crítico al subir el padrón.')}`);
      fetchHistorial();
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    isPolling,
    progress,
    statusMsg,
    errorMsg,
    globalMessage,
    historial,
    isFetchingHistorial,
    searchResult,
    isSearching,
    setErrorMsg,
    uploadPadron,
    fetchHistorial,
    buscarCuit
  };
};

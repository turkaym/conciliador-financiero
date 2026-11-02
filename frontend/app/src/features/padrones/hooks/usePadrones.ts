import { useState, useCallback, useRef, useEffect } from 'react';
import api from '@/api/axios';
import { extractApiError } from '@/lib/utils';
import { fetchWithBackoff, throttle } from '@/lib/resilience';
import { useAuthStore } from '@/store/useAuthStore';

export interface HistorialIngesta {
  id: number;
  jurisdiccion: string;
  periodo: string;
  nombre_archivo: string;
  estado: string;
  registros_insertados: number;
  mensaje_error?: string;
  tarea_celery_id?: string;
  iniciado_el: string;
  finalizado_el?: string;
}

export interface PadronFiscalInfo {
  cuit: string;
  jurisdiccion: string;
  periodo: string;
  alicuota_retencion: number;
  alicuota_percepcion: number;
  coeficiente_riesgo?: number;
}

const asyncPool = async (poolLimit: number, array: any[], iteratorFn: (item: any) => Promise<any>) => {
  const ret: Promise<any>[] = [];
  const executing: Promise<any>[] = [];
  for (const item of array) {
    const p = Promise.resolve().then(() => iteratorFn(item));
    ret.push(p);
    if (poolLimit <= array.length) {
      const e: Promise<any> = p.then(() => executing.splice(executing.indexOf(e), 1));
      executing.push(e);
      if (executing.length >= poolLimit) {
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
      const res = await api.get('/v1/padrones/historial', {
        headers: { 'x-entity-id': entidadActiva.id }
      });
      setHistorial(res.data);
    } catch (err: any) {
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
      const res = await api.get(`/v1/padrones/consulta/${cuit}`, {
        params: { jurisdiccion, periodo },
        headers: { 'x-entity-id': entidadActiva.id }
      });
      setSearchResult(res.data);
      showMessage("Registro fiscal encontrado en base de datos.", "success");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "CUIT no encontrado en el padrón especificado.";
      showMessage(msg, "error");
    } finally {
      setIsSearching(false);
    }
  };

  const handleProgressUpdate = useCallback(
    throttle((data: any) => {
        setProgress(data.progress || 0);
        setStatusMsg(data.message || 'Procesando...');
    }, 250),
    []
  );

  const listenToTaskStream = useCallback(async (taskId: string) => {
    setIsPolling(true);
    setErrorMsg(null);
    setProgress(100);
    setStatusMsg('Completado');

    try {
      const authRes = await api.post('/v1/auth/sse-token');
      const sseToken = authRes.data.sse_token;
      const baseURL = api.defaults.baseURL || "http://localhost:80";

      if (eventSourceRef.current) {
          eventSourceRef.current.close();
      }

      eventSourceRef.current = new EventSource(`${baseURL}/v1/status/stream/${taskId}?token=${sseToken}`);

      eventSourceRef.current.onmessage = (event) => {
        if (event.data === "heartbeat") return;
        const data = JSON.parse(event.data);

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

        const initRes = await fetchWithBackoff(`/v1/ingesta/multipart/urls`, {
           modulo: "padrones",
           extension: ext,
           total_parts: totalParts
        });

        const { final_object_name, parts } = initRes.data;

        let partsUploaded = 0;
        const uploadTask = async (partInfo: any) => {
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

        const confirmRes = await fetchWithBackoff(`/v1/padrones/ingesta/multipart/confirm`, {
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
        const presignedRes = await api.get(`/v1/ingesta/upload-url`, {
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

        const confirmRes = await api.post(`/v1/padrones/ingesta/confirm`, confirmFormData, {
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

    } catch (err: any) {
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

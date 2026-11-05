import axios from 'axios';
import { useAuthStore } from '@/store/useAuthStore';
import { toast } from 'react-toastify';

// Generador robusto de UUID (Fallback para entornos locales sin HTTPS)
const generateIdempotencyKey = () => {
  if (typeof window !== 'undefined' && window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return 'idemp-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 10);
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isPaywallTriggered = false;

// ==========================================
// INTERCEPTOR DE PETICIONES
// ==========================================
api.interceptors.request.use(
  (config) => {
    const state = useAuthStore.getState();
    const token = state.token;
    const entidadActiva = state.entidadActiva;

    // Aseguramos la existencia de headers para prevenir fallos en versiones de Axios
    if (!config.headers) config.headers = {} as any;

    if (token) {
      if (config.headers.set) config.headers.set('Authorization', `Bearer ${token}`);
      else config.headers['Authorization'] = `Bearer ${token}`;
    }

    if (entidadActiva?.id) {
      if (config.headers.set) config.headers.set('X-Entity-ID', entidadActiva.id.toString());
      else config.headers['X-Entity-ID'] = entidadActiva.id.toString();
    }

    // 🌟 FIX ARQUITECTÓNICO 360: IDEMPOTENCIA GLOBAL
    // Inyectamos la clave a nivel infraestructura para TODAS las mutaciones.
    // Esto evita duplicaciones en cualquier parte del sistema y elimina parches manuales.
    const method = (config.method || '').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const hasIdemp = config.headers.has ? config.headers.has('Idempotency-Key') : !!config.headers['Idempotency-Key'];
      if (!hasIdemp) {
        const uuid = generateIdempotencyKey();
        if (config.headers.set) config.headers.set('Idempotency-Key', uuid);
        else config.headers['Idempotency-Key'] = uuid;
      }
    }

    if (config.data instanceof FormData) {
      if (config.headers.delete) config.headers.delete('Content-Type');
      else delete config.headers['Content-Type'];
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// ==========================================
// INTERCEPTOR DE RESPUESTAS
// ==========================================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const originalRequest = error.config;

    if (error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) {
      console.error("⏳ [Axios] El servidor tardó demasiado en responder o la red se cayó.");
      toast.error("⏳ Error de Red: El servidor tardó demasiado en responder.");
      return Promise.reject(error);
    }

    if (!error.response) {
      toast.error("🌐 Error Crítico: No se pudo contactar al servidor.");
      return Promise.reject(error);
    }

    const isAuthRoute = originalRequest.url?.includes('/auth/');
    const status = error.response.status;

    const displayDetail = typeof error.response.data?.detail === 'string'
      ? error.response.data.detail
      : "Ocurrió un error inesperado al procesar la solicitud.";
    const detailLower = displayDetail.toLowerCase();

    const isQuotaLimitReached = status === 403 && (
      detailLower.includes('límite de plan') ||
      detailLower.includes('limite de plan') ||
      detailLower.includes('plan alcanzado')
    );

    if (isQuotaLimitReached) {
      if (!isPaywallTriggered) {
        isPaywallTriggered = true;
        console.warn("🛡️ [Gobernanza] Límite de plan alcanzado. Desplegando Paywall de Upselling...");
        useAuthStore.getState().openPaywall();
        setTimeout(() => { isPaywallTriggered = false; }, 1000);
      }
      return Promise.reject(error);
    }

    if (status === 402) {
      console.warn("🛑 [Paywall] Suscripción inactiva. Levantando el Muro de Vidrio...");
      useAuthStore.getState().setDataLocked(true);
      return Promise.reject(error);
    }

    const isSessionKilled =
      status === 401 ||
      (status === 403 && (detailLower.includes('inactivo') || detailLower.includes('suspendid')));

    if (isSessionKilled && !isAuthRoute) {
      console.warn("🚨 Sesión terminada por el servidor o inválida. Purgando estado global...");
      toast.info("🔒 Tu sesión ha expirado o es inválida.");
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }

    switch (status) {
      case 422:
        toast.error(`⚠️ Bloqueo de Validación: ${displayDetail}`, { autoClose: 8000 });
        break;
      case 409:
        toast.warning(`⚠️ Conflicto: ${displayDetail}`);
        break;
      case 400:
        toast.warning(`🚫 Operación Inválida: ${displayDetail}`);
        break;
      case 403:
        if (!isQuotaLimitReached && !isSessionKilled) {
          toast.error(`🛑 Acceso Denegado: Permisos insuficientes.`);
        }
        break;
      default:
        if (status >= 500) {
          toast.error(`💥 Error Interno del Servidor: ${displayDetail}`);
        }
    }

    return Promise.reject(error);
  }
);

export default api;
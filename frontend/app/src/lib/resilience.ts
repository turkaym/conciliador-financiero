import api from '@/api/axios';
import axios, { type AxiosRequestConfig } from 'axios';

/**
 * 📡 [OFFLINE-FIRST] Exponential Backoff
 * Blindaje para reintentar peticiones ante cortes de red.
 */
export const fetchWithBackoff = async (url: string, payload: unknown, config?: AxiosRequestConfig, maxRetries = 3) => {
  let retries = 0;
  while (retries < maxRetries) {
    try {
      return await api.post(url, payload, config);
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response) throw error; // Error de servidor (4xx, 500), no reintentamos.
      retries++;
      if (retries >= maxRetries) throw new Error("Conexión inestable. El servidor no respondió.");
      const waitTime = Math.pow(2, retries - 1) * 1000;
      console.warn(`📡 Reintentando en ${waitTime}ms... (${retries}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }
  throw new Error("Conexión inestable. El servidor no respondió.");
};

/**
 * ⚡ [PERFORMANCE] Throttle (Estrangulador)
 * Limita la ejecución de una función para no saturar el Main Thread.
 * Ideal para eventos SSE de progreso que llegan muy rápido.
 */
export function throttle<TThis, TArgs extends unknown[]>(fn: (this: TThis, ...args: TArgs) => void, limit: number) {
  let inThrottle: boolean;
  return function(this: TThis, ...args: TArgs) {
    if (!inThrottle) {
      fn.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * 🏃 [ULTRA-LOW LATENCY] Animación por Frame
 * Ejecuta una actualización visual en el próximo frame disponible del navegador (60fps).
 * Evita el DOM Thrashing al actualizar barras de progreso.
 */
export const requestVisualUpdate = (callback: () => void) => {
  requestAnimationFrame(() => {
    callback();
  });
};

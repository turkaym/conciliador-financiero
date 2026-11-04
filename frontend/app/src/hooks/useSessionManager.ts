import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/store/useAuthStore';
import api from '@/api/axios';

const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutos de inactividad máxima
const REFRESH_INTERVAL_MS = 14 * 60 * 1000; // Renovar a los 14 min
const LOCK_KEY = 'auth_refresh_lock'; // 🌟 FIX: Llave para el candado multi-pestaña

export function useSessionManager() {
  const { token, logout, setAuth } = useAuthStore();
  const lastActivity = useRef<number | null>(null);

  useEffect(() => {
    if (!token) {
      lastActivity.current = null;
      return;
    }

    if (lastActivity.current === null) {
      lastActivity.current = Date.now();
    }

    // 1. RASTREADOR DE ACTIVIDAD
    const updateActivity = () => {
      lastActivity.current = Date.now();
    };

    const events = ['mousemove', 'keydown', 'mousedown', 'touchstart', 'scroll'];
    events.forEach(event => window.addEventListener(event, updateActivity, { passive: true }));

    // 2. EL GUARDIA: Revisa la inactividad cada 60 segundos
    const idleCheckInterval = setInterval(() => {
      const now = Date.now();
      if (now - (lastActivity.current ?? now) >= IDLE_TIMEOUT_MS) {
        if (import.meta.env.DEV) {
          console.warn("🔒 Sesión expirada por inactividad. Cerrando bóveda.");
        }
        logout();
      }
    }, 60000);

    // 3. EL NEGOCIADOR (Blindado contra multi-pestañas)
    const refreshInterval = setInterval(async () => {
      const now = Date.now();
      const isUserActive = (now - (lastActivity.current ?? now)) < IDLE_TIMEOUT_MS;

      if (!isUserActive) return;

      // 🌟 FIX CONDICIÓN DE CARRERA: Bloqueo distribuido
      const lockValue = localStorage.getItem(LOCK_KEY);
      const lastRefresh = lockValue ? parseInt(lockValue, 10) : 0;

      // Si otra pestaña tomó el candado y renovó el token en los últimos 30 segundos, abortamos
      if (now - lastRefresh < 30000) {
        if (import.meta.env.DEV) {
          console.log("🔄 [Sesión] Otra pestaña ya renovó el token. Omitiendo petición duplicada.");
        }
        return;
      }

      // Tomamos el candado (Lock)
      localStorage.setItem(LOCK_KEY, now.toString());

      try {
        const { data } = await api.post('/v1/auth/refresh');
        setAuth(data.access_token, data.tenant_id, data.user, data.features);
      } catch (error) {
        logout();
      }
    }, REFRESH_INTERVAL_MS);

    // 🌟 FIX UX MULTI-VENTANA: Sincronización de logout
    const handleStorageChange = (e: StorageEvent) => {
      // Si la bóveda de Zustand fue limpiada desde otra pestaña, cerramos sesión acá también
      if (e.key === 'auth-storage' && !e.newValue) {
        logout();
      }
    };
    window.addEventListener('storage', handleStorageChange);

    // Limpieza al desmontar
    return () => {
      events.forEach(event => window.removeEventListener(event, updateActivity));
      clearInterval(idleCheckInterval);
      clearInterval(refreshInterval);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [token, logout, setAuth]);
}

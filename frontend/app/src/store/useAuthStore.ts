import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Entidad {
  id: number;
  cuit: string;
  nombre_fantasia: string;
  razon_social: string;
  condicion_fiscal: "RESPONSABLE_INSCRIPTO" | "MONOTRIBUTO" | "EXENTO" | "CONSUMIDOR_FINAL" | "NO_CATEGORIZADO";
  has_afip_credentials: boolean;
  afip_cert_expiration: string | null;
  afip_last_sync_at: string | null;
}

export interface User {
  id: string;
  email: string;
  role: string;
  tenant_id: string;
  account_status: string;
  permissions?: string[];
}

// 🌟 FIX DEUDA TÉCNICA: Tipado estricto para Features, erradicando 'any'
export interface TenantFeatures {
  plan?: string;
  max_entidades?: number;
  max_operadores?: number;
  max_transacciones?: number;
  [key: string]: unknown;
}

export interface AuthState {
  token: string | null;
  tenant_id: string | null;
  user: User | null;
  features: TenantFeatures;
  entidadActiva: Entidad | null;

  isPaywallOpen: boolean;

  subscription_status: string;
  isDataLocked: boolean;

  setAuth: (token: string, tenant_id: string, user: User, features: TenantFeatures) => void;
  setEntidadActiva: (entidad: Entidad | null) => void;
  openPaywall: () => void;
  closePaywall: () => void;
  setDataLocked: (locked: boolean) => void;
  setSubscriptionStatus: (status: string) => void;
  logout: () => void;

  hasPermission: (permission: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      tenant_id: null,
      user: null,
      features: {},
      entidadActiva: null,
      isPaywallOpen: false,

      subscription_status: 'trialing',
      isDataLocked: false,

      setAuth: (token, tenant_id, user, features) =>
        set({ token, tenant_id, user, features: features || {} }),

      setEntidadActiva: (entidad) =>
        set({ entidadActiva: entidad }),

      openPaywall: () => set({ isPaywallOpen: true }),
      closePaywall: () => set({ isPaywallOpen: false }),

      setDataLocked: (locked) => set({ isDataLocked: locked }),
      setSubscriptionStatus: (status) => set({ subscription_status: status }),

      hasPermission: (permission: string) => {
        const user = get().user;
        if (!user || !user.permissions) return false;
        return user.permissions.includes(permission);
      },

      logout: () => {
        set({
          token: null,
          tenant_id: null,
          user: null,
          features: {},
          entidadActiva: null,
          isPaywallOpen: false,
          subscription_status: 'trialing',
          isDataLocked: false
        });
        localStorage.removeItem('auth-storage');
      },
    }),
    {
      name: 'auth-storage'
    }
  )
);

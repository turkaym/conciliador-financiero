import { useState, useCallback } from 'react';
import api from '@/api/axios';

export interface Miembro {
  id: number;
  user_id: string; // Email
  rol: string;
  is_active: boolean;
}

export interface Entidad {
  id: number;
  razon_social: string;
}

export const useEquipo = () => {
  const [miembros, setMiembros] = useState<Miembro[]>([]);
  const [entidades, setEntidades] = useState<Entidad[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchEquipo = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(`/v1/equipo/`);
      setMiembros(response.data);
    } catch (error) {
      console.error("Error cargando equipo", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEntidades = useCallback(async (tenantSchema: string) => {
    try {
      const response = await api.get(`/v1/entidades/${tenantSchema}`);
      setEntidades(response.data);
    } catch (error) {
      console.error("Error cargando entidades", error);
    }
  }, []);

  const invitarMiembro = async (email: string, rol: string, entidad_id: number) => {
    const response = await api.post(`/v1/equipo/`, { email, rol, entidad_id });
    await fetchEquipo();
    return response.data;
  };

  const actualizarMiembro = async (email: string, data: { rol?: string; is_active?: boolean }) => {
    await api.patch(`/v1/equipo/${email}`, data);
    await fetchEquipo();
  };

  const eliminarMiembro = async (email: string) => {
    await api.delete(`/v1/equipo/${email}`);
    await fetchEquipo();
  };

  return { miembros, entidades, loading, fetchEquipo, fetchEntidades, invitarMiembro, actualizarMiembro, eliminarMiembro };
};
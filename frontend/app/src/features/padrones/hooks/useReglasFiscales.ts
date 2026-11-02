import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import api from '@/api/axios';

export interface ReglaImpuesto {
  id?: number;
  tipo_impuesto: string;
  jurisdiccion: string;
  codigo_regimen_afip: number;
  alicuota_defecto: number;
  monto_minimo_sujeto: number;
  aplica_padron: boolean;
  is_active: boolean;
}

export function useReglasFiscales() {
  const [reglas, setReglas] = useState<ReglaImpuesto[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReglas = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/v1/fiscal/reglas');
      setReglas(response.data);
    } catch (error) {
      toast.error('Error al cargar la matriz impositiva.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createRegla = async (payload: Omit<ReglaImpuesto, 'id' | 'is_active'>) => {
    try {
      await api.post('/v1/fiscal/reglas', payload);
      toast.success('Regla fiscal parametrizada correctamente.');
      fetchReglas();
      return true;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Fallo de validación al crear la regla.');
      return false;
    }
  };

  const updateRegla = async (id: number, payload: Partial<ReglaImpuesto>) => {
    try {
      await api.patch(`/v1/fiscal/reglas/${id}`, payload);
      toast.success('Regla fiscal actualizada.');
      fetchReglas();
      return true;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'No se pudo alterar la matriz tributaria.');
      return false;
    }
  };

  useEffect(() => {
    fetchReglas();
  }, [fetchReglas]);

  return { reglas, isLoading, createRegla, updateRegla, refresh: fetchReglas };
}
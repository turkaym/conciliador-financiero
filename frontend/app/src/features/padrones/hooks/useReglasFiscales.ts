import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import api from '@/api/axios';
import { extractApiError } from '@/lib/utils';

export interface ReglaImpuesto {
  id: number;
  entidad_id: number;
  tipo_impuesto: string;
  jurisdiccion: string;
  codigo_regimen_afip: number;
  alicuota_defecto: number;
  monto_minimo_sujeto: number;
  aplica_padron: boolean;
  is_active: boolean;
  cuenta_contable_id: number | null;
}

type ReglaImpuestoCreate = Omit<ReglaImpuesto, 'id' | 'entidad_id' | 'is_active' | 'cuenta_contable_id'> & {
  cuenta_contable_id?: number | null;
};

type ReglaImpuestoUpdate = Partial<Pick<ReglaImpuesto,
  'codigo_regimen_afip' | 'alicuota_defecto' | 'monto_minimo_sujeto' | 'aplica_padron' | 'is_active' | 'cuenta_contable_id'
>>;

export function useReglasFiscales() {
  const [reglas, setReglas] = useState<ReglaImpuesto[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReglas = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.get<ReglaImpuesto[]>('/v1/fiscal/reglas');
      setReglas(response.data);
    } catch (error) {
      toast.error('Error al cargar la matriz impositiva.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createRegla = async (payload: ReglaImpuestoCreate) => {
    try {
      await api.post('/v1/fiscal/reglas', payload);
      toast.success('Regla fiscal parametrizada correctamente.');
      fetchReglas();
      return true;
    } catch (error: unknown) {
      toast.error(extractApiError(error, 'Fallo de validación al crear la regla.'));
      return false;
    }
  };

  const updateRegla = async (id: number, payload: ReglaImpuestoUpdate) => {
    try {
      await api.patch(`/v1/fiscal/reglas/${id}`, payload);
      toast.success('Regla fiscal actualizada.');
      fetchReglas();
      return true;
    } catch (error: unknown) {
      toast.error(extractApiError(error, 'No se pudo alterar la matriz tributaria.'));
      return false;
    }
  };

  useEffect(() => {
    fetchReglas();
  }, [fetchReglas]);

  return { reglas, isLoading, createRegla, updateRegla, refresh: fetchReglas };
}

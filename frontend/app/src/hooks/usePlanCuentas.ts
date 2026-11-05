import { useState, useCallback } from 'react';
import api from '@/api/axios';
import { extractApiError } from '@/lib/utils';

export interface PlanCuenta {
  id: number;
  codigo: string;
  nombre: string;
  tipo: string;
  imputable: boolean;
  parent_id?: number | null;
}

export const usePlanCuentas = () => {
  const [cuentasImputables, setCuentasImputables] = useState<PlanCuenta[]>([]);
  const [isLoadingCuentas, setIsLoadingCuentas] = useState(false);
  const [errorCuentas, setErrorCuentas] = useState<string | null>(null);

  const fetchCuentasImputables = useCallback(async () => {
    setIsLoadingCuentas(true);
    setErrorCuentas(null);
    try {
      const response = await api.get<PlanCuenta[]>('/v1/contabilidad/cuentas/imputables');
      setCuentasImputables(response.data);
    } catch (err) {
      setErrorCuentas(extractApiError(err, 'Fallo al obtener el plan de cuentas.'));
    } finally {
      setIsLoadingCuentas(false);
    }
  }, []);

  return {
    cuentasImputables,
    isLoadingCuentas,
    errorCuentas,
    fetchCuentasImputables
  };
};
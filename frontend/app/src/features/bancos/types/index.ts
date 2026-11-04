// ==========================================
// CATÁLOGOS ESTRICTOS (Sincronizados con Backend)
// ==========================================
export type TipoCanalEnum = "BANCO" | "PASARELA";
export type TipoCuentaEnum = "CC_ARS" | "CA_ARS" | "CC_USD" | "CA_USD";
export type MonedaEnum = "ARS" | "USD";

// ==========================================
// INTERFACES BASE (Reflejo del Backend)
// ==========================================
export interface CuentaBancariaRequest {
  tipo_canal: TipoCanalEnum;
  banco: string;
  numero_cuenta: string;
  cbu?: string | null;
  alias?: string | null;
  tipo_cuenta: TipoCuentaEnum;
  moneda: MonedaEnum;
  saldo_actual: string | number;

  is_virtual_clearing?: boolean;
  proveedor_clearing_id?: number | null;
}

export interface CuentaBancaria extends CuentaBancariaRequest {
  id: number;
  entidad_id: number;
  is_active: boolean;
  is_syncing: boolean;
  saldo_retenido: string | number;
  last_task_id?: string | null;
  progress?: number | null;
  status_msg?: string | null;
  created_at?: string | null;
  updated_at?: string | null;

  is_virtual_clearing: boolean;
  proveedor_clearing_id?: number | null;
}

export type CuentaBancariaCreate = CuentaBancariaRequest;

export interface MovimientoBancarioRequest {
  cuenta_id: number;
  cuenta_contable_id: number;
  fecha: string;
  concepto_bancario_crudo: string;
  concepto_interno?: string | null;
  monto: string | number;
  referencia_banco: string;
}

export interface MovimientoBancario extends MovimientoBancarioRequest {
  id: number;

  // 🌟 FIX FASE 2.2: Discriminador explícito proveniente de Pydantic
  tipo_registro: "MOVIMIENTO" | "SOLICITUD";

  entidad_id?: number;
  concepto_bancario_crudo: string;
  concepto_interno?: string | null;
  hash_transaccional?: string;
  concepto?: string;
  moneda: MonedaEnum;

  saldo_pendiente?: string | number;
  saldo_resultante?: string | number | null;
  anulado?: boolean;

  estado: string; // PENDING_APPROVAL, APROBADO, RECHAZADO, CONCILIADO
  usuario_creador_id?: string | null;
  usuario_creador_nombre?: string | null;
  usuario_resolutor_id?: string | null;
  motivo_rechazo?: string | null;

  created_at?: string | null;
  conciliado: boolean;
}

export type MovimientoBancarioCreate = MovimientoBancarioRequest;

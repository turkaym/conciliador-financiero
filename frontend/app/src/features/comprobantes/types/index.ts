// 🌟 FIX FASE 11: Tipos Híbridos para PostgreSQL JSONB
export interface SubtotalIva {
  id_alicuota_afip: "3" | "4" | "5" | "6" | "8" | "9";
  base_imponible: number;
  importe: number;
}

export interface OtroTributo {
  id_tributo_afip: "1" | "2" | "3" | "4" | "99";
  descripcion?: string;
  base_imponible: number;
  alicuota: number;
  importe: number;
}

export interface Comprobante {
  id: number;
  // 🌟 FIX FASE A: Inyección de datos
  cuenta_contable_id?: number | null;
  numero_formateado?: string;

  clase_documento: string;
  tipo_operacion: string;
  fecha_emision: string;
  tipo_cbte_afip?: number | null;
  punto_venta: number;
  numero: number;
  cuit_emisor: string;
  cuit_receptor: string;

  importe_neto_gravado: number;
  importe_no_gravado: number;
  importe_exento: number;
  importe_total: number;

  subtotales_iva?: SubtotalIva[];
  otros_tributos?: OtroTributo[];

  estado: string;
  cae?: string | null;
}

export interface ComprobanteCreatePayload {
  entidad_id: number;
  // 🌟 FIX FASE A: Obligatorio para el POST
  cuenta_contable_id: number;

  clase_documento: string;
  tipo_operacion: string;
  fecha_emision: string;
  moneda: string;

  punto_venta: number;
  numero: number;
  cuit_emisor: string;
  cuit_receptor: string;

  importe_neto_gravado: number;
  importe_no_gravado: number;
  importe_exento: number;
  importe_total: number;
  subtotales_iva: SubtotalIva[];
  otros_tributos: OtroTributo[];

  comprobante_origen_id?: number | null;
  es_fiscal?: boolean;
  condicion_fiscal_receptor?: string;
  condicion_venta: string;
  cuenta_tesoreria_id?: number | null;
}
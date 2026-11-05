import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import axios from "axios"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 🛡️ Validador Matemático de CUIT/CUIL (Algoritmo Módulo 11 - AFIP)
 * Centralizado para cumplimiento DRY. Utilizable en Registro y ABM de Entidades.
 */
export const isValidCUIT = (cuit: string): boolean => {
  if (!cuit) return false;
  const cleanCuit = cuit.replace(/\D/g, '');
  if (cleanCuit.length !== 11) return false;

  const base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  let sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cleanCuit[i], 10) * base[i];
  }

  let verifier = 11 - (sum % 11);
  if (verifier === 11) verifier = 0;
  if (verifier === 10) return false; // CUIT inválido

  return verifier === parseInt(cleanCuit[10], 10);
};

/**
 * Aduana Global de Errores
 * Desempaqueta de forma estándar los errores de FastAPI y Pydantic para toda la aplicación.
 */
export function extractApiError(err: unknown, defaultMsg: string = "Ocurrió un error inesperado."): string {
  if (axios.isAxiosError(err)) {
    const serverDetail = err.response?.data?.detail;

    // 1. Manejo de Errores de Validación de Pydantic (HTTP 422)
    if (Array.isArray(serverDetail)) {
      const mensajes = serverDetail.map((errItem: any) => {
        const campo = errItem.loc?.[errItem.loc.length - 1] || 'campo desconocido';
        let msg = errItem.msg;

        // Diccionario global de traducciones amigables para el usuario
        if (msg.includes("String should have at least")) msg = "Es demasiado corto.";
        if (msg.includes("String should have at most")) msg = "Es demasiado largo.";
        if (msg.includes("Input should be a valid")) msg = "Formato inválido.";
        if (msg.includes("should match pattern '^\\d{11}$'")) msg = "Debe tener exactamente 11 dígitos numéricos.";
        if (msg.includes("Input should be")) msg = "Valor no permitido o vacío.";

        return `Revisá '${campo}': ${msg}`;
      });
      return mensajes.join(' | ');
    }

    // 2. Manejo de Errores de Negocio del Backend (HTTP 400, 403, 409, 500)
    if (typeof serverDetail === 'string') {
      return serverDetail;
    }
  }

  // 3. Fallbacks para errores nativos de JS o caídas completas de Red (CORS, 502, etc.)
  if (err instanceof Error && !axios.isAxiosError(err)) {
    return err.message;
  }

  return defaultMsg;
}

/**
 * 🌟 FORMATEADOR BIMONETARIO ENTERPRISE
 * Centralizado para cumplimiento DRY y soporte multimoneda E2E.
 * Mapea la nomenclatura estándar contable e inyecta los símbolos de divisa dinámicos.
 */
export function formatCurrency(amount: number, currency: string | undefined | null = "ARS"): string {
  const normCurrency = String(currency || "ARS").toUpperCase().trim();

  const numericFormatter = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });

  const valueFormatted = numericFormatter.format(amount);

  if (normCurrency === "USD" || normCurrency === "US$") {
    return `U$S ${valueFormatted}`;
  }

  return `$ ${valueFormatted}`;
}
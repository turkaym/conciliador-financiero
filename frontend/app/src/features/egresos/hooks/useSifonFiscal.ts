import { useState, useEffect } from "react";
import api from "@/api/axios";
import { compressToWebP } from "@/lib/edgeCompression";
import { useAuthStore, type Entidad } from "@/store/useAuthStore";
import { usePlanCuentas } from "@/hooks/usePlanCuentas";
import { useEgresosStore } from "@/store/useEgresosStore";
import { extractApiError } from "@/lib/utils";
import type { CuentaBancaria } from "@/features/bancos/types";

interface EntidadConRol extends Entidad {
  rol?: string;
  role?: string;
}

interface Concepto {
  id: number;
  codigo: string;
  nombre_descriptivo: string;
}

interface Proveedor {
  id: number;
  cuit: string;
  razon_social: string;
}

interface PresignedUploadResponse {
  upload_url: string;
  final_url: string;
}

export function useSifonFiscal() {
  const user = useAuthStore((state) => state.user);
  const entidadActiva = useAuthStore((state) => state.entidadActiva as EntidadConRol | null);
  const activeRole = String(entidadActiva?.rol || entidadActiva?.role || user?.role || "").toLowerCase();
  const isAdmin = ["admin", "editor", "dueño"].includes(activeRole);
  const fetchOrdenes = useEgresosStore((state) => state.fetchOrdenes);

  const { cuentasImputables, fetchCuentasImputables, isLoadingCuentas } = usePlanCuentas();

  const [monto, setMonto] = useState("");
  const [moneda, setMoneda] = useState("ARS");
  const [tipoCambio, setTipoCambio] = useState("");
  const [conceptoId, setConceptoId] = useState(""); // 🌟 Saneado
  const [proveedorId, setProveedorId] = useState("");
  const [cuentaId, setCuentaId] = useState("");
  const [cuentaContableId, setCuentaContableId] = useState("");
  const [requiereComprobante, setRequiereComprobante] = useState(false);
  const [numeroTicket, setNumeroTicket] = useState("");

  const [conceptos, setConceptos] = useState<Concepto[]>([]);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [cuentas, setCuentas] = useState<CuentaBancaria[]>([]);
  const [isLoadingMaestros, setIsLoadingMaestros] = useState(true);

  const [isAddingProv, setIsAddingProv] = useState(false);
  const [newProv, setNewProv] = useState({ cuit: "", razon_social: "", condicion_fiscal: "RESPONSABLE_INSCRIPTO" });
  const [isAddingConc, setIsAddingConc] = useState(false);
  const [newConc, setNewConc] = useState({ codigo: "", nombre_descriptivo: "" });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!entidadActiva?.id) return;

    let isMounted = true;
    const fetchMaestros = async () => {
      try {
        const headers = { 'x-entity-id': entidadActiva.id };
        const [conceptosResponse, proveedoresResponse, cuentasResponse] = await Promise.all([
          api.get<Concepto[]>('/v1/pagos/conceptos', { headers }),
          api.get<Proveedor[]>('/v1/pagos/proveedores', { headers }),
          isAdmin ? api.get<CuentaBancaria[]>('/v1/bancos/cuentas', { headers }) : Promise.resolve(null)
        ]);

        if (isMounted) {
          setConceptos(conceptosResponse.data);
          setProveedores(proveedoresResponse.data);
          if (cuentasResponse) setCuentas(cuentasResponse.data);
        }

        if (cuentasImputables.length === 0) {
          await fetchCuentasImputables();
        }
      } catch (error) {
        console.error("Error cargando maestros:", error);
      } finally {
        if (isMounted) setIsLoadingMaestros(false);
      }
    };
    fetchMaestros();
    return () => { isMounted = false };
  }, [isAdmin, fetchCuentasImputables, cuentasImputables.length, entidadActiva?.id]);

  useEffect(() => {
    if (cuentaId && cuentas.length > 0) {
      const cuentaSeleccionada = cuentas.find(c => c.id.toString() === cuentaId);
      if (cuentaSeleccionada && cuentaSeleccionada.moneda) {
        setMoneda(cuentaSeleccionada.moneda);
        if (cuentaSeleccionada.moneda === "ARS") setTipoCambio("");
      }
    }
  }, [cuentaId, cuentas]);

  const handleCrearProveedor = async () => {
    setFormError(null);
    if (!entidadActiva?.id) return;
    if (newProv.cuit.length !== 11 || !newProv.razon_social) {
      return setFormError("El CUIT debe tener 11 dígitos exactos y la Razón Social es obligatoria.");
    }
    try {
      setIsSubmitting(true);
      const { data } = await api.post<Proveedor>('/v1/pagos/proveedores', { ...newProv, is_proveedor: true }, { headers: { 'x-entity-id': entidadActiva.id } });
      setProveedores([...proveedores, data]);
      setProveedorId(data.id.toString());
      setIsAddingProv(false);
      setNewProv({ cuit: '', razon_social: '', condicion_fiscal: "RESPONSABLE_INSCRIPTO" });
    } catch (error: unknown) {
      setFormError(extractApiError(error, "Error al crear proveedor."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCrearConcepto = async () => {
    setFormError(null);
    if (!entidadActiva?.id) return;
    if (!newConc.codigo || !newConc.nombre_descriptivo) {
      return setFormError("Debe completar el Código y el Nombre del concepto.");
    }
    try {
      setIsSubmitting(true);
      const { data } = await api.post<Concepto>('/v1/pagos/conceptos', newConc, { headers: { 'x-entity-id': entidadActiva.id } });
      setConceptos([...conceptos, data]);
      setConceptoId(data.id.toString());
      setIsAddingConc(false);
      setNewConc({ codigo: '', nombre_descriptivo: '' });
    } catch (error: unknown) {
      setFormError(extractApiError(error, "Error al crear concepto operativo."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) return setFormError("Sube una imagen válida.");

    try {
      setIsCompressing(true);
      const compressedFile = await compressToWebP(file, 1920, 0.7);
      setSelectedFile(compressedFile);
      setPreviewUrl(URL.createObjectURL(compressedFile));
    } catch {
      setFormError("Hubo un error al procesar la imagen de resguardo.");
    } finally {
      setIsCompressing(false);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!entidadActiva?.id) return setFormError("Entidad no detectada. Refresque la página.");

    if (!monto || !conceptoId || !cuentaContableId) {
      return setFormError("Debes completar Monto, Concepto e Imputación contable obligatoriamente.");
    }
    if (isAdmin && !cuentaId) {
      return setFormError("Debe seleccionar una Cuenta/Caja de origen para liquidar el pago al instante.");
    }

    if (moneda === "USD" && (!tipoCambio || parseFloat(tipoCambio) <= 0)) {
      return setFormError("Al operar en moneda extranjera (USD), es obligatorio ingresar la cotización del día para el asiento contable.");
    }

    try {
      setIsSubmitting(true);
      let urlTicketFinal = null;

      if (selectedFile) {
        try {
          const { data } = await api.get<PresignedUploadResponse>('/v1/pagos/adjuntos/presigned', {
            params: { filename: "ticket.webp", content_type: selectedFile.type },
            headers: { 'x-entity-id': entidadActiva.id }
          });
          const uploadResponse = await fetch(data.upload_url, {
            method: 'PUT',
            body: selectedFile,
            headers: { 'Content-Type': selectedFile.type }
          });
          if (!uploadResponse.ok) throw new Error("Fallo HTTP");
          urlTicketFinal = data.final_url;
        } catch {
          return setFormError("Fallo de red al enviar el archivo de resguardo fotográfico a MinIO.");
        }
      }

      const payload = {
        concepto_id: parseInt(conceptoId),
        proveedor_id: proveedorId ? parseInt(proveedorId) : null,
        cuenta_contable_id: parseInt(cuentaContableId),
        monto_estimado: parseFloat(monto),
        moneda: moneda,
        tipo_cambio_estimado: moneda === "USD" ? parseFloat(tipoCambio) : 1.0,
        requiere_comprobante_fiscal: requiereComprobante,
        comprobante_interno_url: urlTicketFinal,
        numero_ticket: requiereComprobante ? null : numeroTicket,
        fast_track_cuenta_id: (isAdmin && cuentaId) ? parseInt(cuentaId) : null
      };

      const idempotencyKey = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString() + Math.random().toString(36).substring(2);

      await api.post('/v1/pagos/ordenes', payload, {
        headers: {
          'x-entity-id': entidadActiva.id,
          'Idempotency-Key': idempotencyKey
        }
      });

      await fetchOrdenes(true);

      setSuccess(true);
      setMonto(""); setTipoCambio(""); setConceptoId(""); setProveedorId(""); setCuentaId(""); setCuentaContableId("");
      setRequiereComprobante(false); setNumeroTicket(""); clearFile();
      setTimeout(() => setSuccess(false), 3000);

    } catch (error: unknown) {
      setFormError(extractApiError(error, "Fallo interno de servidor al procesar la liquidación."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    isAdmin, monto, setMonto, moneda, setMoneda, tipoCambio, setTipoCambio, conceptoId, setConceptoId, proveedorId, setProveedorId, cuentaId, setCuentaId, requiereComprobante, setRequiereComprobante,
    numeroTicket, setNumeroTicket, cuentaContableId, setCuentaContableId,
    conceptos, proveedores, cuentas, cuentasImputables, isLoadingMaestros, isLoadingCuentas,
    isAddingProv, setIsAddingProv, newProv, setNewProv, handleCrearProveedor,
    isAddingConc, setIsAddingConc, newConc, setNewConc, handleCrearConcepto,
    selectedFile, previewUrl, isCompressing, isSubmitting, success,
    handleFileChange, clearFile, handleSubmit, formError, setFormError
  };
}

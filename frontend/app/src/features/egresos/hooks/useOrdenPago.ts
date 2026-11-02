import { useState, useEffect, useRef } from "react";
import api from "@/api/axios";
import { toast } from "react-toastify";
import { useAuthStore } from "@/store/useAuthStore";
import type { Comprobante } from "@/features/comprobantes/types";
import type { ContactoComercial } from "@/features/ingesta/types";

interface RetencionCalculada {
  tipo_impuesto: string;
  jurisdiccion: string;
  alicuota_aplicada: number;
  monto_impuesto: number;
}

export function useOrdenPago() {
  const entidadActiva = useAuthStore((state: any) => state.entidadActiva);
  const user = useAuthStore((state: any) => state.user);

  const isAdminRole = ["admin", "editor", "dueño"].includes(user?.role?.toLowerCase() || "");

  const [proveedores, setProveedores] = useState<ContactoComercial[]>([]);
  const [cuentas, setCuentas] = useState<any[]>([]);
  const [facturasDelProveedor, setFacturasDelProveedor] = useState<Comprobante[]>([]);

  const [isLoadingMaestros, setIsLoadingMaestros] = useState(true);
  const [isLoadingFacturas, setIsLoadingFacturas] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCalculatingTax, setIsCalculatingTax] = useState(false);

  const [proveedorId, setProveedorId] = useState<string>("");
  const [facturasSeleccionadasIds, setFacturasSeleccionadasIds] = useState<Set<number>>(new Set());
  const [montoAbonar, setMontoAbonar] = useState<string>("");
  const [cuentaOrigenId, setCuentaOrigenId] = useState<string>("");
  const [tipoCambio, setTipoCambio] = useState<string>("1.0");

  const [retencionesSugeridas, setRetencionesSugeridas] = useState<RetencionCalculada[]>([]);
  const [aplicarRetenciones, setAplicarRetenciones] = useState(true);

  const [netoCalculadoMotor, setNetoCalculadoMotor] = useState<number>(0);

  const debounceRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!entidadActiva?.id) return;

    let isMounted = true;
    const fetchMaestros = async () => {
      try {
        const headers = { 'x-entity-id': entidadActiva.id };
        const [resProv, resCuentas] = await Promise.all([
          api.get('/v1/pagos/proveedores', { headers }),
          api.get('/v1/bancos/cuentas', { headers })
        ]);
        if (isMounted) {
          setProveedores(resProv.data || []);
          setCuentas(resCuentas.data || []);
        }
      } catch (error) {
        toast.error("Error al cargar el catálogo de proveedores y cuentas.");
      } finally {
        if (isMounted) setIsLoadingMaestros(false);
      }
    };
    fetchMaestros();
    return () => { isMounted = false; };
  }, [entidadActiva?.id]);

  useEffect(() => {
    if (!proveedorId || !entidadActiva?.id) {
      setFacturasDelProveedor([]);
      setFacturasSeleccionadasIds(new Set());
      setMontoAbonar("");
      return;
    }

    let isMounted = true;
    const fetchFacturasPendientes = async () => {
      setIsLoadingFacturas(true);
      try {
        const headers = { 'x-entity-id': entidadActiva.id };
        const res = await api.get(`/v1/comprobantes/pendientes-proveedor/${proveedorId}`, { headers });
        if (isMounted) {
          setFacturasDelProveedor(res.data || []);
          setFacturasSeleccionadasIds(new Set());
          setMontoAbonar("");
        }
      } catch (error) {
        toast.error("No se pudieron cargar las facturas de este proveedor.");
      } finally {
        if (isMounted) setIsLoadingFacturas(false);
      }
    };
    fetchFacturasPendientes();
    return () => { isMounted = false; };
  }, [proveedorId, entidadActiva?.id]);

  const toggleFactura = (facturaId: number) => {
    const newSelection = new Set(facturasSeleccionadasIds);
    if (newSelection.has(facturaId)) newSelection.delete(facturaId);
    else newSelection.add(facturaId);
    setFacturasSeleccionadasIds(newSelection);

    const nuevoMontoTotal = Array.from(newSelection).reduce((acc, id) => {
      const f = facturasDelProveedor.find(fac => fac.id === id);
      return acc + (f ? Number(f.saldo_pendiente || 0) : 0);
    }, 0);
    setMontoAbonar(nuevoMontoTotal > 0 ? nuevoMontoTotal.toString() : "");
  };

  useEffect(() => {
    const montoNumerico = parseFloat(montoAbonar);
    if (facturasSeleccionadasIds.size === 0 || !montoAbonar || isNaN(montoNumerico) || montoNumerico <= 0 || !proveedorId || !entidadActiva?.id) {
      setRetencionesSugeridas([]);
      setNetoCalculadoMotor(0);
      return;
    }

    const tcNum = parseFloat(tipoCambio) || 1.0;
    const cuentaSeleccionada = cuentas.find(c => c?.id?.toString() === cuentaOrigenId);
    const monedaPago = cuentaSeleccionada && cuentaSeleccionada.moneda ? cuentaSeleccionada.moneda : "ARS";

    if (monedaPago !== "ARS" && tcNum <= 1.0) {
      setRetencionesSugeridas([]);
      return;
    }

    const fetchRetenciones = async () => {
      setIsCalculatingTax(true);
      try {
        const payload = {
          proveedor_id: parseInt(proveedorId),
          facturas_ids: Array.from(facturasSeleccionadasIds),
          monto_bruto_abonar: montoNumerico,
          moneda_pago: monedaPago,
          tipo_cambio: tcNum
        };

        const { data } = await api.post('/v1/fiscal/simular-retencion', payload, { headers: { 'x-entity-id': entidadActiva.id } });
        setRetencionesSugeridas(data?.retenciones_sugeridas || []);
        setNetoCalculadoMotor(Number(data?.neto_a_transferir) || 0);
      } catch (error: any) {
        toast.warning(error.response?.data?.detail || "No se pudo calcular la matriz impositiva para este pago.");
        setRetencionesSugeridas([]);
        setNetoCalculadoMotor(montoNumerico);
      } finally {
        setIsCalculatingTax(false);
      }
    };

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(fetchRetenciones, 500);

    return () => clearTimeout(debounceRef.current);
  }, [montoAbonar, facturasSeleccionadasIds, tipoCambio, cuentaOrigenId, proveedorId, cuentas, entidadActiva?.id]);

  // 🌟 FIX DEUDA TÉCNICA: Se añade el parámetro customRetenciones para evitar mutaciones directas del estado desde el formulario
  const handleSubmit = async (e: React.FormEvent, customRetenciones?: RetencionCalculada[]) => {
    e.preventDefault();

    if (facturasSeleccionadasIds.size === 0 || !montoAbonar || !entidadActiva?.id) {
      return toast.warning("Complete todos los campos obligatorios (Proveedor y Facturas).");
    }

    try {
      setIsSubmitting(true);
      const cuentaSeleccionada = cuentas.find(c => c?.id?.toString() === cuentaOrigenId);
      const monedaPago = cuentaSeleccionada && cuentaSeleccionada.moneda ? cuentaSeleccionada.moneda : "ARS";

      const cuentaFinalId = isAdminRole && cuentaOrigenId ? parseInt(cuentaOrigenId) : null;

      const payload = {
        proveedor_id: parseInt(proveedorId),
        facturas_ids: Array.from(facturasSeleccionadasIds),
        monto_bruto_abonar: parseFloat(montoAbonar),
        cuenta_origen_id: cuentaFinalId,
        moneda_pago: monedaPago,
        tipo_cambio: parseFloat(tipoCambio) || 1.0,
        // Usamos las retenciones editadas en la UI, si existen, de lo contrario usamos el estado base
        retenciones: aplicarRetenciones ? (customRetenciones || retencionesSugeridas) : []
      };

      // 🌟 El Idempotency-Key ahora lo inyecta axios.ts de forma automática y segura
      await api.post('/v1/pagos/ordenes/pago-multiple', payload, {
        headers: { 'x-entity-id': entidadActiva.id }
      });

      if (payload.cuenta_origen_id) {
        toast.success("Liquidación directa ejecutada. Fondos debitados al instante.");
      } else {
        toast.success("Operación autorizada y encolada con éxito en el Hub Interbanking.");
      }

      setProveedorId("");
      setFacturasSeleccionadasIds(new Set());
      setFacturasDelProveedor([]);
      setCuentaOrigenId("");
      setTipoCambio("1.0");

    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Fallo crítico al procesar la orden de pago múltiple.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalRetenciones = aplicarRetenciones ? retencionesSugeridas.reduce((acc, curr) => acc + (Number(curr?.monto_impuesto) || 0), 0) : 0;
  const montoBaseArs = Number(montoAbonar) || 0;
  const netoFinalUI = aplicarRetenciones && netoCalculadoMotor > 0 ? netoCalculadoMotor : montoBaseArs;
  const cuentaSeleccionada = cuentas.find(c => c?.id?.toString() === cuentaOrigenId);
  const saldoActual = Number(cuentaSeleccionada?.saldo_actual) || 0;
  const saldoRetenido = Number(cuentaSeleccionada?.saldo_retenido) || 0;
  const saldoDisponible = saldoActual - saldoRetenido;

  const netoSeguro = Number(netoFinalUI) || 0;
  const saldoSeguro = Number(saldoDisponible) || 0;

  const tieneSaldoInsuficiente = cuentaOrigenId !== "" && netoSeguro > saldoSeguro;

  return {
    proveedores, cuentas, facturasDelProveedor,
    isLoadingMaestros, isLoadingFacturas, isSubmitting, isCalculatingTax,
    proveedorId, setProveedorId,
    facturasSeleccionadasIds, toggleFactura,
    montoAbonar, setMontoAbonar, cuentaOrigenId, setCuentaOrigenId,
    tipoCambio, setTipoCambio,
    retencionesSugeridas, aplicarRetenciones, setAplicarRetenciones,
    totalRetenciones, netoTransferir: netoSeguro, handleSubmit,
    saldoDisponible: saldoSeguro, tieneSaldoInsuficiente,
    isAdmin: isAdminRole
  };
}
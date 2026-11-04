import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Plus, Loader2, AlertCircle, Lock, Unlock, Calculator, ArrowDownUp, Landmark, TriangleAlert, BookOpenCheck } from "lucide-react"

import type { Comprobante, ComprobanteCreateInput, ComprobanteFormData, SubtotalIva } from "../types"
import { usePlanCuentas } from "@/hooks/usePlanCuentas"
import { SeccionTercero } from "./SeccionTercero"
import { useComprobantes } from "../hooks/useComprobantes"

interface ComprobanteFormModalProps {
  entidadActiva: { id: number; cuit: string; nombre_fantasia: string; condicion_fiscal: string };
  remitosPendientes: Comprobante[];
  cajasDisponibles: {id: number, nombre: string, moneda: string}[];
  isSaving: boolean;
  errorMsg: string | null;
  onOpen: (cuit?: string) => void;
  onClose: () => void;
  onSubmit: (payload: ComprobanteCreateInput) => Promise<boolean>;
}

export function ComprobanteFormModal({ entidadActiva, remitosPendientes, cajasDisponibles, isSaving, errorMsg, onOpen, onClose, onSubmit }: ComprobanteFormModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { cuentasImputables, fetchCuentasImputables, isLoadingCuentas } = usePlanCuentas();
  const { facturasAsociables, fetchFacturasParaAsociar } = useComprobantes();

  const [formData, setFormData] = useState<ComprobanteFormData>({
    clase_documento: "FACTURA",
    tipo_operacion: "VENTA",
    fecha_emision: new Date(new Date().getTime() - new Date().getTimezoneOffset() * 60000).toISOString().split('T')[0],
    punto_venta: "",
    numero: "",
    cuit_tercero: "",
    razon_social_receptor: "",
    condicion_fiscal_receptor: "CONSUMIDOR_FINAL",
    importe_neto_gravado: "",
    importe_no_gravado: "0.00",
    importe_exento: "0.00",
    importe_total: "",
    comprobante_origen_id: "none",
    condicion_venta: "CUENTA_CORRIENTE",
    cuenta_tesoreria_id: "",
    cuenta_contable_id: "",
    moneda: "ARS",
    cotizacion: "1.000"
  });

  const [alicuota, setAlicuota] = useState("5");
  const [isOverride, setIsOverride] = useState(false);
  const [calculoInverso, setCalculoInverso] = useState(true);
  const [warningIva, setWarningIva] = useState<string | null>(null);
  const [cuitError, setCuitError] = useState<string | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);

  const isMonotributo = ["MONOTRIBUTO", "EXENTO"].includes(entidadActiva.condicion_fiscal);
  const isVenta = formData.tipo_operacion === "VENTA";
  const isRemito = formData.clase_documento === "REMITO";
  const isNotaCreditoODebito = formData.clase_documento === "NOTA_CREDITO" || formData.clase_documento === "NOTA_DEBITO";
  const isVinculado = formData.comprobante_origen_id !== "none";
  const isContado = formData.condicion_venta === "CONTADO";
  const canOverride = !isVenta && !isVinculado;
  const isMathLocked = (!isOverride || isVenta) && !isVinculado;

  useEffect(() => {
    if (isOpen && cuentasImputables.length === 0) {
      fetchCuentasImputables();
    }
  }, [isOpen, fetchCuentasImputables, cuentasImputables.length]);

  // 🌟 FIX: Efecto exclusivo para validar el CUIT y abrir la carpeta del cliente en el backend
  useEffect(() => {
    const cleanCuit = formData.cuit_tercero.replace(/\D/g, '');
    if (cleanCuit.length > 11) {
        setCuitError("El CUIT no puede exceder los 11 dígitos. Por favor, verifique.");
        if (isOpen) onOpen("");
        setFormData(prev => ({...prev, comprobante_origen_id: "none"}));
    } else {
        setCuitError(null);
        if (cleanCuit.length === 11 && !isRemito) {
            if (isOpen) onOpen(cleanCuit);
        } else if (cleanCuit.length < 11) {
            if (isOpen) onOpen("");
            setFormData(prev => ({...prev, comprobante_origen_id: "none"}));
        }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.cuit_tercero, isRemito, isOpen]);

  // 🌟 FIX FASE D: Efecto reactivo exclusivo para buscar Facturas Asociables (NC/ND)
  // Ahora se disparará sin importar el orden en que el usuario llene el formulario
  useEffect(() => {
    const cleanCuit = formData.cuit_tercero.replace(/\D/g, '');
    if (isOpen && isNotaCreditoODebito && cleanCuit.length === 11) {
        fetchFacturasParaAsociar(cleanCuit, formData.tipo_operacion);
    }
  }, [isOpen, isNotaCreditoODebito, formData.cuit_tercero, formData.tipo_operacion, fetchFacturasParaAsociar]);

  useEffect(() => {
    if (isRemito) return;

    const timeoutId = setTimeout(() => {
      const noGrav = parseFloat(formData.importe_no_gravado) || 0;
      const exento = parseFloat(formData.importe_exento) || 0;
      let multiplicador = alicuota === "5" ? 0.21 : (alicuota === "4" ? 0.105 : 0.27);

      if (isMathLocked) {
        if (isMonotributo) {
          // 🌟 FIX RIESGO: Respetamos el Total que ingresó el usuario. Solo forzamos el Neto a 0.
          setFormData(prev => {
            if (prev.importe_neto_gravado === "0.00") return prev; // Evita re-renders infinitos
            return { ...prev, importe_neto_gravado: "0.00" };
          });
        } else {
          if (calculoInverso) {
            let total = parseFloat(formData.importe_total) || 0;
            let baseParaCalculo = total - noGrav - exento;
            if (baseParaCalculo < 0) baseParaCalculo = 0;

            let netoDeducido = baseParaCalculo / (1 + multiplicador);
            setFormData(prev => {
              const strValue = netoDeducido.toFixed(2);
              if (prev.importe_neto_gravado === strValue) return prev;
              return { ...prev, importe_neto_gravado: strValue };
            });
          } else {
            let neto = parseFloat(formData.importe_neto_gravado) || 0;
            const iva = neto * multiplicador;
            const totalCalculado = neto + noGrav + exento + iva;
            setFormData(prev => {
              const strValue = totalCalculado.toFixed(2);
              if (prev.importe_total === strValue) return prev;
              return { ...prev, importe_total: strValue };
            });
          }
        }
        setWarningIva(null);
      } else if (!isMonotributo && !isMathLocked) {
        const neto = parseFloat(formData.importe_neto_gravado) || 0;
        const total = parseFloat(formData.importe_total) || 0;

        if (neto > 0 && total > 0) {
          const ivaDeclaradoPorDiferencia = total - neto - noGrav - exento;
          const ivaTeoricoAFIP = neto * multiplicador;

          if (Math.abs(ivaDeclaradoPorDiferencia - ivaTeoricoAFIP) > 1.0) {
            setWarningIva(`⚠️ Cuidado: Los valores implican un IVA de $${ivaDeclaradoPorDiferencia.toFixed(2)}, pero AFIP espera $${ivaTeoricoAFIP.toFixed(2)}.`);
          } else {
            setWarningIva(null);
          }
        }
      }
      setIsCalculating(false);
    }, 400);

    return () => clearTimeout(timeoutId);
  }, [formData.importe_neto_gravado, formData.importe_total, formData.importe_no_gravado, formData.importe_exento, alicuota, isMathLocked, isMonotributo, calculoInverso, isRemito]);

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (open) onOpen();
    else {
      onClose();
      setIsOverride(false);
      setWarningIva(null);
      setCuitError(null);
      setFormData(prev => ({
        ...prev, punto_venta: "", numero: "", cuit_tercero: "", condicion_fiscal_receptor: "CONSUMIDOR_FINAL", razon_social_receptor: "",
        importe_neto_gravado: "", importe_no_gravado: "0.00", importe_exento: "0.00", importe_total: "",
        clase_documento: "FACTURA", comprobante_origen_id: "none", condicion_venta: "CUENTA_CORRIENTE", cuenta_tesoreria_id: "",
        cuenta_contable_id: "",
        moneda: "ARS", cotizacion: "1.000"
      }));
    }
  };

  const handleSelectRemito = (remitoId: string) => {
      if (remitoId === "none") {
        setFormData(prev => ({ ...prev, comprobante_origen_id: "none" }));
        return;
      }
      const remito = remitosPendientes.find(r => r.id.toString() === remitoId);
      if (remito) {
          setCalculoInverso(true);
          setIsOverride(false);
          setIsCalculating(true);
          setFormData(prev => ({
              ...prev,
              comprobante_origen_id: remitoId,
              importe_total: remito.importe_total.toString(),
              tipo_operacion: remito.tipo_operacion
          }));
      }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cuitTerceroLimpio = formData.cuit_tercero.replace(/\D/g, '');
    const myCuit = entidadActiva.cuit;
    const payloadCuitEmisor = isVenta ? myCuit : cuitTerceroLimpio;
    const payloadCuitReceptor = !isVenta ? myCuit : cuitTerceroLimpio;

    let subtotalesIva: SubtotalIva[] = [];
    if (!isMonotributo && !isRemito) {
      const neto = parseFloat(formData.importe_neto_gravado) || 0;
      const total = parseFloat(formData.importe_total) || 0;
      const noGrav = parseFloat(formData.importe_no_gravado) || 0;
      const exento = parseFloat(formData.importe_exento) || 0;

      if (neto > 0) {
        const ivaImporte = total - neto - noGrav - exento;
        subtotalesIva.push({
          // 🌟 FIX TIPADO: Se purga el 'as any' usando tipado numérico explícito
          id_alicuota_afip: Number(alicuota) as SubtotalIva['id_alicuota_afip'],
          base_imponible: neto,
          importe: parseFloat(ivaImporte.toFixed(2))
        });
      }
    }

    let divisaOperacion = formData.moneda;
    if (isContado && formData.cuenta_tesoreria_id) {
        const cajaSeleccionada = cajasDisponibles.find(c => c.id.toString() === formData.cuenta_tesoreria_id);
        if (cajaSeleccionada) divisaOperacion = cajaSeleccionada.moneda;
    }

    const payload: ComprobanteCreateInput = {
      clase_documento: formData.clase_documento,
      tipo_operacion: formData.tipo_operacion,
      fecha_emision: formData.fecha_emision,
      punto_venta: parseInt(formData.punto_venta),
      numero: isVenta ? 1 : (parseInt(formData.numero) || 1),
      cuit_emisor: payloadCuitEmisor,
      cuit_receptor: payloadCuitReceptor,
      importe_neto_gravado: isRemito || isMonotributo ? 0 : parseFloat(formData.importe_neto_gravado || "0"),
      importe_no_gravado: parseFloat(formData.importe_no_gravado || "0"),
      importe_exento: parseFloat(formData.importe_exento || "0"),
      importe_total: parseFloat(formData.importe_total || "0"),
      subtotales_iva: subtotalesIva,
      otros_tributos: [],
      // 🌟 FIX SANITIZACIÓN: Asegurar valores lógicos para la base de datos
      moneda: divisaOperacion,
      cotizacion: divisaOperacion === "ARS" ? 1.0 : parseFloat(formData.cotizacion || "1.0"),
      comprobante_origen_id: formData.comprobante_origen_id !== "none" ? parseInt(formData.comprobante_origen_id) : null,
      es_fiscal: !isRemito,
      condicion_fiscal_receptor: isRemito ? "NO_CATEGORIZADO" : formData.condicion_fiscal_receptor,
      razon_social_receptor: formData.razon_social_receptor,
      condicion_venta: isRemito ? "CUENTA_CORRIENTE" : formData.condicion_venta,
      cuenta_tesoreria_id: isContado ? parseInt(formData.cuenta_tesoreria_id) : null,
      cuenta_contable_id: parseInt(formData.cuenta_contable_id)
    };

    const success = await onSubmit(payload);
    if (success) handleOpenChange(false);
  };

  const isSubmitDisabled =
    isSaving ||
    isCalculating ||
    cuitError !== null ||
    formData.cuit_tercero.replace(/\D/g, '').length < 11 ||
    (isContado && !formData.cuenta_tesoreria_id) ||
    !formData.cuenta_contable_id ||
    (formData.moneda === "USD" && parseFloat(formData.cotizacion) <= 1.0) ||
    (parseFloat(formData.importe_total || "0") <= 0 && !isRemito) ||
    (isNotaCreditoODebito && formData.comprobante_origen_id === "none");
    // Nota: Si es NC/ND bloquea si no hay factura origen. Si es Remito puede ir en 0.

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-slate-900 hover:bg-slate-800 shadow-md">
          <Plus className="mr-2 h-4 w-4" /> Nuevo Comprobante
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[650px] p-0 bg-white overflow-hidden shadow-2xl rounded-xl" onInteractOutside={(e) => e.preventDefault()}>
        <div className="px-4 sm:px-6 py-4 border-b border-slate-100 shrink-0 bg-white">
          <DialogHeader>
            <DialogTitle className="text-xl">Registro de Comprobante</DialogTitle>
            <DialogDescription>
              Matriz fiscal: <span className="font-bold text-indigo-700">{entidadActiva.condicion_fiscal.replace('_', ' ')}</span>
            </DialogDescription>
          </DialogHeader>
        </div>

        <form onSubmit={handleSubmit} className="block m-0 p-0">
          <div className="overflow-y-auto max-h-[50vh] sm:max-h-[56vh] px-4 sm:px-6 py-4 space-y-5 scrollbar-hide bg-white">
            {errorMsg && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md flex items-start text-sm">
                <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div className="space-y-2">
                <Label className="text-xs uppercase font-bold text-slate-500">Clase de Documento</Label>
                <Select value={formData.clase_documento} onValueChange={(val) => setFormData({...formData, clase_documento: val, comprobante_origen_id: "none"})}>
                  <SelectTrigger className="bg-white h-10"><SelectValue placeholder="Clase" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FACTURA">Factura / Ticket Oficial</SelectItem>
                    <SelectItem value="NOTA_CREDITO">Nota de Crédito</SelectItem>
                    <SelectItem value="NOTA_DEBITO">Nota de Débito</SelectItem>
                    <SelectItem value="REMITO">Remito / Movimiento Interno</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase font-bold text-slate-500">Flujo Comercial</Label>
                <Select disabled={formData.comprobante_origen_id !== "none"} value={formData.tipo_operacion} onValueChange={(val) => setFormData({...formData, tipo_operacion: val})}>
                  <SelectTrigger className="bg-white h-10"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="VENTA">Venta Emitida (Ingreso)</SelectItem>
                    <SelectItem value="COMPRA">Compra Recibida (Egreso)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 sm:col-span-2 mt-2 border-t border-slate-200 pt-3">
                <Label className="text-xs uppercase font-bold text-slate-700 flex items-center">
                  <BookOpenCheck className="w-4 h-4 mr-1 text-indigo-600" /> Imputación Contable (Plan de Cuentas) *
                </Label>
                <Select value={formData.cuenta_contable_id} onValueChange={(val) => setFormData({...formData, cuenta_contable_id: val})}>
                  <SelectTrigger className={`bg-white h-10 ${!formData.cuenta_contable_id ? 'border-amber-300 ring-1 ring-amber-100' : 'border-indigo-200'}`}>
                    <SelectValue placeholder={isLoadingCuentas ? "Cargando plan de cuentas..." : "Seleccione el rubro contable correspondiente..."} />
                  </SelectTrigger>
                  <SelectContent>
                    {cuentasImputables.map(cta => (
                      <SelectItem key={cta.id} value={cta.id.toString()} className="font-medium">
                        <span className="text-slate-500 mr-2 text-xs font-mono">{cta.codigo}</span>
                        {cta.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {!isRemito && (
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <Label className="text-sm font-bold text-slate-800">Liquidación de {isVenta ? "Cobro" : "Pago"}</Label>
                    <p className="text-[10px] text-slate-500 mt-0.5">Define si la operación fue a crédito o liquidada en el acto.</p>
                  </div>
                  <div className="flex items-center space-x-2 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                    <Label className={`text-[10px] uppercase font-bold cursor-pointer transition-colors ${!isContado ? 'text-indigo-600' : 'text-slate-400'}`}>C. Corriente</Label>
                    <Switch checked={isContado} onCheckedChange={(val) => setFormData({...formData, condicion_venta: val ? "CONTADO" : "CUENTA_CORRIENTE"})} className="data-[state=checked]:bg-emerald-500" />
                    <Label className={`text-[10px] uppercase font-bold cursor-pointer transition-colors ${isContado ? 'text-emerald-600' : 'text-slate-400'}`}>Al Contado</Label>
                  </div>
                </div>

                {isContado && (
                  <div className="mt-4 pt-4 border-t border-slate-100 animate-in slide-in-from-top-2">
                    <Label className="text-[11px] text-slate-500 uppercase font-bold mb-2 flex items-center">
                      <Landmark className="w-3 h-3 mr-1 text-emerald-600" /> ¿A qué cuenta ingresó el dinero?
                    </Label>
                    <Select value={formData.cuenta_tesoreria_id} onValueChange={(val) => setFormData({...formData, cuenta_tesoreria_id: val})}>
                      <SelectTrigger className="bg-emerald-50/50 border-emerald-200 focus:ring-emerald-500 h-11">
                        <SelectValue placeholder="Seleccione Caja o Billetera destino..." />
                      </SelectTrigger>
                      <SelectContent>
                        {cajasDisponibles.map(caja => (
                          <SelectItem key={caja.id} value={caja.id.toString()} className="font-medium">
                            {caja.nombre} ({caja.moneda})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-xs font-semibold">Fecha Emisión</Label>
                <Input type="date" required className="h-10" value={formData.fecha_emision} onChange={(e) => setFormData({...formData, fecha_emision: e.target.value})} />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-semibold">Punto Venta</Label>
                <Input type="number" required placeholder="0001" className="h-10" value={formData.punto_venta} onChange={(e) => setFormData({...formData, punto_venta: e.target.value})} />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-semibold">Número</Label>
                <Input
                  type={isVenta ? "text" : "number"} required={!isVenta} placeholder="12345678"
                  className={`h-10 ${isVenta ? 'bg-slate-100 text-slate-500 font-mono text-xs' : ''}`}
                  value={isVenta ? "Auto-asignado" : formData.numero} onChange={(e) => setFormData({...formData, numero: e.target.value})} disabled={isVenta}
                />
              </div>
            </div>

            <SeccionTercero
              formData={formData}
              setFormData={setFormData}
              cuitError={cuitError}
              isVenta={isVenta}
              isRemito={isRemito}
              isNotaCreditoODebito={isNotaCreditoODebito}
              remitosPendientes={remitosPendientes}
              facturasAsociables={facturasAsociables}
              handleSelectRemito={handleSelectRemito}
              handleSelectFactura={(id) => setFormData({...formData, comprobante_origen_id: id})}
            />

            <div className="space-y-4 pt-2 pb-4">
              {!isRemito && (
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-4">
                    <Label className="text-slate-700 font-bold flex items-center text-sm">
                      <Calculator className="w-4 h-4 mr-2" /> Matemática Impositiva
                    </Label>
                    {!isMonotributo && isMathLocked && (
                      <div className="flex items-center space-x-2 bg-white px-2 py-1.5 rounded-md border border-slate-200 shadow-sm w-fit">
                        <Label className="text-[10px] text-slate-500 uppercase font-bold cursor-pointer">Neto</Label>
                        <Switch checked={calculoInverso} onCheckedChange={setCalculoInverso} className="scale-75 origin-center" />
                        <Label className="text-[10px] text-indigo-600 uppercase font-bold cursor-pointer">Total</Label>
                      </div>
                    )}
                    {canOverride && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => setIsOverride(!isOverride)} className={`h-9 px-3 text-xs w-full sm:w-auto ${isOverride ? 'text-amber-600 bg-amber-50 font-bold border border-amber-200' : 'text-slate-500 border border-transparent'}`}>
                        {isOverride ? <Unlock className="w-4 h-4 mr-2" /> : <Lock className="w-4 h-4 mr-2" />}
                        {isOverride ? "Overrides Activos" : "Forzar Totales (Compras)"}
                      </Button>
                    )}
                  </div>

                  {!isMonotributo ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-xs font-semibold">Neto Gravado ($)</Label>
                        <Input
                          type="number" step="0.01" disabled={calculoInverso && isMathLocked} value={formData.importe_neto_gravado}
                          onChange={(e) => { setFormData({...formData, importe_neto_gravado: e.target.value}); setIsCalculating(true); }}
                          className={`h-10 ${calculoInverso && isMathLocked ? 'bg-slate-100/50 text-slate-500' : 'bg-white font-medium border-indigo-300 focus:ring-indigo-500'}`}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">Alícuota IVA Principal</Label>
                        <Select value={alicuota} onValueChange={(val) => { setAlicuota(val); setIsCalculating(true); }} disabled={isOverride}>
                          <SelectTrigger className="bg-white h-10"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="5">21.0%</SelectItem>
                            <SelectItem value="4">10.5%</SelectItem>
                            <SelectItem value="6">27.0%</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-amber-700 bg-amber-50 p-3 rounded-lg border border-amber-200/50 font-medium">
                      Su empresa es Monotributista/Exenta. El IVA no será discriminado.
                    </div>
                  )}

                  {warningIva && (
                    <div className="mt-4 bg-amber-100/60 border border-amber-300 text-amber-900 p-3 rounded-md flex items-start text-xs font-medium">
                      <TriangleAlert className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5 text-amber-600" />
                      {warningIva}
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 px-1 pb-2">
                <div className="space-y-2">
                  <Label className="text-xs font-semibold uppercase text-slate-500">Moneda del Comprobante</Label>
                  <Select value={formData.moneda} onValueChange={(val) => setFormData({...formData, moneda: val, cotizacion: val === "ARS" ? "1.000" : ""})}>
                    <SelectTrigger className="bg-white h-10 border-indigo-200 focus:ring-indigo-500"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ARS">Pesos Argentinos (ARS)</SelectItem>
                      <SelectItem value="USD">Dólares Estadounidenses (USD)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {formData.moneda !== "ARS" && (
                  <div className="space-y-2 animate-in fade-in slide-in-from-right-2">
                    <Label className="text-xs font-bold text-blue-700 uppercase flex items-center justify-between">
                      Cotización AFIP
                      <span className="bg-blue-100 text-blue-800 text-[9px] px-1.5 py-0.5 rounded">Requerido</span>
                    </Label>
                    <div className="relative">
                      <span className="absolute left-3 top-2.5 text-blue-500 font-medium text-sm">$</span>
                      <Input
                        type="number" step="0.001" min="1.001" required disabled={isSaving}
                        value={formData.cotizacion}
                        onChange={(e) => setFormData({...formData, cotizacion: e.target.value})}
                        className="bg-blue-50 border-blue-200 text-blue-900 focus:ring-blue-500 h-10 font-bold pl-8"
                        placeholder="Ej: 1050.50"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-2 px-1 pb-4">
                <Label className="text-sm font-bold text-slate-900 flex items-center">
                  Importe Total {isRemito ? "Valorizado (Opcional)" : "Final"} ({formData.moneda === "USD" ? "U$S" : "$"})
                  {calculoInverso && !isRemito && <ArrowDownUp className="w-4 h-4 ml-2 text-indigo-500" />}
                </Label>
                <Input
                  type="number" step="0.01" required={!isRemito} disabled={!calculoInverso && isMathLocked && !isRemito} value={formData.importe_total}
                  onChange={(e) => { setFormData({...formData, importe_total: e.target.value}); setIsCalculating(true); }}
                  className={`text-2xl font-bold h-14 tracking-tight ${calculoInverso || isOverride || isRemito ? 'border-indigo-400 bg-indigo-50/30 text-indigo-900 focus:ring-indigo-500' : 'bg-slate-100 text-slate-500 border-slate-200'}`}
                  placeholder="0.00"
                />
              </div>
            </div>
          </div>

          <div className="px-4 sm:px-6 py-4 border-t border-slate-200 bg-slate-50 flex flex-col sm:flex-row justify-end gap-3 rounded-b-xl">
            <Button type="button" variant="outline" className="h-11 sm:h-10 w-full sm:w-auto" onClick={() => handleOpenChange(false)}>Cancelar</Button>
            <Button type="submit" disabled={isSubmitDisabled} className="h-11 sm:h-10 bg-indigo-600 hover:bg-indigo-700 text-white w-full sm:w-auto sm:min-w-[150px] shadow-sm transition-all">
              {isSaving || isCalculating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {isCalculating ? "Calculando..." : isRemito ? "Registrar Remito" : isContado ? "Liquidar en Caja" : "Emitir Comprobante"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

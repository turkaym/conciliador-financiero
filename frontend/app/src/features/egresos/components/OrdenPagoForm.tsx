import { useState } from "react";
import { Loader2, Receipt, Landmark, ShieldAlert, Calculator, CheckSquare, Square, ChevronsUpDown, Check, Search, Edit3, Layers, Send, Building } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useOrdenPago } from "../hooks/useOrdenPago";
import { useAuthStore } from "@/store/useAuthStore";

export default function OrdenPagoForm() {
  const h = useOrdenPago();
  const [openCombobox, setOpenCombobox] = useState(false);

  // 🌟 FIX RBAC: Definimos el rol ANTES del estado inicial
  const user = useAuthStore((state) => state.user);
  const isAdmin = ["admin", "editor", "dueño"].includes(user?.role?.toLowerCase() || "");

  // 🌟 Si NO es admin, la variable nace y muere en TRUE (siempre Encolado)
  const [esInterbanking, setEsInterbanking] = useState(true);
  const retencionesKey = JSON.stringify([
    h.proveedorId,
    Array.from(h.facturasSeleccionadasIds).sort((a, b) => a - b),
    h.cuentaOrigenId,
    h.tipoCambio,
    h.retencionesSugeridas
  ]);
  const [retencionesEditadas, setRetencionesEditadas] = useState<{ key: string; values: any[] }>({ key: "", values: [] });
  const retencionesEditables = retencionesEditadas.key === retencionesKey
    ? retencionesEditadas.values
    : h.retencionesSugeridas;

  const handleRetencionChange = (index: number, newMonto: string) => {
    const updated = retencionesEditables.map(retencion => ({ ...retencion }));
    updated[index].monto_impuesto = parseFloat(newMonto) || 0;
    setRetencionesEditadas({ key: retencionesKey, values: updated });
  };

  if (h.isLoadingMaestros) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const formatearMoneda = (monto: string | number, moneda?: string | null) => {
    let currencyCode = "ARS";
    if (moneda && typeof moneda === 'string') {
       if (moneda.toUpperCase().includes("USD")) currencyCode = "USD";
       else if (moneda.toUpperCase().includes("ARS")) currencyCode = "ARS";
    }
    const val = Number(monto) || 0;
    try {
      return new Intl.NumberFormat("es-AR", { style: "currency", currency: currencyCode }).format(val);
    } catch (e) {
      return `$ ${val.toFixed(2)}`;
    }
  };

  const proveedorSeleccionado = h.proveedores.find((p) => p?.id?.toString() === h.proveedorId);
  const cuentaElegida = h.cuentas.find(c => c?.id?.toString() === h.cuentaOrigenId);
  const monedaPago = cuentaElegida ? cuentaElegida.moneda : "ARS";

  // 🌟 CÁLCULOS REACTIVOS
  const montoBaseArs = Number(h.montoAbonar) || 0;
  const totalRetencionesEditadas = h.aplicarRetenciones
    ? retencionesEditables.reduce((acc, curr) => acc + (Number(curr?.monto_impuesto) || 0), 0)
    : 0;

  const netoFinalUI = montoBaseArs - totalRetencionesEditadas;
  const saldoActual = Number(cuentaElegida?.saldo_actual) || 0;
  const saldoRetenido = Number(cuentaElegida?.saldo_retenido) || 0;
  const saldoDisponible = saldoActual - saldoRetenido;

  // Bypass de liquidez si es interbanking (no hay cuenta seleccionada aún)
  const tieneSaldoInsuficienteLocal = !esInterbanking && h.cuentaOrigenId !== "" && netoFinalUI > saldoDisponible;

  // 🌟 FIX MATEMÁTICO: Cerrojo Anti-Neto Negativo
  const retencionesInvalidas = netoFinalUI < 0;

  const handleSubmitIntercedido = (e: React.FormEvent) => {
    e.preventDefault();

    // Doble validación estructural
    if (retencionesInvalidas) return;

    // inyectamos las retenciones editables como parámetro al hook, respetando el flujo funcional.
    h.handleSubmit(e, retencionesEditables);
  };

  return (
    <Card className="border-indigo-100 shadow-lg max-w-4xl mx-auto overflow-hidden">
      {/* HEADER & TIPO DE OPERACIÓN */}
      <div className="bg-indigo-50 border-b border-indigo-100 p-4 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start space-x-3">
          <Receipt className="h-6 w-6 text-indigo-600 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-indigo-900 font-bold text-lg">Emisión de Orden de Pago</h3>
            <p className="text-indigo-700/80 text-xs mt-1 leading-relaxed">
              Seleccione el beneficiario y las facturas. El motor calculará retenciones automáticamente.
            </p>
          </div>
        </div>

        {/* 🌟 FIX ESCUDO RBAC: Si es admin ve el switch, si es operador ve la insignia de bloqueo */}
        {isAdmin ? (
          <div className="flex items-center gap-3 bg-white p-2 rounded-lg border border-indigo-200 shadow-sm shrink-0 w-full sm:w-auto justify-center">
            <span className={`text-xs font-bold ${esInterbanking ? 'text-slate-400' : 'text-indigo-600'}`}>Pago Individual</span>
            <Switch
              checked={esInterbanking}
              onCheckedChange={(checked) => {
                setEsInterbanking(checked);
                if (checked) h.setCuentaOrigenId(""); // Limpiamos la cuenta si pasa a encolado masivo
              }}
            />
            <span className={`text-xs font-bold flex items-center gap-1 ${esInterbanking ? 'text-indigo-600' : 'text-slate-400'}`}>
              <Building className="w-4 h-4" /> Interbanking Masivo
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-blue-50 text-blue-800 p-2.5 rounded-lg border border-blue-200 shadow-sm shrink-0 w-full sm:w-auto justify-center cursor-not-allowed" title="Los operadores solo pueden enviar órdenes a autorización.">
            <Layers className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-bold uppercase tracking-wider">Modo Operador: Encolado</span>
          </div>
        )}
      </div>

      <CardContent className="p-4 sm:p-6">
        <form onSubmit={handleSubmitIntercedido} className="space-y-8">

          {/* ============================== */}
          {/* PASO 1: SELECCIÓN DE PROVEEDOR */}
          {/* ============================== */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b pb-2">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-xs">1</span>
              Identificación del Proveedor
            </h3>

            <Popover open={openCombobox} onOpenChange={setOpenCombobox}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  disabled={h.isSubmitting}
                  className={cn(
                    "flex h-11 w-full items-center justify-between rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50",
                    !h.proveedorId && "text-slate-500 font-normal"
                  )}
                >
                  {proveedorSeleccionado ? (
                    <span className="truncate text-slate-900 font-medium">
                      {proveedorSeleccionado.razon_social} <span className="text-slate-400 font-mono text-xs ml-1">(CUIT: {proveedorSeleccionado.cuit})</span>
                    </span>
                  ) : (
                    "Seleccione o busque un proveedor..."
                  )}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </button>
              </PopoverTrigger>

              <PopoverContent className="w-[calc(100vw-3rem)] sm:w-[500px] p-0 shadow-xl border-slate-200" align="start">
                <Command
                  filter={(value, search) => {
                    const normalizedSearch = search.toLowerCase().replace(/\s+/g, '');
                    const [cuit, ...nameParts] = value.split(" ");
                    const normalizedName = nameParts.join("").toLowerCase();
                    if (cuit.includes(normalizedSearch) || normalizedName.includes(normalizedSearch)) return 1;
                    return 0;
                  }}
                >
                  <div className="flex items-center border-b px-3">
                    <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                    <CommandInput placeholder="Nombre o CUIT..." className="h-11 outline-none border-none ring-0 focus:ring-0 shadow-none" />
                  </div>
                  <CommandList>
                    <CommandEmpty className="py-6 text-center text-sm text-slate-500">
                      No se encontraron proveedores coincidentes.
                    </CommandEmpty>
                    <CommandGroup className="max-h-64 overflow-auto py-1">
                      {h.proveedores.map((p) => (
                        <CommandItem
                          key={p.id}
                          value={`${p.cuit} ${p.razon_social}`}
                          onSelect={() => {
                            h.setProveedorId(p.id.toString());
                            setOpenCombobox(false);
                          }}
                          className="flex items-center px-3 py-2.5 cursor-pointer aria-selected:bg-indigo-50"
                        >
                          <Check className={cn("mr-2 h-4 w-4 text-indigo-600", h.proveedorId === p.id.toString() ? "opacity-100" : "opacity-0")} />
                          <div className="flex flex-col truncate">
                            <span className="text-sm font-bold text-slate-800 truncate">{p?.razon_social || "Sin Nombre"}</span>
                            <span className="text-[11px] font-mono text-slate-500 mt-0.5">CUIT: {p?.cuit || "N/A"}</span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* ============================== */}
          {/* PASO 2: SELECCIÓN DE FACTURAS  */}
          {/* ============================== */}
          {h.proveedorId && (
            <div className="space-y-4 animate-in fade-in duration-300">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b pb-2">
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-xs">2</span>
                Facturas Pendientes de Cobro
              </h3>

              {h.isLoadingFacturas ? (
                <div className="flex justify-center py-4"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>
              ) : h.facturasDelProveedor.length === 0 ? (
                <div className="bg-slate-50 border border-dashed border-slate-300 p-6 text-center rounded-lg">
                  <p className="text-sm text-slate-500 font-medium">Este proveedor no tiene facturas con saldo pendiente.</p>
                </div>
              ) : (
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                      <tr>
                        <th className="px-4 py-3 w-12 text-center">Sel.</th>
                        <th className="px-4 py-3 font-semibold">Comprobante</th>
                        <th className="px-4 py-3 font-semibold hidden sm:table-cell">Fecha</th>
                        <th className="px-4 py-3 font-semibold text-right">Saldo Deudor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {h.facturasDelProveedor.map(f => {
                        const isSelected = h.facturasSeleccionadasIds.has(f.id);
                        const ptoVtaStr = (f.punto_venta || 0).toString().padStart(4, '0');
                        const numStr = (f.numero || 0).toString().padStart(8, '0');
                        return (
                          <tr key={f.id} className={`cursor-pointer transition-colors ${isSelected ? 'bg-indigo-50/50' : 'hover:bg-slate-50'}`} onClick={() => h.toggleFactura(f.id)}>
                            <td className="px-4 py-3 text-center">
                              {isSelected ? <CheckSquare className="w-5 h-5 text-indigo-600 mx-auto" /> : <Square className="w-5 h-5 text-slate-300 mx-auto" />}
                            </td>
                            <td className="px-4 py-3 font-mono text-slate-700">
                              <span className="font-bold block sm:inline">FC {ptoVtaStr}-{numStr}</span>
                              <span className="text-[10px] text-slate-400 block sm:hidden">Emisión: {new Date(f.fecha_emision).toLocaleDateString('es-AR')}</span>
                            </td>
                            <td className="px-4 py-3 text-slate-500 hidden sm:table-cell">{new Date(f.fecha_emision).toLocaleDateString('es-AR')}</td>
                            <td className="px-4 py-3 text-right font-bold text-slate-800">{formatearMoneda(Number(f.saldo_pendiente))}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {h.facturasSeleccionadasIds.size > 0 && (
                <div className="flex justify-end pt-2">
                  <div className="bg-slate-800 text-white px-4 py-2 rounded-lg flex items-center gap-3">
                    <span className="text-xs text-slate-400 uppercase font-bold">Monto Bruto Total</span>
                    <span className="text-lg font-bold">{formatearMoneda(Number(h.montoAbonar))}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================================================== */}
          {/* PASO 3: ORIGEN DE FONDOS Y RETENCIONES (SIFÓN FISCAL) */}
          {/* ==================================================== */}
          {h.facturasSeleccionadasIds.size > 0 && (
            <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-300">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b pb-2">
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-xs">3</span>
                Liquidez y Sifón Fiscal
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">

                {/* 🏦 ORÍGEN CONTABLE */}
                <div className="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 h-full">
                  {/* 🌟 FIX ESCUDO RBAC: Si no es Interbanking y es ADMIN, muestra el banco */}
                  {!esInterbanking && isAdmin ? (
                    <>
                      <div>
                        <label className="text-xs font-bold text-slate-500 uppercase flex items-center gap-1 mb-1">
                          <Landmark className="w-4 h-4" /> Cuenta Origen (Débito Inmediato)
                        </label>
                        <select
                          value={h.cuentaOrigenId} onChange={(e) => h.setCuentaOrigenId(e.target.value)} required={!esInterbanking} disabled={h.isSubmitting}
                          className="w-full h-11 rounded-md border border-slate-300 px-3 text-sm focus:ring-2 focus:ring-indigo-500 bg-white"
                        >
                          <option value="">-- Seleccione Cuenta / Caja --</option>
                          {h.cuentas.map(c => (
                            <option key={c.id} value={c.id}>{c.banco} - {c.numero_cuenta} ({c.moneda})</option>
                          ))}
                        </select>
                      </div>

                      {monedaPago === "USD" && (
                        <div className="animate-in fade-in bg-blue-50 p-3 rounded-lg border border-blue-200 mt-2">
                          <label className="text-xs font-bold text-blue-800 uppercase">Cotización USD/ARS</label>
                          <input
                            type="number" step="0.01" min="1" required value={h.tipoCambio} onChange={(e) => h.setTipoCambio(e.target.value)} disabled={h.isSubmitting}
                            className="mt-1 w-full h-10 rounded-md border border-blue-300 px-3 text-sm focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      )}

                      {h.cuentaOrigenId && (
                        <div className="flex justify-between items-center text-xs p-3 mt-2 rounded bg-white border border-slate-200 shadow-sm">
                          <span className="text-slate-500 font-bold uppercase">Saldo Operativo Disp.</span>
                          <span className={`font-mono font-bold text-sm ${tieneSaldoInsuficienteLocal ? 'text-red-600' : 'text-emerald-600'}`}>
                            {formatearMoneda(saldoDisponible, monedaPago)}
                          </span>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="flex flex-col items-center justify-center text-center p-4 space-y-3 h-full">
                      <div className="p-3 bg-indigo-100 rounded-full text-indigo-600">
                        <Building className="w-6 h-6" />
                      </div>
                      <div>
                        <p className="font-bold text-slate-800">Orden Protegida</p>
                        <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                          La orden se guardará como Pendiente sin afectar el saldo de tesorería.<br/>
                          Aguardará autorización para liquidarse en el Hub Bancario Masivo.
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* ⚖️ MOTOR FISCAL (RETENCIONES EDITABLES) */}
                <div className={`border rounded-lg overflow-hidden shadow-sm transition-colors ${retencionesInvalidas ? 'border-red-300' : 'border-emerald-200'}`}>
                  <div className={`${retencionesInvalidas ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-100'} p-3 flex justify-between items-center border-b transition-colors`}>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox" id="chk-ret"
                        checked={h.aplicarRetenciones} onChange={(e) => h.setAplicarRetenciones(e.target.checked)} disabled={h.isSubmitting || h.retencionesSugeridas.length === 0}
                        className={`w-4 h-4 rounded focus:ring-emerald-500 border-slate-300 cursor-pointer ${retencionesInvalidas ? 'text-red-600' : 'text-emerald-600'}`}
                      />
                      <label htmlFor="chk-ret" className={`text-sm font-bold flex items-center cursor-pointer select-none ${retencionesInvalidas ? 'text-red-900' : 'text-emerald-900'}`}>
                        <Calculator className="w-4 h-4 mr-1.5" /> Retenciones Fiscales
                      </label>
                    </div>
                    {retencionesEditables.length > 0 && (
                      <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded flex items-center ${retencionesInvalidas ? 'bg-red-200 text-red-800' : 'bg-emerald-200 text-emerald-800'}`}>
                        <Edit3 className="w-3 h-3 mr-1" /> Editable
                      </span>
                    )}
                  </div>

                  <div className="bg-white p-0">
                    {h.isCalculatingTax ? (
                      <div className="flex h-20 items-center justify-center">
                        <Loader2 className="h-5 w-5 animate-spin text-emerald-500 mr-2" />
                        <span className="text-sm font-medium text-emerald-700">Simulando padrón...</span>
                      </div>
                    ) : retencionesEditables.length > 0 ? (
                      h.aplicarRetenciones ? (
                        <>
                          {retencionesEditables.map((ret, idx) => (
                            <div key={idx} className="flex justify-between items-center p-3 hover:bg-slate-50 border-b border-slate-100 transition-colors">
                              <div className="flex-1">
                                <p className="text-sm font-bold text-slate-800 flex items-center">
                                  {ret?.tipo_impuesto?.replace(/_/g, ' ') || "Impuesto"}
                                  <span className="ml-2 text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded border border-slate-200">
                                    {ret?.jurisdiccion || "N/A"}
                                  </span>
                                </p>
                                <p className="text-[11px] text-slate-500 font-medium mt-0.5">Sugerido ARCA: {ret?.alicuota_aplicada || 0}%</p>
                              </div>

                              <div className="relative w-32 ml-4 shrink-0">
                                <span className={`absolute left-3 top-2 font-medium text-sm ${retencionesInvalidas ? 'text-red-400' : 'text-slate-400'}`}>$</span>
                                <input
                                  type="number" step="0.01" min="0" disabled={h.isSubmitting}
                                  value={ret.monto_impuesto}
                                  onChange={(e) => handleRetencionChange(idx, e.target.value)}
                                  className={`w-full pl-7 pr-2 py-1.5 text-sm font-bold rounded-md focus:outline-none focus:ring-2 text-right transition-colors ${
                                    retencionesInvalidas ? 'text-red-700 bg-red-50 border border-red-300 focus:ring-red-500' : 'text-emerald-700 bg-emerald-50/50 border border-emerald-200 focus:ring-emerald-500'
                                  }`}
                                />
                              </div>
                            </div>
                          ))}
                          <div className="flex justify-between items-center p-3 bg-slate-50 border-b border-slate-200">
                            <span className="text-sm font-bold text-slate-700 uppercase tracking-wide">Total Deducciones</span>
                            <span className={`text-sm font-black ${retencionesInvalidas ? 'text-red-600' : 'text-emerald-600'}`}>
                              - {formatearMoneda(totalRetencionesEditadas, monedaPago)}
                            </span>
                          </div>
                        </>
                      ) : (
                        <div className="p-4 text-center text-sm font-medium text-slate-500">Retenciones desactivadas manualmente.</div>
                      )
                    ) : (
                      <div className="p-4 text-center text-sm font-medium text-slate-500">Proveedor exento o base no alcanzada.</div>
                    )}

                    <div className={`flex justify-between items-center p-4 transition-colors ${retencionesInvalidas ? 'bg-red-50' : 'bg-emerald-100/50'}`}>
                      <span className={`text-sm font-bold uppercase tracking-wide ${retencionesInvalidas ? 'text-red-800' : 'text-emerald-900'}`}>
                        Monto Neto a Pagar
                      </span>
                      <span className={`text-xl font-black ${retencionesInvalidas ? 'text-red-700' : 'text-emerald-700'}`}>
                        {formatearMoneda(netoFinalUI, monedaPago)}
                      </span>
                    </div>

                    {/* ALERTA DE BLOQUEO MATEMÁTICO */}
                    {retencionesInvalidas && (
                      <div className="p-3 bg-red-100 text-red-800 text-xs font-bold flex items-center border-t border-red-200">
                        <ShieldAlert className="w-5 h-5 mr-2 shrink-0 text-red-600" />
                        El monto de las retenciones ({formatearMoneda(totalRetencionesEditadas)}) no puede superar la deuda bruta a cancelar ({formatearMoneda(montoBaseArs)}).
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ALERTA DE FONDOS (Solo si NO es Interbanking y es Admin) */}
          {!esInterbanking && isAdmin && tieneSaldoInsuficienteLocal && !retencionesInvalidas && (
            <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg flex items-start gap-3 animate-in fade-in">
              <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5 text-red-600" />
              <p className="text-sm font-medium">La cuenta bancaria seleccionada no posee liquidez suficiente. Confirmar la operación forzará un giro en descubierto contable.</p>
            </div>
          )}

          {/* ============================== */}
          {/* FOOTER ACCIONES                */}
          {/* ============================== */}
          <div className="pt-6 border-t border-slate-200 flex justify-end">
            <button
              type="submit"
              disabled={h.isSubmitting || h.facturasSeleccionadasIds.size === 0 || (!esInterbanking && isAdmin && !h.cuentaOrigenId) || retencionesInvalidas}
              className="w-full sm:w-auto px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-md transition-all flex items-center justify-center disabled:opacity-50"
            >
              {h.isSubmitting ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Procesando...</>
              ) : retencionesInvalidas ? (
                <><ShieldAlert className="w-5 h-5 mr-2" /> Matemática Inválida</>
              ) : esInterbanking || !isAdmin ? (
                <><Layers className="w-5 h-5 mr-2" /> Guardar y Encolar para Loteo</>
              ) : (
                <><Send className="w-5 h-5 mr-2" /> Liquidar Pago Inmediato</>
              )}
            </button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

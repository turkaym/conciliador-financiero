import { useRef, useState } from "react";
import { UploadCloud, FileType, CheckCircle2, Loader2, X, AlertCircle, Plus, Landmark, ShieldCheck, Receipt, BookOpenCheck, DollarSign, Search, Layers } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useSifonFiscal } from "../hooks/useSifonFiscal";
import { useAuthStore } from "@/store/useAuthStore";

export default function SifonFiscalForm() {
  const h = useSifonFiscal();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const user = useAuthStore((state) => state.user);
  const isAdmin = ["admin", "editor", "dueño"].includes(user?.role?.toLowerCase() || "");

  const [searchProv, setSearchProv] = useState("");
  const [isProvDropdownOpen, setIsProvDropdownOpen] = useState(false);

  if (h.isLoadingMaestros || h.isLoadingCuentas) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
      </div>
    );
  }

  const filteredProv = h.proveedores.filter(p =>
    p.razon_social.toLowerCase().includes(searchProv.toLowerCase()) ||
    p.cuit.includes(searchProv)
  );

  const selectedProv = h.proveedores.find(p => p.id.toString() === h.proveedorId);

  return (
    <Card className="border-amber-200 shadow-lg max-w-2xl mx-auto overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 p-4 flex items-start space-x-3">
        <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
        <div>
          <h3 className="text-amber-800 font-bold text-sm">
            {isAdmin ? "Vía Rápida de Liquidación" : "Gestión de Gasto Operativo"}
          </h3>
          <p className="text-amber-700 text-xs mt-1 leading-relaxed">
            {isAdmin
              ? "Como Administrador, la operación se liquidará automáticamente sobre la cuenta seleccionada sin requerir ensamblaje posterior."
              : "Registra egresos de caja. Las solicitudes serán enviadas a la cola de autorización del Administrador corporativo."}
          </p>
        </div>
      </div>

      <CardContent className="p-4 sm:p-6">
        {h.formError && (
          <div className="mb-6 bg-red-50 text-red-700 p-3 rounded-md text-sm font-bold flex items-start space-x-2 border border-red-200 animate-in fade-in slide-in-from-top-2 duration-300 shadow-sm">
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <span>{h.formError}</span>
          </div>
        )}

        <form onSubmit={h.handleSubmit} className="space-y-6">

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* PROVEEDOR */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-slate-500 uppercase">Beneficiario</label>
                <button type="button" onClick={() => h.setIsAddingProv(!h.isAddingProv)} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center">
                  {h.isAddingProv ? "Cancelar" : <><Plus className="w-3 h-3 mr-1" /> Nuevo</>}
                </button>
              </div>

              {h.isAddingProv ? (
                <div className="bg-slate-50 border border-slate-200 rounded-md p-3 space-y-2 animate-in fade-in zoom-in-95 duration-200">
                  <input type="text" placeholder="CUIT (11 dígitos)" value={h.newProv.cuit} onChange={e => h.setNewProv({...h.newProv, cuit: e.target.value})} className="w-full h-8 text-sm rounded border-slate-300 px-2 outline-none" />
                  <input type="text" placeholder="Razón Social" value={h.newProv.razon_social} onChange={e => h.setNewProv({...h.newProv, razon_social: e.target.value})} className="w-full h-8 text-sm rounded border-slate-300 px-2 outline-none" />
                  <select value={h.newProv.condicion_fiscal} onChange={e => h.setNewProv({...h.newProv, condicion_fiscal: e.target.value})} className="w-full h-8 text-sm rounded border-slate-300 px-2 outline-none bg-white">
                    <option value="CONSUMIDOR_FINAL">Consumidor Final</option>
                    <option value="MONOTRIBUTO">Monotributo</option>
                    <option value="RESPONSABLE_INSCRIPTO">Responsable Inscripto</option>
                  </select>
                  <button type="button" onClick={h.handleCrearProveedor} disabled={h.isSubmitting} className="w-full h-8 bg-indigo-600 text-white rounded text-xs font-bold">Guardar</button>
                </div>
              ) : (
                <div className="relative">
                  <div className="relative flex items-center">
                    <Search className="absolute left-3 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      disabled={h.isSubmitting}
                      placeholder="Nombre o CUIT..."
                      className={`flex h-11 w-full rounded-md border border-slate-300 bg-white pl-9 pr-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-amber-500 disabled:opacity-50 ${!h.proveedorId && !isProvDropdownOpen ? 'border-amber-300 bg-amber-50/30' : ''}`}
                      value={isProvDropdownOpen ? searchProv : (selectedProv ? selectedProv.razon_social : "")}
                      onChange={(e) => {
                        setSearchProv(e.target.value);
                        setIsProvDropdownOpen(true);
                        h.setProveedorId("");
                      }}
                      onFocus={() => {
                        setIsProvDropdownOpen(true);
                        setSearchProv("");
                      }}
                      onBlur={() => setTimeout(() => setIsProvDropdownOpen(false), 200)}
                    />
                  </div>

                  {isProvDropdownOpen && (
                    <div className="absolute z-50 mt-1 w-full max-h-52 overflow-y-auto bg-white border border-slate-200 rounded-md shadow-lg">
                      {filteredProv.length > 0 ? filteredProv.map(p => (
                        <div
                          key={p.id}
                          className="px-3 py-2 cursor-pointer hover:bg-amber-50 border-b border-slate-50 last:border-0"
                          onClick={() => {
                            h.setProveedorId(p.id.toString());
                            setIsProvDropdownOpen(false);
                          }}
                        >
                          <div className="font-semibold text-slate-700 text-sm">{p.razon_social}</div>
                          <div className="text-xs text-slate-500">CUIT: {p.cuit}</div>
                        </div>
                      )) : (
                        <div className="px-3 py-4 text-sm text-center text-slate-500">No se encontraron resultados</div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* CONCEPTO */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-slate-500 uppercase">Concepto</label>
                <button type="button" onClick={() => h.setIsAddingConc(!h.isAddingConc)} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center">
                  {h.isAddingConc ? "Cancelar" : <><Plus className="w-3 h-3 mr-1" /> Nuevo</>}
                </button>
              </div>
              {h.isAddingConc ? (
                <div className="bg-slate-50 border border-slate-200 rounded-md p-3 space-y-2 animate-in fade-in zoom-in-95 duration-200">
                  <input type="text" placeholder="Código (Ej: 305)" value={h.newConc.codigo} onChange={e => h.setNewConc({...h.newConc, codigo: e.target.value})} className="w-full h-8 text-sm rounded border-slate-300 px-2 outline-none" />
                  <input type="text" placeholder="Nombre (Ej: Viáticos)" value={h.newConc.nombre_descriptivo} onChange={e => h.setNewConc({...h.newConc, nombre_descriptivo: e.target.value})} className="w-full h-8 text-sm rounded border-slate-300 px-2 outline-none" />
                  <button type="button" onClick={h.handleCrearConcepto} disabled={h.isSubmitting} className="w-full h-8 bg-indigo-600 text-white rounded text-xs font-bold">Guardar</button>
                </div>
              ) : (
                <select required disabled={h.isSubmitting} className="flex h-11 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm" value={h.conceptoId} onChange={(e) => h.setConceptoId(e.target.value)}>
                  <option value="">Seleccione concepto...</option>
                  {h.conceptos.map(c => (
                    <option key={c.id} value={c.id}>{c.codigo} - {c.nombre_descriptivo}</option>
                  ))}
                </select>
              )}
            </div>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <label className="text-xs uppercase font-bold text-slate-700 flex items-center">
              <BookOpenCheck className="w-4 h-4 mr-1 text-indigo-600" /> Imputación Contable *
            </label>
            <select
              required disabled={h.isSubmitting}
              className={`flex h-11 w-full rounded-md border ${!h.cuentaContableId ? 'border-amber-300 bg-amber-50/30' : 'border-slate-300 bg-white'} px-3 py-2 text-sm shadow-sm outline-none`}
              value={h.cuentaContableId} onChange={(e) => h.setCuentaContableId(e.target.value)}
            >
              <option value="">Seleccione el rubro contable correspondiente...</option>
              {h.cuentasImputables.map((cta) => (
                <option key={cta.id} value={cta.id}>{cta.codigo} - {cta.nombre}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-500 uppercase">Importe Total</label>
              <div className="flex shadow-sm rounded-md border border-slate-300 bg-white">
                <select
                  value={h.moneda}
                  onChange={(e) => h.setMoneda(e.target.value)}
                  disabled={!!h.cuentaId || h.isSubmitting}
                  className="h-11 rounded-l-md border-r border-slate-300 bg-slate-50 px-3 text-sm font-bold text-slate-700 outline-none"
                >
                  <option value="ARS">ARS ($)</option>
                  <option value="USD">USD (U$S)</option>
                </select>
                <input
                  type="number"
                  required min="0.01" step="0.01"
                  disabled={h.isSubmitting}
                  placeholder="0.00"
                  className="flex-1 h-11 bg-transparent px-3 py-2 text-lg font-bold text-slate-800 outline-none"
                  value={h.monto}
                  onChange={(e) => h.setMonto(e.target.value)}
                />
              </div>
            </div>

            {/* 🌟 FIX ESCUDO RBAC EN CONTROL DE CUENTAS */}
            {h.moneda === "USD" ? (
              <div className="space-y-1.5 animate-in slide-in-from-left-2 duration-300">
                <label className="text-xs font-semibold text-slate-500 uppercase flex items-center">
                  <DollarSign className="w-3 h-3 text-amber-600 mr-1" /> Cotización (TC) *
                </label>
                <input
                  type="number" required={h.moneda === "USD"} min="1" step="0.01" disabled={h.isSubmitting} placeholder="Ej: 1150.50"
                  className="w-full h-11 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900 outline-none"
                  value={h.tipoCambio} onChange={(e) => h.setTipoCambio(e.target.value)}
                />
              </div>
            ) : (
              isAdmin ? (
                <div className="space-y-1.5 animate-in slide-in-from-right-2 duration-300">
                  <label className="text-xs font-semibold text-slate-500 uppercase flex items-center">
                    <Landmark className="w-3 h-3 mr-1 text-emerald-600" /> Cuenta de Origen
                  </label>
                  <select required={isAdmin} disabled={h.isSubmitting} className="w-full h-11 rounded-md border border-emerald-300 bg-emerald-50 px-3 text-sm font-medium text-emerald-900 outline-none" value={h.cuentaId} onChange={(e) => h.setCuentaId(e.target.value)}>
                    <option value="">¿De dónde salió el dinero?</option>
                    {h.cuentas.map(b => (
                      <option key={b.id} value={b.id}>{b.nombre_banco} - {b.numero_cuenta} ({b.moneda})</option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="bg-slate-100 border border-slate-200 rounded-lg p-3 flex items-center gap-2 h-11 mt-6">
                  <Layers className="w-4 h-4 text-slate-500" />
                  <span className="text-xs font-medium text-slate-600">Amortización diferida (Requiere Admin)</span>
                </div>
              )
            )}
          </div>

          {isAdmin && h.moneda === "USD" && (
            <div className="space-y-1.5 pt-2 animate-in slide-in-from-top-2 duration-300">
              <label className="text-xs font-semibold text-slate-500 uppercase flex items-center">
                <Landmark className="w-3 h-3 mr-1 text-emerald-600" /> Cuenta de Origen
              </label>
              <select required={isAdmin} disabled={h.isSubmitting} className="w-full h-11 rounded-md border border-emerald-300 bg-emerald-50 px-3 text-sm font-medium text-emerald-900 outline-none" value={h.cuentaId} onChange={(e) => h.setCuentaId(e.target.value)}>
                <option value="">¿De dónde salió el dinero?</option>
                {h.cuentas.map(b => (
                  <option key={b.id} value={b.id}>{b.nombre_banco} - {b.numero_cuenta} ({b.moneda})</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <input type="checkbox" id="chk-fiscal" checked={h.requiereComprobante} onChange={(e) => h.setRequiereComprobante(e.target.checked)} className="w-4 h-4 rounded border-slate-300 text-indigo-600 cursor-pointer" />
            <label htmlFor="chk-fiscal" className="text-sm font-medium text-slate-700 flex-1 cursor-pointer flex items-center">
              Requieres Comprobante AFIP (Se esperará factura oficial)
            </label>
            {h.requiereComprobante ? <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" /> : <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />}
          </div>

          {!h.requiereComprobante && (
            <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-100 space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 uppercase flex items-center">
                  <Receipt className="w-3 h-3 mr-1 text-amber-600" /> Número de Ticket / Remito *
                </label>
                <input type="text" required={!h.requiereComprobante} disabled={h.isSubmitting} placeholder="Ej: 0001-00001234" className="flex h-11 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono outline-none" value={h.numeroTicket} onChange={(e) => h.setNumeroTicket(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 uppercase flex items-center">Fotografía del Resguardo *</label>
                {!h.selectedFile ? (
                  <div onClick={() => fileInputRef.current?.click()} className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer bg-white ${h.isCompressing ? 'border-amber-400' : 'border-slate-300 hover:border-amber-400'}`}>
                    {h.isCompressing ? <><Loader2 className="h-8 w-8 text-amber-500 animate-spin mb-2" /><p className="text-sm font-medium text-amber-700">Comprimiendo...</p></> : <><UploadCloud className="h-8 w-8 text-slate-400 mb-2" /><p className="text-sm font-medium text-slate-700">Toca para abrir cámara o galería</p></>}
                    <input type="file" ref={fileInputRef} accept="image/*" capture="environment" className="hidden" onChange={h.handleFileChange} disabled={h.isCompressing || h.isSubmitting} />
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-xl p-3 flex items-center justify-between bg-white shadow-sm">
                    <div className="flex items-center space-x-3 overflow-hidden">
                      <div className="h-12 w-12 rounded-lg bg-slate-100 flex-shrink-0 overflow-hidden border border-slate-200">
                        {h.previewUrl ? <img src={h.previewUrl} alt="Preview" className="h-full w-full object-cover" /> : <FileType className="h-6 w-6 m-3 text-slate-400" />}
                      </div>
                      <div className="truncate">
                        <p className="text-sm font-semibold text-slate-700 truncate">{h.selectedFile.name}</p>
                      </div>
                    </div>
                    <button type="button" onClick={h.clearFile} disabled={h.isSubmitting} className="p-2 text-slate-400 hover:text-red-500"><X className="h-5 w-5" /></button>
                  </div>
                )}
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={h.isSubmitting || h.isCompressing}
            style={{ backgroundColor: h.success ? '#10b981' : '#4f46e5', color: 'white', opacity: (h.isSubmitting || h.isCompressing) ? 0.6 : 1 }}
            className="w-full h-12 text-md font-bold rounded-md shadow-md flex items-center justify-center transition-all disabled:cursor-not-allowed"
          >
            {h.isSubmitting ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Procesando...</> : h.success ? <><CheckCircle2 className="w-5 h-5 mr-2" /> Gasto Registrado Exitosamente</> : isAdmin ? "Registrar y Liquidar Gasto" : "Enviar a Autorización"}
          </button>
        </form>
      </CardContent>
    </Card>
  );
}

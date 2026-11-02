import { useEffect, useState, useMemo } from "react"
import { useAuthStore } from "@/store/useAuthStore"
import { useBancos } from "../features/bancos/hooks/useBancos"
import { NuevaCuentaModal } from "../features/bancos/components/NuevaCuentaModal"
import { MovimientosTable } from "../features/bancos/components/MovimientosTable"
import { NuevoMovimientoModal } from "../features/bancos/components/NuevoMovimientoModal"
import { ImportarExtractoModal } from "../features/bancos/components/ImportarExtractoModal"
import { BandejaAprobaciones } from "../features/bancos/components/BandejaAprobaciones"
import DataGuard from "@/components/ui/DataGuard"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { AlertCircle, Building2, Wallet, Landmark, History, RefreshCw, Loader2, ShieldAlert, CreditCard } from "lucide-react"

export default function BancosPage() {
  const { entidadActiva, user } = useAuthStore()

  // 🌟 FIX FASE 3: Extraemos las variables del motor de clearing
  const {
    cuentas, movimientos, isLoadingCuentas, isLoadingMovs, isPolling, hasMoreMovs, errorCuentas, errorMovs, globalMessage, setErrorMovs, fetchCuentas, createCuenta, fetchMovimientos, createMovimiento, clearMovimientos, uploadExtracto, cancelarIngesta, procesarPreVuelo, confirmarIngesta,
    resolverAprobacion,
    proveedoresClearing, fetchProveedoresClearing
  } = useBancos()

  const [selectedCuentaId, setSelectedCuentaId] = useState<string>("")
  const [page, setPage] = useState(0)

  const [activeView, setActiveView] = useState<'historial' | 'aprobaciones'>('historial')

  // 🌟 FIX FASE C: Uso estricto del discriminador de tipo
  const movimientosPendientes = useMemo(() =>
    movimientos.filter(m => {
      const isSolicitud = m.tipo_registro === 'SOLICITUD';
      const isPending = m.estado === 'PENDING_APPROVAL';
      const isAdmin = user?.role === 'admin' || user?.role === 'dueño';
      return isSolicitud && isPending && isAdmin;
    }),
  [movimientos, user])

  const movimientosHistorial = useMemo(() =>
    movimientos.filter(m => m.tipo_registro === 'MOVIMIENTO'),
  [movimientos])

  const isSyncing = isLoadingCuentas || isLoadingMovs
  const storageKey = `conciliador_banco_activo_${entidadActiva?.id}`;

  useEffect(() => {
    if (entidadActiva?.id) {
      setSelectedCuentaId("")
      setPage(0)
      clearMovimientos()
      fetchCuentas()
      setActiveView('historial')
    }
  }, [entidadActiva?.id])

  useEffect(() => {
    if (!isLoadingCuentas && cuentas.length > 0 && !selectedCuentaId) {
      const savedId = localStorage.getItem(storageKey);

      if (savedId && cuentas.some(c => c.id.toString() === savedId)) {
        setSelectedCuentaId(savedId);
      } else {
        setSelectedCuentaId(cuentas[0].id.toString());
      }
    }
  }, [cuentas, selectedCuentaId, isLoadingCuentas, storageKey])

  useEffect(() => {
    if (!isLoadingCuentas && selectedCuentaId && cuentas.length > 0) {
      const cuentaValida = cuentas.some(c => c.id.toString() === selectedCuentaId);

      if (cuentaValida) {
        localStorage.setItem(storageKey, selectedCuentaId);
        fetchMovimientos(selectedCuentaId, page);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCuentaId, page, cuentas, isLoadingCuentas, storageKey])

  const handleDataRefresh = () => {
    fetchCuentas()
    if (page === 0) fetchMovimientos(selectedCuentaId, 0)
    else setPage(0)
  }

  const handleResolucion = async (id: number, accion: 'aprobar' | 'rechazar', motivoRechazo?: string) => {
    if (resolverAprobacion) {
      const exito = await resolverAprobacion(id, accion, motivoRechazo);
      if (exito) handleDataRefresh();
    }
  }

  if (!entidadActiva) {
    return (
      <div className="flex flex-col items-center justify-center h-[75vh] animate-in zoom-in-95 duration-300">
        <div className="bg-indigo-50 p-6 rounded-full mb-6 ring-8 ring-indigo-50/50">
          <Building2 className="h-14 w-14 text-indigo-500" />
        </div>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-3 tracking-tight">Identificación Requerida</h2>
        <p className="text-slate-500 max-w-sm text-center leading-relaxed">
          Para acceder a la tesorería de <span className="text-indigo-600 font-semibold">Conciliador</span>, seleccioná una empresa en el panel superior.
        </p>
      </div>
    )
  }

  const cuentaSeleccionadaData = cuentas.find(c => c.id.toString() === selectedCuentaId)

  return (
    <div className="max-w-[1600px] mx-auto space-y-8 pb-10 animate-in fade-in slide-in-from-bottom-4 duration-700">

      {globalMessage && (
        <div className={`fixed top-20 right-8 z-50 p-4 rounded-xl shadow-2xl border-l-4 flex items-center gap-3 animate-in slide-in-from-right-10 duration-300 ${
          globalMessage.type === 'success' ? 'bg-white border-emerald-500 text-emerald-900' : 'bg-white border-red-500 text-red-900'
        }`}>
          <div className={`p-2 rounded-full ${globalMessage.type === 'success' ? 'bg-emerald-100' : 'bg-red-100'}`}>
            <AlertCircle className="h-5 w-5" />
          </div>
          <p className="text-sm font-semibold pr-4">{globalMessage.text}</p>
        </div>
      )}

      <DataGuard>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          <div className="lg:col-span-2 flex flex-col justify-between p-7 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden relative group">
            <div className="absolute top-0 right-0 -mt-4 -mr-4 h-32 w-32 bg-indigo-50 rounded-full opacity-50 group-hover:scale-110 transition-transform duration-500" />

            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-3 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-200 text-white">
                  <Landmark className="h-6 w-6" />
                </div>
                <div>
                  <h1 className="text-2xl font-black text-slate-900 tracking-tight">Tesorería Central</h1>
                  <p className="text-slate-400 text-sm font-medium">Empresa: {entidadActiva.nombre_fantasia}</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4">
                <div className="w-full sm:w-[340px]">
                  <Label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5 block ml-1">Seleccionar Fuente de Fondos</Label>
                  <Select value={selectedCuentaId} onValueChange={(val) => { setSelectedCuentaId(val); setPage(0); }}>
                    <SelectTrigger className="h-12 bg-slate-50 border-slate-200 rounded-xl focus:ring-indigo-500 transition-all font-semibold" disabled={isPolling}>
                      <SelectValue placeholder="Cargando canales..." />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl shadow-xl border-slate-100">
                      {cuentas.map(cuenta => (
                        <SelectItem key={cuenta.id} value={cuenta.id.toString()} className="focus:bg-indigo-50 rounded-lg py-3 px-4">
                          <div className="flex items-center gap-2">
                            {/* 🌟 NUEVO: Indicador visual B2B */}
                            {cuenta.tipo_canal === 'PASARELA' ? (
                              <CreditCard className="h-4 w-4 text-indigo-500 mr-1" />
                            ) : (
                              <Landmark className="h-4 w-4 text-slate-400 mr-1" />
                            )}
                            <span className="font-bold">{cuenta.banco}</span>
                            <span className="text-slate-400 font-normal">| {cuenta.numero_cuenta}</span>
                            {/* 🌟 NUEVO: Badge de Pasarela */}
                            {cuenta.tipo_canal === 'PASARELA' && (
                              <span className="ml-2 text-[9px] font-bold uppercase bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                                Pasarela
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="pt-5">
                  {/* 🌟 FIX FASE 3: Pasamos props de proveedores y trigger al hijo */}
                  <NuevaCuentaModal
                    isLoading={isLoadingCuentas || isPolling}
                    errorMsg={errorCuentas}
                    onSubmit={createCuenta}
                    proveedores={proveedoresClearing}
                    onOpen={fetchProveedoresClearing}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 rounded-2xl p-7 text-white shadow-2xl relative overflow-hidden flex flex-col justify-between min-h-[220px]">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Wallet className="h-24 w-24" />
            </div>

            <div>
              <p className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Disponibilidad Actual</p>
              {cuentaSeleccionadaData ? (
                <div className="space-y-1">
                  <h2 className="text-4xl font-black tracking-tighter">
                    {new Intl.NumberFormat('es-AR', {
                      style: 'currency',
                      currency: cuentaSeleccionadaData.moneda || 'ARS'
                    }).format(Number(cuentaSeleccionadaData.saldo_actual) - Number(cuentaSeleccionadaData.saldo_retenido || 0))}
                  </h2>

                  {Number(cuentaSeleccionadaData.saldo_retenido) > 0 && (
                    <p className="text-xs text-amber-400 font-bold tracking-wide flex items-center gap-1.5 pb-2">
                      <ShieldAlert className="h-3 w-3" />
                      {new Intl.NumberFormat('es-AR', { style: 'currency', currency: cuentaSeleccionadaData.moneda || 'ARS' }).format(Number(cuentaSeleccionadaData.saldo_retenido))} en Cuarentena
                    </p>
                  )}

                  <div className="flex items-center gap-2 text-indigo-400 text-xs font-mono bg-indigo-500/10 py-1 px-2 rounded-md w-fit border border-indigo-500/20">
                    {/* 🌟 FIX: Mostramos si es Banco o Pasarela */}
                    <span className="opacity-70">{cuentaSeleccionadaData.tipo_canal === 'PASARELA' ? 'IDENTIFICADOR:' : 'CBU:'}</span> {cuentaSeleccionadaData.cbu || 'N/A'}
                  </div>
                </div>
              ) : (
                <p className="text-slate-500 italic">No se ha detectado saldo para esta cuenta.</p>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-white/10 pt-4 mt-4">
              <div className="flex items-center gap-2">
                {isSyncing || isPolling ? (
                  <>
                    <Loader2 className="h-3 w-3 text-amber-500 animate-spin" />
                    <span className="text-[10px] font-bold text-amber-500 uppercase tracking-widest">
                      {isPolling ? 'Procesando Extracto...' : 'Actualizando...'}
                    </span>
                  </>
                ) : (
                  <>
                    <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Sincronizado</span>
                  </>
                )}
              </div>
              <Landmark className="h-4 w-4 text-slate-600" />
            </div>
          </div>
        </div>

        <Card className="rounded-2xl border-slate-200 overflow-hidden shadow-xl bg-white mt-6">
          <div className="bg-slate-50/50 border-b border-slate-200 p-4 flex flex-col lg:flex-row justify-between items-center gap-4">

            <div className="flex bg-slate-200/60 p-1 rounded-xl w-full lg:w-auto">
              <button
                onClick={() => setActiveView('historial')}
                className={`flex-1 lg:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg font-bold text-sm transition-all ${activeView === 'historial' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <History className="h-4 w-4" /> Historial
              </button>

              {(user?.role === 'admin' || user?.role === 'dueño') && (
                <button
                  onClick={() => setActiveView('aprobaciones')}
                  className={`flex-1 lg:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg font-bold text-sm transition-all ${activeView === 'aprobaciones' ? 'bg-white text-amber-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  <ShieldAlert className="h-4 w-4" /> Autorizaciones
                  {movimientosPendientes.length > 0 && (
                    <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full text-[10px] ml-1">
                      {movimientosPendientes.length}
                    </span>
                  )}
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              {selectedCuentaId && (
                <>
                  <Button variant="outline" size="sm" className="bg-white" onClick={handleDataRefresh} disabled={isSyncing || isPolling} title="Actualizar datos">
                    <RefreshCw className={`h-4 w-4 sm:mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
                    <span className="hidden sm:inline">Actualizar</span>
                  </Button>

                  <ImportarExtractoModal
                    cuentaId={selectedCuentaId} isLoading={isLoadingMovs || isPolling} errorMsg={errorMovs}
                    onSubmit={uploadExtracto} onAnalyzeFormat={procesarPreVuelo} onConfirmDynamic={confirmarIngesta}
                    isPolling={isPolling} onClearError={() => setErrorMovs(null)} onCancelProcess={cancelarIngesta}
                    statusMsg={cuentaSeleccionadaData?.status_msg} progress={cuentaSeleccionadaData?.progress}
                  />
                  <NuevoMovimientoModal
                    cuentaId={selectedCuentaId} isLoading={isLoadingMovs || isPolling} errorMsg={errorMovs}
                    onSubmit={async (payload) => {
                      const success = await createMovimiento(payload);
                      if (success) handleDataRefresh();
                      return success;
                    }}
                  />
                </>
              )}
            </div>
          </div>

          <div className="p-0 bg-white">
            {!selectedCuentaId ? (
              <div className="py-24 flex flex-col items-center justify-center text-center px-6">
                <div className="bg-slate-50 p-6 rounded-3xl border border-dashed border-slate-200 mb-4 hover:bg-slate-100 transition-colors">
                  <Landmark className="h-10 w-10 text-slate-300" />
                </div>
                <p className="text-slate-500 font-medium max-w-[280px]">Seleccioná un canal bancario para auditar los flujos de caja.</p>
              </div>
            ) : activeView === 'historial' ? (
              <MovimientosTable
                movimientos={movimientosHistorial}
                isLoading={isLoadingMovs}
                isPolling={isPolling}
                selectedCuentaId={selectedCuentaId}
                page={page}
                hasMore={hasMoreMovs}
                onRefresh={() => fetchMovimientos(selectedCuentaId, page)}
                onPageChange={setPage}
              />
            ) : (
              <BandejaAprobaciones
                pendientes={movimientosPendientes}
                isLoading={isLoadingMovs}
                onResolver={handleResolucion}
              />
            )}
          </div>
        </Card>
      </DataGuard>
    </div>
  )
}
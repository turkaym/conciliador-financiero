import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Loader2, Link2, AlertCircle, AlertTriangle, CheckCircle2 } from "lucide-react"
import { useAuthStore } from "@/store/useAuthStore"
import { useConciliacion, type RetencionSufridaPayload } from "../features/conciliacion/hooks/useConciliacion"
import DataGuard from "@/components/ui/DataGuard"

// Importamos la arquitectura desacoplada
import { AjusteFiscalModal } from "@/features/conciliacion/components/AjusteFiscalModal"
import { ConciliacionHeader } from "@/features/conciliacion/components/ConciliacionHeader"
import { ColumnaExtracto } from "@/features/conciliacion/components/ColumnaExtracto"
import { ColumnaComprobantes } from "@/features/conciliacion/components/ColumnaComprobantes"
import { HistorialAuditoria } from "@/features/conciliacion/components/HistorialAuditoria"

class CrashCatcher extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: any}> {
  constructor(props: {children: React.ReactNode}) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-red-50 text-red-900 h-full overflow-auto rounded-xl border border-red-200 m-4">
          <h1 className="font-black text-2xl mb-4 flex items-center gap-2"><AlertTriangle/> Error Letal en Renderizado</h1>
          <p className="mb-4 text-sm font-medium">React abortó la carga de Conciliación por este motivo exacto:</p>
          <pre className="text-xs bg-white p-4 rounded border border-red-200 whitespace-pre-wrap">{this.state.error?.toString()}\n{this.state.error?.stack}</pre>
        </div>
      )
    }
    return this.props.children
  }
}

function ConciliacionContenido() {
  const { entidadActiva } = useAuthStore()
  const {
    data, historyData, isLoading, isProcessing, error,
    fetchStatus, fetchHistory, triggerAutoMatch, triggerManualMatch, triggerUnmatch
  } = useConciliacion()

  const [activeTab, setActiveTab] = useState<'PENDIENTES' | 'HISTORIAL'>('PENDIENTES')
  const [flowTab, setFlowTab] = useState<'COBROS' | 'PAGOS'>('COBROS')
  const [mobileStep, setMobileStep] = useState<1 | 2>(1)

  const [selectedMovs, setSelectedMovs] = useState<number[]>([])
  // 🌟 FIX POLIMORFISMO: Tipado estricto a string[] para alinear con el Backend (CBT-123, OP-45)
  const [selectedCbtes, setSelectedCbtes] = useState<string[]>([])

  const [modalAjusteOpen, setModalAjusteOpen] = useState(false)
  const [diferenciaCalculada, setDiferenciaCalculada] = useState(0)

  useEffect(() => {
    if (entidadActiva) {
      fetchStatus()
      fetchHistory()
      clearSelection()
    }
  }, [entidadActiva, fetchStatus, fetchHistory])

  useEffect(() => {
    clearSelection()
  }, [flowTab, activeTab])

  const handleSelectMov = (id: number) => setSelectedMovs(prev => prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id])

  // 🌟 FIX POLIMORFISMO: Exige string como argumento
  const handleSelectCbte = (id: string) => setSelectedCbtes(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id])

  const clearSelection = () => { setSelectedMovs([]); setSelectedCbtes([]); setMobileStep(1); setModalAjusteOpen(false) }

  const pendingsNode = data?.pendings || {}
  const currentFlowData = (flowTab === 'COBROS' ? pendingsNode.ar : pendingsNode.ap) || {}

  const movimientosPendientes = currentFlowData.bank_movements || []
  const comprobantesPendientes = currentFlowData.invoices || []
  const historial = historyData?.items || []

  const preVincular = () => {
    if (selectedMovs.length === 0 || selectedCbtes.length === 0) return

    let sumaBanco = 0
    selectedMovs.forEach(id => {
      const m = movimientosPendientes.find(x => String(x.id) === String(id))
      if (m) sumaBanco += Math.abs(parseFloat(String(m.monto)) || 0)
    })

    let sumaCbtes = 0
    selectedCbtes.forEach(id => {
      const c = comprobantesPendientes.find(x => String(x.id) === String(id))
      if (c) sumaCbtes += Math.abs(parseFloat(String(c.monto)) || 0)
    })

    const diff = Number((sumaCbtes - sumaBanco).toFixed(2))

    if (diff > 0) {
      setDiferenciaCalculada(diff)
      setModalAjusteOpen(true)
    } else {
      ejecutarVinculacion(undefined)
    }
  }

  const ejecutarVinculacion = async (ajuste?: RetencionSufridaPayload) => {
    const success = await triggerManualMatch(selectedMovs, selectedCbtes, ajuste ? [ajuste] : undefined)
    if (success) {
      clearSelection()
      fetchStatus()
      fetchHistory()
    }
  }

  const handleDesconciliar = async (matchId: number) => {
    if (window.confirm("¿Estás seguro de deshacer esta conciliación? Los saldos volverán a las cuentas origen.")) {
      await triggerUnmatch(matchId)
    }
  }

  if (!entidadActiva) {
    return <div className="flex items-center justify-center h-full"><p className="text-slate-500">Seleccioná una empresa para operar.</p></div>
  }

  return (
    <div className="flex flex-col h-full space-y-4 max-w-[1600px] mx-auto relative pb-24">
      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm font-medium flex items-center gap-2 border border-red-200 flex-shrink-0">
          <AlertCircle className="h-4 w-4 shrink-0" /><span>{error}</span>
        </div>
      )}

      <ConciliacionHeader
        activeTab={activeTab} setActiveTab={setActiveTab}
        flowTab={flowTab} setFlowTab={setFlowTab}
        triggerAutoMatch={triggerAutoMatch}
        isLoading={isLoading} isProcessing={isProcessing}
      />

      <DataGuard isLoading={isLoading && !isProcessing}>
        <TooltipProvider delayDuration={200}>

          {activeTab === 'PENDIENTES' && (
            <div className="flex flex-col flex-1 min-h-0">
              {/* Selector UX Mobile Integrado con Telemetría - Modificado a md:hidden */}
              <div className="flex md:hidden bg-slate-100 p-1 rounded-xl border border-slate-200 mb-3 shrink-0">
                <button
                  type="button" onClick={() => setMobileStep(1)}
                  className={`flex-1 flex items-center justify-center gap-1 py-2 text-xs font-black tracking-wide rounded-lg transition-all ${mobileStep === 1 ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  🏦 Extracto
                  {selectedMovs.length > 0 ? (
                    <span className="bg-indigo-600 text-white text-[10px] px-1.5 py-0.5 rounded-full leading-none flex items-center h-4">{selectedMovs.length}</span>
                  ) : (
                    <span className="opacity-70">({movimientosPendientes.length})</span>
                  )}
                </button>
                <button
                  type="button" onClick={() => setMobileStep(2)}
                  className={`flex-1 flex items-center justify-center gap-1 py-2 text-xs font-black tracking-wide rounded-lg transition-all ${mobileStep === 2 ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  📄 Cbtes
                  {selectedCbtes.length > 0 ? (
                    <span className="bg-emerald-500 text-white text-[10px] px-1.5 py-0.5 rounded-full leading-none flex items-center h-4">{selectedCbtes.length}</span>
                  ) : (
                    <span className="opacity-70">({comprobantesPendientes.length})</span>
                  )}
                </button>
              </div>

              {/* Ajuste de Breakpoint a md:grid-cols-2 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
                <ColumnaExtracto
                  movimientosPendientes={movimientosPendientes}
                  selectedMovs={selectedMovs}
                  handleSelectMov={handleSelectMov}
                  flowTab={flowTab}
                  mobileStep={mobileStep}
                />

                <ColumnaComprobantes
                  comprobantesPendientes={comprobantesPendientes}
                  selectedCbtes={selectedCbtes}
                  handleSelectCbte={handleSelectCbte}
                  flowTab={flowTab}
                  mobileStep={mobileStep}
                />
              </div>

              {/* PILL UX */}
              <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-1.5rem)] sm:w-max bg-white/95 backdrop-blur-xl border border-slate-200 p-3 sm:px-6 sm:py-3 shadow-[0_10px_40px_-10px_rgba(0,0,0,0.3)] rounded-2xl sm:rounded-full z-[90] transition-all">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-6 w-full">
                  <div className="hidden sm:flex items-center gap-3 pr-4 border-r border-slate-200">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 font-bold text-slate-600"><CheckCircle2 className="w-5 h-5"/></span>
                    <span className="text-sm font-bold text-slate-700 whitespace-nowrap">
                      {selectedMovs.length} Seleccionado(s)
                    </span>
                  </div>

                  <div className="flex w-full sm:w-auto items-center justify-between sm:justify-center gap-2">
                    <Button onClick={clearSelection} variant="ghost" size="sm" className="text-slate-500 rounded-full">
                      Cancelar
                    </Button>
                    <Button
                      onClick={preVincular}
                      disabled={selectedMovs.length === 0 || selectedCbtes.length === 0 || isProcessing}
                      className="bg-emerald-500 hover:bg-emerald-600 text-white font-black rounded-full px-6 shadow-md transition-transform active:scale-95 text-xs uppercase tracking-wider"
                    >
                      {isProcessing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Link2 className="w-4 h-4 mr-2" />}
                      Vincular Lote
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'HISTORIAL' && (
            <HistorialAuditoria historial={historial} handleDesconciliar={handleDesconciliar} />
          )}
        </TooltipProvider>
      </DataGuard>

      <AjusteFiscalModal
        isOpen={modalAjusteOpen} onClose={() => setModalAjusteOpen(false)}
        diferencia={diferenciaCalculada} isProcessing={isProcessing}
        onSubmit={(ajuste) => ejecutarVinculacion(ajuste)}
      />
    </div>
  )
}

export default function ConciliacionPage() {
  return (
    <CrashCatcher>
      <ConciliacionContenido />
    </CrashCatcher>
  )
}
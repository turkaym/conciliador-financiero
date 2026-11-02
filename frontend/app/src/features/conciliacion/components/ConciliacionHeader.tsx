import { Button } from "@/components/ui/button"
import { History, Loader2, ArrowRightLeft } from "lucide-react"

interface ConciliacionHeaderProps {
  activeTab: 'PENDIENTES' | 'HISTORIAL'
  setActiveTab: (tab: 'PENDIENTES' | 'HISTORIAL') => void
  flowTab: 'COBROS' | 'PAGOS'
  setFlowTab: (flow: 'COBROS' | 'PAGOS') => void
  triggerAutoMatch: () => void
  isLoading: boolean
  isProcessing: boolean
}

export function ConciliacionHeader({
  activeTab,
  setActiveTab,
  flowTab,
  setFlowTab,
  triggerAutoMatch,
  isLoading,
  isProcessing
}: ConciliacionHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200 gap-4 flex-shrink-0">
      <div className="space-y-2 w-full sm:w-auto">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800 tracking-tight">Conciliación Bancaria</h1>
        <div className="flex gap-2">
          <Button
            variant={activeTab === 'PENDIENTES' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('PENDIENTES')}
            className={activeTab === 'PENDIENTES' ? 'bg-slate-800' : ''}
          >
            Pendientes
          </Button>
          <Button
            variant={activeTab === 'HISTORIAL' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('HISTORIAL')}
            className={activeTab === 'HISTORIAL' ? 'bg-indigo-600 hover:bg-indigo-700' : ''}
          >
            <History className="w-4 h-4 mr-2" /> Auditoría Forense
          </Button>
        </div>
      </div>

      {activeTab === 'PENDIENTES' && (
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto items-center">
          <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shadow-inner w-full sm:w-auto">
            <button
              type="button"
              onClick={() => setFlowTab('COBROS')}
              className={`px-6 py-2 rounded-lg text-xs font-black tracking-wide transition-all ${flowTab === 'COBROS' ? "bg-white text-emerald-700 shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
            >
              💰 COBROS (AR)
            </button>
            <button
              type="button"
              onClick={() => setFlowTab('PAGOS')}
              className={`px-6 py-2 rounded-lg text-xs font-black tracking-wide transition-all ${flowTab === 'PAGOS' ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
            >
              💸 PAGOS (AP)
            </button>
          </div>

          <Button
            onClick={() => triggerAutoMatch()}
            disabled={isLoading || isProcessing}
            className="bg-indigo-600 hover:bg-indigo-700 shadow-sm w-full sm:w-auto"
          >
            {isProcessing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowRightLeft className="w-4 h-4 mr-2" />}
            Ejecutar Motor
          </Button>
        </div>
      )}
    </div>
  )
}
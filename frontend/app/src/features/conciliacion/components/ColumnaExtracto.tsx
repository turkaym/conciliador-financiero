import { useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Calendar, Hash } from "lucide-react"
import { useVirtualizer } from "@tanstack/react-virtual"

// Ruta corregida apuntando a utils
import { formatearMonedaSegura, formatFechaUI } from "../utils/formatters"

interface MovimientoBancario {
  id: number
  fecha: string
  referencia: string
  concepto: string
  monto: number
  moneda: string
}

interface ColumnaExtractoProps {
  movimientosPendientes: MovimientoBancario[]
  selectedMovs: number[]
  handleSelectMov: (id: number) => void
  flowTab: 'COBROS' | 'PAGOS'
  mobileStep: number
}

export function ColumnaExtracto({
  movimientosPendientes,
  selectedMovs,
  handleSelectMov,
  flowTab,
  mobileStep
}: ColumnaExtractoProps) {
  const movParentRef = useRef<HTMLDivElement>(null)

  const movVirtualizer = useVirtualizer({
    count: movimientosPendientes.length,
    getScrollElement: () => movParentRef.current,
    estimateSize: () => 92,
    overscan: 5,
  })

  return (
    <div className={`flex-col h-full min-h-0 ${mobileStep === 1 ? 'flex' : 'hidden md:flex'}`}>
      <Card className="flex flex-col flex-1 border-indigo-100 shadow-sm overflow-hidden min-h-0 min-w-0">
        <CardHeader className="bg-indigo-50/80 pb-3 border-b border-indigo-100 flex-shrink-0">
          <CardTitle className="text-md font-bold text-indigo-900 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {flowTab === 'COBROS' ? <TrendingUp className="w-4 h-4 text-emerald-600" /> : <TrendingDown className="w-4 h-4 text-indigo-600" />}
              {flowTab === 'COBROS' ? "Ingresos de Caja / Extracto" : "Egresos de Caja / Extracto"}
              <span className="text-xs font-normal text-slate-500">({movimientosPendientes.length})</span>
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent ref={movParentRef} className="flex-1 p-0 bg-white overflow-y-auto relative pb-24">
          {movimientosPendientes.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-slate-400">
              No hay movimientos pendientes en este flujo.
            </div>
          ) : (
            <div role="table" style={{ height: `${movVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
              {movVirtualizer.getVirtualItems().map((virtualRow) => {
                const mov = movimientosPendientes[virtualRow.index]
                if (!mov) return null

                const isSelected = selectedMovs.includes(mov.id)
                return (
                  <div
                    key={virtualRow.key}
                    onClick={() => handleSelectMov(mov.id)}
                    className={`absolute top-0 left-0 w-full flex items-center px-4 cursor-pointer transition-all border-b border-slate-100 ${isSelected ? 'bg-indigo-50/70 border-l-4 border-l-indigo-600' : 'hover:bg-slate-50 border-l-4 border-l-transparent'}`}
                    style={{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                  >
                    <input type="checkbox" checked={isSelected} readOnly className="w-4 h-4 text-indigo-600 rounded mr-4" />

                    <div className="flex-1 min-w-0 py-2 space-y-1">
                      <div className="flex items-center text-[11px] text-slate-400 font-semibold gap-3">
                        <span className="flex items-center gap-1 font-mono"><Calendar className="w-3 h-3"/> {formatFechaUI(mov.fecha)}</span>
                        <span className="flex items-center gap-1 bg-slate-100 px-1.5 py-0.5 rounded text-slate-600"><Hash className="w-3 h-3"/> Ref: {mov.referencia}</span>
                      </div>
                      <div className="text-sm font-bold text-slate-800 truncate" title={mov.concepto}>
                        {mov.concepto}
                      </div>
                    </div>
                    <div className={`w-28 text-right font-black text-sm flex-shrink-0 pl-2 ${flowTab === 'COBROS' ? "text-emerald-600" : "text-slate-700"}`}>
                      {flowTab === 'PAGOS' ? "-" : ""}{formatearMonedaSegura(mov.monto, mov.moneda)}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
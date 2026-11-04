import { useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FileText, Calendar, User, ArrowDownRight, ArrowUpRight, CheckCircle2 } from "lucide-react"
import { useVirtualizer } from "@tanstack/react-virtual"

// Import correcto hacia la carpeta utils
import { formatearMonedaSegura, formatFechaUI } from "../utils/formatters"
import type { IncompleteInvoice } from "../hooks/useConciliacion"

interface ColumnaComprobantesProps {
  comprobantesPendientes: IncompleteInvoice[]
  selectedCbtes: string[]
  handleSelectCbte: (id: string) => void
  flowTab: "COBROS" | "PAGOS"
  mobileStep: number
}

// Helper para estilizar el badge según el tipo de documento
const getDocumentBadge = (clase: string = "FACTURA") => {
  switch (clase) {
    case "NOTA_CREDITO":
      return { label: "N. Crédito", classes: "bg-blue-100 text-blue-800 border-blue-200", icon: <ArrowDownRight className="w-3 h-3 mr-0.5" /> };
    case "NOTA_DEBITO":
      return { label: "N. Débito", classes: "bg-amber-100 text-amber-800 border-amber-200", icon: <ArrowUpRight className="w-3 h-3 mr-0.5" /> };
    case "RECIBO":
      return { label: "Recibo/Anticipo", classes: "bg-emerald-100 text-emerald-800 border-emerald-200", icon: <FileText className="w-3 h-3 mr-0.5" /> };
    case "ORDEN DE PAGO":
      // 🌟 FIX: Nuevo estilo para las Órdenes de Pago Unificadas
      return { label: "Orden Pago", classes: "bg-indigo-100 text-indigo-800 border-indigo-200", icon: <CheckCircle2 className="w-3 h-3 mr-0.5" /> };
    default:
      return { label: "Factura", classes: "bg-slate-100 text-slate-600 border-slate-200", icon: null };
  }
}

export function ColumnaComprobantes({
  comprobantesPendientes,
  selectedCbtes,
  handleSelectCbte,
  flowTab,
  mobileStep
}: ColumnaComprobantesProps) {
  const cbteParentRef = useRef<HTMLDivElement>(null)
  const cbteVirtualizer = useVirtualizer({
    count: comprobantesPendientes.length,
    getScrollElement: () => cbteParentRef.current,
    estimateSize: () => 100, // Ajustamos un poco el alto para que entre el badge cómodamente
    overscan: 5,
  })

  return (
    <div className={"flex-col h-full min-h-0 " + (mobileStep === 2 ? "flex" : "hidden md:flex")}>
      <Card className="flex flex-col flex-1 border-emerald-100 shadow-sm overflow-hidden min-h-0 min-w-0">
        <CardHeader className="bg-emerald-50/80 pb-3 border-b border-emerald-100 flex-shrink-0">
          <CardTitle className="text-md font-bold text-emerald-900 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-600" />
              {flowTab === "COBROS" ? "Documentos Emitidos (Cobros)" : "Documentos Recibidos (Pagos)"}
              <span className="text-xs font-normal text-slate-500">({comprobantesPendientes.length})</span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent ref={cbteParentRef} className="flex-1 p-0 bg-white overflow-y-auto relative pb-24">
          {comprobantesPendientes.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-slate-400">No hay documentos pendientes en este flujo.</div>
          ) : (
            <div role="table" style={{ height: `${cbteVirtualizer.getTotalSize()}px`, width: "100%", position: "relative" }}>
              {cbteVirtualizer.getVirtualItems().map((virtualRow) => {
                const cbte = comprobantesPendientes[virtualRow.index]
                if (!cbte) return null
                const isSelected = selectedCbtes.includes(cbte.id)
                const badge = getDocumentBadge(cbte.clase_documento ?? undefined)

                return (
                  <div key={virtualRow.key} onClick={() => handleSelectCbte(cbte.id)}
                    className={"absolute top-0 left-0 w-full flex items-center px-4 cursor-pointer transition-all border-b border-slate-100 " + (isSelected ? "bg-emerald-50/70 border-l-4 border-l-emerald-600" : "hover:bg-slate-50 border-l-4 border-l-transparent")}
                    style={{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                  >
                    <input type="checkbox" checked={isSelected} readOnly className="w-4 h-4 text-emerald-600 rounded mr-4 shrink-0" />

                    <div className="flex-1 min-w-0 py-2 space-y-1">
                      <div className="flex items-center text-[11px] text-slate-400 font-semibold gap-2">
                        <span className="flex items-center gap-1 font-mono shrink-0"><Calendar className="w-3 h-3"/> {formatFechaUI(cbte.fecha)}</span>

                        <span className={`flex items-center px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border ${badge.classes}`}>
                          {badge.icon}
                          {badge.label}
                        </span>

                      </div>

                      <div className="text-sm font-bold text-slate-700 truncate flex items-center gap-1" title={cbte.razon_social}>
                        <User className="w-3 h-3 text-slate-400 shrink-0"/> {cbte.razon_social}
                      </div>

                      <div className="text-xs text-slate-500 font-mono">
                        Ref: {cbte.numero_formateado}
                      </div>
                    </div>

                    <div className="w-28 text-right font-black text-sm flex-shrink-0 pl-2">
                      <div className={cbte.clase_documento === "NOTA_CREDITO" ? "text-blue-700" : "text-slate-800"}>
                        {formatearMonedaSegura(cbte.monto, cbte.moneda)}
                      </div>
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

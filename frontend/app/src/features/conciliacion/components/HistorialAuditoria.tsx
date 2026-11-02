import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, CheckCircle2, Undo2 } from "lucide-react"

// Import apuntando a utils
import { formatearMonedaSegura } from "../utils/formatters"

interface HistorialAuditoriaProps {
  historial: any[]
  handleDesconciliar: (matchId: number) => Promise<boolean> | void
}

export function HistorialAuditoria({ historial, handleDesconciliar }: HistorialAuditoriaProps) {
  // 🌟 FIX FASE D: Estado para bloquear el botón mientras se procesa la reversión en el backend
  const [isRevertingId, setIsRevertingId] = useState<number | null>(null);

  const confirmAndRevert = async (matchId: number) => {
    // 🌟 FIX FASE D: Seguro contra accidentes (Fail-Safe)
    if (!window.confirm("⚠️ ATENCIÓN: Deshacer esta conciliación restaurará las deudas de las facturas y el saldo en el banco.\n\nSi esta conciliación generó recibos o anticipos a favor, serán anulados automáticamente de la base de datos para preservar la integridad forense.\n\n¿Proceder con la anulación?")) {
      return;
    }

    setIsRevertingId(matchId);
    try {
      await handleDesconciliar(matchId);
    } finally {
      setIsRevertingId(null);
    }
  }

  return (
    <Card className="border-indigo-100 shadow-sm min-h-[600px] flex-1">
      <CardHeader className="bg-indigo-50/50 pb-4 border-b border-indigo-100 flex-shrink-0">
        <CardTitle className="text-md font-bold text-slate-800">Historial de Emparejamientos</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {historial.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No hay registros de conciliaciones previas.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {historial.map((match) => {
              if (!match) return null

              const metodoTxt = typeof match.metodo === 'string' ? match.metodo.replace(/_/g, ' ') : "MANUAL"
              const hasAsiento = Boolean(match && (match as any).asiento_id)
              const movs = Array.isArray(match.movimientos) ? match.movimientos : []
              const cbtes = Array.isArray(match.comprobantes) ? match.comprobantes : []
              const isProcessing = isRevertingId === match.id;

              return (
                <div key={match.id} className={`p-4 transition-colors flex flex-col sm:flex-row justify-between gap-4 sm:items-center ${isProcessing ? 'bg-red-50/50 opacity-70' : 'hover:bg-slate-50'}`}>
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-black bg-slate-200 text-slate-600 px-2 py-0.5 rounded tracking-wider">MATCH ID: {match.id}</span>
                      <span className="text-xs text-slate-500 font-medium">Método: {metodoTxt}</span>

                      {!hasAsiento ? (
                        <span className="flex items-center text-[10px] font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded border border-amber-200 animate-pulse">
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Asentando...
                        </span>
                      ) : (
                        <span className="flex items-center text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Libro Diario OK
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div className="bg-indigo-50/40 p-3 rounded-xl border border-indigo-100 space-y-1.5">
                        <span className="font-bold text-indigo-950 block mb-1">Caja/Tesorería ({movs.length})</span>
                        {movs.map((m: any) => (
                          <div key={m.id} className="flex justify-between text-slate-600 font-medium">
                            <span className="truncate max-w-[180px] font-bold" title={m.concepto}>{m.concepto}</span>
                            <div className="flex gap-4 items-center">
                              <span className="text-[10px] text-slate-400 line-through">{formatearMonedaSegura(m.monto_total, m.moneda)}</span>
                              <span className="font-mono font-black text-indigo-600">{formatearMonedaSegura(m.monto_applied || m.monto_aplicado, m.moneda)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="bg-emerald-50/40 p-3 rounded-xl border border-emerald-100 space-y-1.5">
                        <span className="font-bold text-emerald-950 block mb-1">Comprobantes ({cbtes.length})</span>
                        {cbtes.map((c: any) => (
                          <div key={c.id} className="flex justify-between text-slate-600 font-medium">
                            <span className="font-bold text-slate-700">{c.numero_formateado || c.numero}</span>
                            <div className="flex gap-4 items-center">
                              <span className="text-[10px] text-slate-400 line-through">{formatearMonedaSegura(c.monto_total, c.moneda)}</span>
                              <span className="font-mono font-black text-emerald-600">{formatearMonedaSegura(c.monto_applied || c.monto_aplicado, c.moneda)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <Button
                    onClick={() => confirmAndRevert(match.id)}
                    disabled={isProcessing}
                    variant="outline"
                    className="border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 w-full sm:w-auto flex-shrink-0 rounded-full font-bold text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? (
                      <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                    ) : (
                      <Undo2 className="w-3.5 h-3.5 mr-1" />
                    )}
                    {isProcessing ? "Revertiendo..." : "Deshacer"}
                  </Button>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

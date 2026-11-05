import { useEffect, useRef } from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  ArrowDownRight,
  ArrowUpRight,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Info,
  ShieldAlert
} from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import type { MovimientoBancario } from "../types"

interface MovimientosTableProps {
  movimientos: MovimientoBancario[];
  isLoading: boolean;
  isPolling: boolean;
  selectedCuentaId: string;
  page: number;
  hasMore: boolean;
  onRefresh: () => void;
  onPageChange: (newPage: number) => void;
}

export function MovimientosTable({
  movimientos,
  isLoading,
  isPolling,
  selectedCuentaId,
  page,
  hasMore,
  onPageChange
}: MovimientosTableProps) {

  const wasPollingRef = useRef(isPolling);

  useEffect(() => {
    if (wasPollingRef.current && !isPolling) {
      onPageChange(0);
    }
    wasPollingRef.current = isPolling;
  }, [isPolling, onPageChange]);

  return (
    <div className="space-y-0 relative">

      {isPolling && (
        <div className="absolute inset-0 z-10 bg-white/50 backdrop-blur-[2px] flex flex-col items-center justify-center rounded-md border border-indigo-100/50 transition-all">
          <div className="bg-white p-6 rounded-xl shadow-xl border border-indigo-100 flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <Loader2 className="h-10 w-10 animate-spin text-indigo-600 mb-4" />
            <h3 className="text-lg font-bold text-slate-800">Procesando extracto...</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-[260px] text-center leading-relaxed">
              El motor está normalizando los datos y descartando duplicados de forma segura.
            </p>
          </div>
        </div>
      )}

      <div className="w-full overflow-x-auto scrollbar-hide">
        <TooltipProvider delayDuration={200}>
          <Table className="w-full text-sm sm:text-base">
            <TableHeader className="bg-slate-50 sticky top-0">
              <TableRow>
                <TableHead className="w-10 text-center hidden sm:table-cell"></TableHead>
                <TableHead className="font-semibold text-slate-600 whitespace-nowrap">Fecha</TableHead>
                <TableHead className="font-semibold text-slate-600">Concepto</TableHead>
                <TableHead className="font-semibold text-slate-600 hidden sm:table-cell">Ref. Banco</TableHead>
                <TableHead className="text-right font-semibold text-slate-600">Monto</TableHead>
                <TableHead className="text-center font-semibold text-slate-600 pr-4">Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!selectedCuentaId ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-slate-500">
                    Seleccioná una cuenta para ver sus movimientos.
                  </TableCell>
                </TableRow>
              ) : isLoading && !isPolling ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-slate-500">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin mb-2" />Cargando transacciones...
                  </TableCell>
                </TableRow>
              ) : movimientos.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-slate-500">
                    No hay movimientos registrados en esta cuenta.
                  </TableCell>
                </TableRow>
              ) : (
                movimientos.map((mov) => {
                  const amount = Number(mov.monto);
                  return (
                  /* 🌟 FIX FASE 2.2: Clave compuesta para prevenir colisiones entre SOLICITUD y MOVIMIENTO */
                  <TableRow key={`${mov.tipo_registro}-${mov.id}`} className="hover:bg-slate-50/80 transition-colors group">
                    <TableCell className="text-center hidden sm:table-cell">
                      {amount >= 0 ?
                        <ArrowDownRight className="h-5 w-5 text-emerald-500 mx-auto group-hover:scale-110 transition-transform" /> :
                        <ArrowUpRight className="h-5 w-5 text-red-500 mx-auto group-hover:scale-110 transition-transform" />}
                    </TableCell>

                    <TableCell className="text-slate-600 whitespace-nowrap text-xs sm:text-sm">
                      {mov.fecha}
                    </TableCell>

                    <TableCell className="max-w-[160px] sm:max-w-[250px] text-xs sm:text-sm align-middle">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="font-medium text-slate-900 truncate cursor-help">
                            {mov.concepto_bancario_crudo || mov.concepto}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="bg-white text-slate-800 border-slate-200 shadow-xl text-xs max-w-xs font-medium">
                          {mov.concepto_bancario_crudo || mov.concepto}
                        </TooltipContent>
                      </Tooltip>

                      <div className="sm:hidden mt-0.5">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="text-[10px] text-slate-500 font-mono truncate cursor-help">
                              {mov.referencia_banco || "S/N"}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="bg-slate-900 text-emerald-400 border-none shadow-xl text-xs font-mono">
                            {mov.referencia_banco || "S/N"}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </TableCell>

                    <TableCell className="hidden sm:table-cell max-w-[140px] lg:max-w-[180px] align-middle">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="text-slate-500 text-xs sm:text-sm font-mono truncate cursor-help">
                            {mov.referencia_banco || "S/N"}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="bg-slate-900 text-emerald-400 border-none shadow-xl text-xs font-mono">
                          {mov.referencia_banco || "S/N"}
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>

                    <TableCell className={`text-right font-bold whitespace-nowrap text-xs sm:text-sm ${amount >= 0 ? 'text-emerald-600' : 'text-slate-900'}`}>
                      {formatCurrency(amount, mov.moneda)}
                    </TableCell>

                    <TableCell className="text-center pr-2 sm:pr-4">
                      {mov.estado === 'PENDING_APPROVAL' ? (
                        <span className="px-2 sm:px-3 py-1 rounded-full text-[9px] sm:text-[10px] font-bold tracking-wider bg-amber-100 text-amber-800 uppercase shadow-sm border border-amber-200">CUARENTENA</span>
                      ) : mov.estado === 'RECHAZADO' ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex items-center gap-1 px-2 sm:px-3 py-1 rounded-full text-[9px] sm:text-[10px] font-bold tracking-wider bg-red-100 text-red-800 uppercase shadow-sm border border-red-200 cursor-help">
                              RECHAZADO
                              <Info className="h-3 w-3" />
                            </span>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs bg-white border border-red-200 shadow-xl p-4 z-50">
                            <p className="font-bold text-sm mb-2 flex items-center gap-2 text-red-600">
                              <ShieldAlert className="h-4 w-4" /> Motivo del rechazo
                            </p>
                            <p className="text-xs font-medium text-slate-800 leading-relaxed">
                              {mov.motivo_rechazo || 'No se especificó un motivo en el sistema.'}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      ) : (mov.estado === 'CONCILIADO' || mov.conciliado) ? (
                        <span className="px-2 sm:px-3 py-1 rounded-full text-[9px] sm:text-[10px] font-bold tracking-wider bg-emerald-100 text-emerald-800 uppercase shadow-sm border border-emerald-200">CONCILIADO</span>
                      ) : (
                        <span className="px-2 sm:px-3 py-1 rounded-full text-[9px] sm:text-[10px] font-bold tracking-wider bg-slate-100 text-slate-600 uppercase border border-slate-200">PEND. BANCO</span>
                      )}
                    </TableCell>
                  </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TooltipProvider>
      </div>

      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-t border-slate-100 bg-slate-50/50">
        <span className="text-xs sm:text-sm font-medium text-slate-500">Página {page + 1}</span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="bg-white h-8 sm:h-9"
            onClick={() => onPageChange(Math.max(0, page - 1))}
            disabled={page === 0 || isLoading || !selectedCuentaId || isPolling}
          >
            <ChevronLeft className="h-4 w-4 sm:mr-1" /> <span className="hidden sm:inline">Anterior</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="bg-white h-8 sm:h-9"
            onClick={() => onPageChange(page + 1)}
            disabled={!hasMore || isLoading || !selectedCuentaId || isPolling}
          >
            <span className="hidden sm:inline">Siguiente</span> <ChevronRight className="h-4 w-4 sm:ml-1" />
          </Button>
        </div>
      </div>
    </div>
  )
}

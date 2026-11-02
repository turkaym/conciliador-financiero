import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, Trash2, Undo2 } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import type { Comprobante } from "../types"

interface ComprobantesTableProps {
  comprobantes: Comprobante[];
  isLoading: boolean;
  deletingId: number | null;
  onDeleteClick: (comprobante: Comprobante) => void;
}

export function ComprobantesTable({
  comprobantes,
  isLoading,
  deletingId,
  onDeleteClick
}: ComprobantesTableProps) {

  // 🌟 FIX: Reglas de inmutabilidad endurecidas (Anti-Falsos Negativos)
  const isBorradoBloqueado = (comp: Comprobante) => {
    const tieneCaeValido = comp.cae !== null && comp.cae !== undefined && comp.cae.trim() !== "";
    if (tieneCaeValido) return true;
    if (comp.clase_documento === "REMITO" && comp.estado === "FACTURADO") return true;
    if (["EMITIDO", "PAGADA", "AUTORIZADA", "EN_LOTE"].includes(comp.estado)) return true;
    return false;
  };

  return (
    <Card className="shadow-sm border-slate-200">
      <CardContent className="p-0 overflow-x-auto">
        <Table>
          <TableHeader className="bg-slate-50">
            <TableRow>
              <TableHead className="font-semibold text-slate-600 pl-4 w-12"></TableHead>
              <TableHead className="font-semibold text-slate-600">Op.</TableHead>
              <TableHead className="font-semibold text-slate-600">Fecha</TableHead>
              <TableHead className="font-semibold text-slate-600">Comprobante</TableHead>
              <TableHead className="font-semibold text-slate-600">Emisor</TableHead>
              <TableHead className="font-semibold text-slate-600">Receptor</TableHead>
              <TableHead className="text-right font-semibold text-slate-600">Importe</TableHead>
              <TableHead className="text-center font-semibold text-slate-600 pr-4">Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-slate-500">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin mb-2" /> Cargando...
                </TableCell>
              </TableRow>
            ) : comprobantes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-slate-500">
                  No hay comprobantes cargados para esta empresa.
                </TableCell>
              </TableRow>
            ) : (
              comprobantes.map((comp) => {
                const bloqueado = isBorradoBloqueado(comp);
                const requiereNotaCredito = comp.cae !== null && comp.cae !== undefined && comp.cae.trim() !== "";

                return (
                <TableRow key={comp.id} className={`hover:bg-slate-50/80 transition-colors group ${deletingId === comp.id ? 'opacity-50 pointer-events-none' : ''}`}>
                  <TableCell className="pl-4">
                    {deletingId === comp.id ? (
                       <Loader2 className="h-4 w-4 animate-spin text-slate-400 ml-2" />
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        className={`h-8 w-8 transition-opacity ${
                          bloqueado
                            ? (requiereNotaCredito ? 'opacity-0 group-hover:opacity-100 hover:text-amber-600 hover:bg-amber-50' : 'opacity-30 cursor-not-allowed')
                            : 'opacity-0 group-hover:opacity-100 hover:text-red-600 hover:bg-red-50'
                        }`}
                        onClick={() => {
                          if (!bloqueado) {
                            onDeleteClick(comp);
                          } else if (requiereNotaCredito) {
                            alert("Para anular un comprobante fiscalizado por AFIP (con CAE), se debe emitir una Nota de Crédito por el mismo importe.");
                          }
                        }}
                        disabled={bloqueado && !requiereNotaCredito}
                        title={
                          bloqueado
                            ? (requiereNotaCredito ? "Anular (Emitir Nota de Crédito)" : "Documento vinculado o bloqueado")
                            : "Eliminar borrador/remito"
                        }
                      >
                        {bloqueado && requiereNotaCredito ? (
                          <Undo2 className="h-4 w-4 text-amber-600" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                  </TableCell>

                  <TableCell>
                    <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${comp.tipo_operacion === 'VENTA' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
                      {comp.tipo_operacion}
                    </span>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-sm text-slate-600 font-medium">{comp.fecha_emision}</TableCell>
                  <TableCell className="font-medium">
                    <div className="flex flex-col items-start gap-1">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        comp.clase_documento === 'REMITO' ? 'bg-amber-100 text-amber-700 border border-amber-200' : 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                      }`}>
                        {comp.clase_documento}
                      </span>
                      <span className="text-sm font-bold text-slate-800 tracking-tight">
                        {comp.numero_formateado || `DOC ${comp.punto_venta}-${comp.numero}`}
                      </span>
                      {comp.cae && comp.cae.trim() !== "" && (
                        <span className="text-[10px] text-emerald-600 font-semibold bg-emerald-50 px-1 py-0.5 rounded-sm">CAE: {comp.cae}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-slate-600 text-sm font-mono tracking-tight">{comp.cuit_emisor}</TableCell>
                  <TableCell className="text-slate-600 text-sm font-mono tracking-tight">{comp.cuit_receptor}</TableCell>
                  <TableCell className="text-right font-bold text-slate-800 whitespace-nowrap">
                    {formatCurrency(comp.importe_total, comp.moneda)}
                  </TableCell>
                  <TableCell className="text-center pr-4">
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap ${comp.estado === 'FACTURADO' || comp.estado === 'PAGADA' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-slate-100 text-slate-700 border border-slate-200'}`}>
                      {comp.estado}
                    </span>
                  </TableCell>
                </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
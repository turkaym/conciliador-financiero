import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { CheckCircle, XCircle, Clock, ShieldAlert, AlertTriangle } from "lucide-react"
import type { MovimientoBancario } from "../types"

interface BandejaAprobacionesProps {
  pendientes: MovimientoBancario[];
  isLoading: boolean;
  // 🌟 FIX TIPADO: Ahora soporta el parámetro opcional de rechazo
  onResolver: (id: number, tipoRegistro: MovimientoBancario['tipo_registro'], accion: 'aprobar' | 'rechazar', motivoRechazo?: string) => Promise<boolean | void>;
}

export function BandejaAprobaciones({ pendientes, isLoading, onResolver }: BandejaAprobacionesProps) {
  // 🌟 ESTADOS DEL INTERCEPTOR DE RECHAZO
  const [rechazoId, setRechazoId] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");
  const [isSubmittingRechazo, setIsSubmittingRechazo] = useState(false);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(amount)
  }

  const handleAbrirRechazo = (id: number) => {
    setRechazoId(id);
    setMotivo(""); // Limpiamos estados anteriores
  }

  const confirmarRechazo = async () => {
    if (!rechazoId || !motivo.trim()) return;
    setIsSubmittingRechazo(true);

    // Disparamos la resolución hacia el Backend
    await onResolver(rechazoId, 'SOLICITUD', 'rechazar', motivo.trim());

    setIsSubmittingRechazo(false);
    setRechazoId(null); // Cerramos el modal
  }

  if (pendientes.length === 0) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-center px-6 animate-in fade-in">
        <div className="bg-emerald-50 p-6 rounded-full mb-4">
          <CheckCircle className="h-10 w-10 text-emerald-500" />
        </div>
        <h3 className="text-xl font-bold text-slate-800 mb-2">Todo al día</h3>
        <p className="text-slate-500 font-medium max-w-[280px]">No hay transacciones en cuarentena esperando tu autorización.</p>
      </div>
    )
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 p-5 bg-slate-50/30">
        {pendientes.map(mov => (
          <Card key={mov.id} className="p-5 flex flex-col gap-4 border-amber-200 bg-gradient-to-b from-amber-50/50 to-white shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 opacity-[0.03]">
              <ShieldAlert className="h-24 w-24 text-amber-900" />
            </div>

            <div className="relative z-10 flex justify-between items-start">
              <div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 uppercase tracking-widest mb-3 border border-amber-200/50">
                  <Clock className="h-3 w-3" /> En Cuarentena
                </span>
                <h4 className="font-bold text-slate-900 leading-tight pr-4" title={mov.concepto}>
                  {mov.concepto}
                </h4>
                <p className="text-xs text-slate-500 mt-2 font-mono bg-slate-100 inline-block px-2 py-0.5 rounded">
                  Creado por: {mov.usuario_creador_nombre || 'Usuario Desconocido'}
                </p>
              </div>
            </div>

            <div className="relative z-10 bg-white rounded-xl p-4 border border-slate-100 shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] mt-2">
              <p className="text-[10px] text-slate-400 uppercase font-black tracking-widest mb-1">Monto Retenido</p>
              <p className="text-3xl font-black text-slate-900 tracking-tighter">
                {formatCurrency(Math.abs(Number(mov.monto)))}
              </p>
              <p className="text-xs text-slate-400 mt-1 font-medium">{mov.fecha}</p>
            </div>

            <div className="relative z-10 grid grid-cols-2 gap-3 mt-2">
              <Button
                variant="outline"
                className="w-full border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-colors"
                disabled={isLoading}
                onClick={() => handleAbrirRechazo(mov.id)}
              >
                <XCircle className="h-4 w-4 mr-2" /> Rechazar
              </Button>
              <Button
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-200 transition-colors border-transparent"
                disabled={isLoading}
                onClick={() => onResolver(mov.id, mov.tipo_registro, 'aprobar')}
              >
                <CheckCircle className="h-4 w-4 mr-2" /> Aprobar
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* 🌟 FIX FEEDBACK LOOP: Modal Interceptor para justificar rechazo */}
      <Dialog open={rechazoId !== null} onOpenChange={(open) => !open && setRechazoId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Motivo de Rechazo
            </DialogTitle>
            <DialogDescription>
              Para mantener la trazabilidad operativa, debés indicarle al Operador (Maker) por qué estás rechazando esta transacción.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <Input
              placeholder="Ej: El monto no coincide con la factura, comprobante ilegible..."
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              disabled={isSubmittingRechazo}
              autoFocus
              className="col-span-3"
            />
          </div>

          <DialogFooter className="sm:justify-end">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setRechazoId(null)}
              disabled={isSubmittingRechazo}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={confirmarRechazo}
              disabled={!motivo.trim() || isSubmittingRechazo}
            >
              {isSubmittingRechazo ? "Procesando..." : "Confirmar Rechazo"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

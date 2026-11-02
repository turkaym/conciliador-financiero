import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangle, FileText, CheckCircle2, Loader2 } from "lucide-react"
import type { RetencionSufridaPayload } from "../hooks/useConciliacion"

// Ruta corregida apuntando a utils
import { formatearMonedaSegura } from "../utils/formatters"

interface AjusteFiscalModalProps {
  isOpen: boolean
  onClose: () => void
  diferencia: number
  isProcessing: boolean
  onSubmit: (ajuste: RetencionSufridaPayload | undefined) => void
}

export function AjusteFiscalModal({
  isOpen,
  onClose,
  diferencia,
  onSubmit,
  isProcessing
}: AjusteFiscalModalProps) {
  const [modoAjuste, setModoAjuste] = useState<'PARCIAL' | 'RETENCION'>('PARCIAL')
  const [tipoImpuesto, setTipoImpuesto] = useState('RETENCION_IIBB')
  const [jurisdiccion, setJurisdiccion] = useState('ARBA')
  const [numeroCertificado, setNumeroCertificado] = useState('')

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="bg-indigo-50 border-b border-indigo-100 p-4 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-indigo-900 font-bold text-sm">Brecha Matemática Detectada</h3>
            <p className="text-xs text-indigo-700/80 mt-1 leading-relaxed">
              El pago ingresado no alcanza a cubrir la totalidad de las facturas seleccionadas.
            </p>
          </div>
        </div>

        <div className="p-6 space-y-5">
          <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg border border-slate-200 shadow-inner">
            <span className="text-sm font-semibold text-slate-600">Monto Faltante:</span>
            <span className="font-black text-indigo-600 text-lg">{formatearMonedaSegura(diferencia, 'ARS')}</span>
          </div>

          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-500 uppercase">¿Cómo desea justificar este faltante?</label>

            <div
              onClick={() => setModoAjuste('PARCIAL')}
              className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${modoAjuste === 'PARCIAL' ? 'border-indigo-500 bg-indigo-50/50' : 'border-slate-100 hover:border-slate-200'}`}
            >
              <div className="flex items-center gap-2">
                <input type="radio" checked={modoAjuste === 'PARCIAL'} readOnly className="w-4 h-4 text-indigo-600" />
                <span className="font-bold text-sm text-slate-800">Es un Pago Parcial</span>
              </div>
              <p className="text-xs text-slate-500 mt-1 ml-6">El cliente pagó de menos. Quedará un saldo pendiente de cobro en la factura.</p>
            </div>

            <div
              onClick={() => setModoAjuste('RETENCION')}
              className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${modoAjuste === 'RETENCION' ? 'border-amber-500 bg-amber-50/50' : 'border-slate-100 hover:border-slate-200'}`}
            >
              <div className="flex items-center gap-2">
                <input type="radio" checked={modoAjuste === 'RETENCION'} readOnly className="w-4 h-4 text-amber-600" />
                <span className="font-bold text-sm text-amber-900">Sufrí una Retención Impositiva</span>
              </div>
              <p className="text-xs text-amber-700/70 mt-1 ml-6">El cliente me retuvo impuestos. Deseo saldar la factura inyectando el certificado.</p>
            </div>
          </div>

          {modoAjuste === 'RETENCION' && (
            <div className="space-y-3 pt-3 border-t border-slate-100 animate-in fade-in slide-in-from-top-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Impuesto</label>
                  <select
                    className="w-full h-9 mt-1 border-slate-200 rounded-md text-xs focus:ring-amber-500 focus:border-amber-500"
                    value={tipoImpuesto} onChange={(e) => setTipoImpuesto(e.target.value)}
                  >
                    <option value="RETENCION_IIBB">Ingresos Brutos</option>
                    <option value="RETENCION_GANANCIAS">Ganancias</option>
                    <option value="RETENCION_SUSS">S.U.S.S.</option>
                    <option value="RETENCION_IVA">I.V.A.</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Jurisdicción</label>
                  <select
                    className="w-full h-9 mt-1 border-slate-200 rounded-md text-xs focus:ring-amber-500 focus:border-amber-500"
                    value={jurisdiccion} onChange={(e) => setJurisdiccion(e.target.value)}
                  >
                    <option value="AFIP">AFIP (Nacional)</option>
                    <option value="ARBA">ARBA (Bs. As.)</option>
                    <option value="AGIP">AGIP (CABA)</option>
                    <option value="RENTAS_CBA">Córdoba</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase flex items-center gap-1"><FileText className="w-3 h-3"/> N° de Certificado Fiscal</label>
                <input
                  type="text" placeholder="Ej: 0001-00045678" required
                  className="flex h-9 w-full mt-1 rounded-md border border-slate-300 px-3 text-xs shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
                  value={numeroCertificado} onChange={(e) => setNumeroCertificado(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        <div className="bg-slate-50 p-4 border-t border-slate-100 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={isProcessing}>Cancelar</Button>
          <Button
            className={`${modoAjuste === 'RETENCION' ? 'bg-amber-500 hover:bg-amber-600' : 'bg-indigo-600 hover:bg-indigo-700'} text-white font-bold transition-colors`}
            disabled={(modoAjuste === 'RETENCION' && !numeroCertificado) || isProcessing}
            onClick={() => {
              if (modoAjuste === 'PARCIAL') onSubmit(undefined)
              else onSubmit({ tipo_impuesto: tipoImpuesto, jurisdiccion, numero_certificado: numeroCertificado, monto_impuesto: diferencia })
            }}
          >
            {isProcessing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
            Confirmar y Vincular
          </Button>
        </div>
      </div>
    </div>
  )
}
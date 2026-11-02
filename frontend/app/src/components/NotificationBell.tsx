import { useState, useEffect, useRef } from "react"
import api from "../api/axios"
import { useAuthStore } from "../store/useAuthStore"
import { CheckCircle, AlertTriangle, AlertOctagon, Bell, CheckCheck, ExternalLink } from "lucide-react"
import { useNavigate } from "react-router-dom"

interface AlertaFiscal {
  estado_salud: "OPTIMO" | "CRITICO"
  total_alertas: number
  alertas_dlq: any[]
  alertas_cae: any[]
}

export default function NotificationBell() {
  const [alerta, setAlerta] = useState<AlertaFiscal | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const entidadActivaId = useAuthStore((state) => state.entidadActiva?.id)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const fetchAlertas = async (currentEntidadId: number) => {
    if (!currentEntidadId || document.hidden) return

    try {
      // ⏪ REGRESIÓN: Volvemos a usar el Header seguro Zero-Trust
      const response = await api.get<AlertaFiscal>(`/v1/comprobantes/alertas`, {
        headers: { 'X-Entity-ID': currentEntidadId.toString() }
      })
      setAlerta(response.data)
    } catch (error) {
      console.error("Fallo silencioso al consultar alertas fiscales:", error)
    }
  }

  useEffect(() => {
    setAlerta(null)

    if (!entidadActivaId) return;

    fetchAlertas(entidadActivaId)
    const intervalId = setInterval(() => fetchAlertas(entidadActivaId), 180000)
    return () => clearInterval(intervalId)
  }, [entidadActivaId])

  const handleResolverAlerta = async (alertaId: number) => {
    if (!entidadActivaId) return;
    const estadoAnterior = alerta

    setAlerta(prev => {
      if (!prev) return prev
      const nuevasDlq = prev.alertas_dlq.filter(a => a.id_registro !== alertaId)
      const total = prev.alertas_cae.length + nuevasDlq.length
      return {
        ...prev, alertas_dlq: nuevasDlq, total_alertas: total, estado_salud: total > 0 ? "CRITICO" : "OPTIMO"
      }
    })

    try {
      // ⏪ REGRESIÓN: Volvemos a usar el Header
      await api.patch(`/v1/comprobantes/alertas/${alertaId}/resolver`, {}, {
        headers: { 'X-Entity-ID': entidadActivaId.toString() }
      })
    } catch (error) {
      console.error("Fallo de red al descartar alerta. Revirtiendo interfaz.", error)
      setAlerta(estadoAnterior)
    }
  }

  const handleResolverTodas = async () => {
    if (!entidadActivaId) return;
    const estadoAnterior = alerta

    setAlerta(prev => {
      if (!prev) return prev
      const total = prev.alertas_cae.length
      return {
        ...prev, alertas_dlq: [], total_alertas: total, estado_salud: total > 0 ? "CRITICO" : "OPTIMO"
      }
    })

    try {
      // ⏪ REGRESIÓN: Volvemos a usar el Header
      await api.patch(`/v1/comprobantes/alertas/resolver-todas`, {}, {
        headers: { 'X-Entity-ID': entidadActivaId.toString() }
      })
    } catch (error) {
      console.error("Fallo masivo al descartar. Revirtiendo interfaz.", error)
      setAlerta(estadoAnterior)
    }
  }

  const tieneAlertas = alerta && alerta.total_alertas > 0

  return (
    <div className="relative" ref={dropdownRef}>

      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
      >
        <Bell className="h-5 w-5" />
        {tieneAlertas && (
          <span className="absolute top-1.5 right-1.5 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500 border-2 border-white"></span>
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-3 w-[320px] sm:w-96 bg-white rounded-xl shadow-2xl ring-1 ring-slate-900/5 z-[100] origin-top-right overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">

          <div className="bg-gradient-to-r from-slate-900 to-indigo-950 px-4 py-3.5 flex justify-between items-center shrink-0">
            <h3 className="text-sm font-medium tracking-tight text-white flex items-center gap-2">
              Centro de Monitoreo
              {tieneAlertas && (
                <span className="bg-rose-500 text-white text-[10px] uppercase font-bold px-3 py-1 rounded-full tracking-wider shadow-sm flex-shrink-0 whitespace-nowrap">
                  {alerta.total_alertas} Críticas
                </span>
              )}
            </h3>
            {alerta?.alertas_dlq && alerta.alertas_dlq.length > 0 && (
              <button
                onClick={handleResolverTodas}
                className="text-xs font-medium text-indigo-200 hover:text-white flex items-center gap-1.5 transition-colors focus:outline-none"
              >
                <CheckCheck className="h-4 w-4" /> Leer todas
              </button>
            )}
          </div>

          <div className="max-h-[50vh] sm:max-h-[22rem] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
            {!tieneAlertas ? (
              <div className="p-8 sm:p-10 text-center text-sm text-slate-400 flex flex-col items-center">
                <div className="h-12 w-12 rounded-full bg-emerald-50 flex items-center justify-center mb-3">
                  <CheckCircle className="h-6 w-6 text-emerald-500" />
                </div>
                <p className="tracking-tight">Motor fiscal operando sin anomalías</p>
              </div>
            ) : (
              <div className="flex flex-col">
                {alerta.alertas_cae.map((cae, idx) => (
                  <div key={`cae-${idx}`} className="p-4 border-b border-slate-50 hover:bg-slate-50/80 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 p-1.5 rounded-md bg-orange-50 shrink-0">
                        <AlertTriangle className="h-4 w-4 text-orange-500" />
                      </div>
                      <div>
                        <p className="text-[13px] font-semibold text-slate-800 tracking-tight">Fuga de CAE (Borrador)</p>
                        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">Comprobante Interno N° {cae.numero_interno} no obtuvo CAE de AFIP.</p>
                      </div>
                    </div>
                  </div>
                ))}

                {alerta.alertas_dlq.map((dlq, idx) => (
                  <div key={`dlq-${idx}`} className="p-4 border-b border-slate-50 hover:bg-slate-50/80 transition-colors group">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 p-1.5 rounded-md bg-rose-50 shrink-0">
                        <AlertOctagon className="h-4 w-4 text-rose-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-semibold text-slate-800 tracking-tight">Rechazo Crítico AFIP</p>
                        <p className="text-xs text-slate-600 font-mono bg-slate-100/50 p-1.5 rounded border border-slate-100 mt-1.5 break-words">
                          {dlq.error}
                        </p>
                        <button
                          onClick={() => handleResolverAlerta(dlq.id_registro)}
                          className="mt-3 text-[13px] font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1.5"
                        >
                          <CheckCircle className="h-3.5 w-3.5" /> Marcar como resuelto
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-50/50 px-4 py-3 border-t border-slate-100 shrink-0">
            <button
              onClick={() => {
                setIsOpen(false);
                navigate('/dashboard/reportes');
              }}
              className="w-full text-center text-[13px] font-medium text-slate-500 hover:text-slate-800 flex items-center justify-center gap-1.5 transition-colors"
            >
              Ver historial de auditoría <ExternalLink className="h-3.5 w-3.5" />
            </button>
          </div>

        </div>
      )}
    </div>
  )
}
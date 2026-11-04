import { useCallback, useEffect, useState } from "react"
import api from "@/api/axios"
import { useAuthStore } from "@/store/useAuthStore"
import type { Entidad } from "@/store/useAuthStore"
import { Building2, ChevronDown, Check, Loader2, AlertCircle, Plus, Lock } from "lucide-react"
import NuevaEmpresaModal from "./NuevaEmpresaModal"

export default function EntitySelector() {
  // 🌟 FIX: Agregamos isDataLocked para escuchar el estado del Paywall
  const { tenant_id, entidadActiva, setEntidadActiva, features, user, openPaywall, isDataLocked } = useAuthStore()

  const [entidades, setEntidades] = useState<Entidad[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const fetchEntidades = useCallback(async (id: string) => {
    setLoading(true)
    setError(false)
    try {
      const { data } = await api.get(`/v1/entidades/${id}`)
      setEntidades(data)
      const activeEntity = useAuthStore.getState().entidadActiva

      if (data.length > 0 && !activeEntity) {
        setEntidadActiva(data[0])
      }

      if (activeEntity && data.length > 0) {
        const stillExists = data.find((e: Entidad) => e.id === activeEntity.id)
        if (!stillExists) setEntidadActiva(data[0])
      }
    } catch (err: any) {
      // 🌟 FIX UX: Ignoramos el error 402 porque el interceptor ya activó isDataLocked.
      if (err.response?.status !== 402) {
        console.error("Error cargando entidades:", err)
        setError(true)
      }
    } finally {
      setLoading(false)
    }
  }, [setEntidadActiva])

  useEffect(() => {
    if (tenant_id) {
      void fetchEntidades(tenant_id)
    }
  }, [fetchEntidades, tenant_id])

  const handleSelect = (entidad: Entidad) => {
    setEntidadActiva(entidad)
    setIsOpen(false)
  }

  const handleAddCompanyClick = () => {
    setIsOpen(false);
    const maxEntidades = features?.max_entidades || 1;

    if (entidades.length >= maxEntidades) {
      openPaywall();
    } else {
      setIsCreateModalOpen(true);
    }
  }

  // 🌟 FASE 10: Estado de Bloqueo Visual (Anula el botón sin mostrar error)
  if (isDataLocked) {
    return (
      <div className="w-full flex items-center justify-between gap-3 px-3 py-2 bg-slate-900/40 text-slate-500 rounded-md border border-slate-800 cursor-not-allowed">
        <div className="flex items-center gap-2 overflow-hidden flex-1">
          <div className="p-1 bg-slate-800/50 rounded flex-shrink-0">
            <Lock className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold truncate w-full">Suscripción Suspendida</span>
        </div>
      </div>
    )
  }

  if (loading) return <div className="flex items-center gap-2 px-3 py-2 text-sm text-slate-400 bg-slate-800/50 rounded-md border border-slate-700"><Loader2 className="h-4 w-4 animate-spin" /><span>Cargando...</span></div>
  if (error) return <div className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 bg-red-950/30 rounded-md border border-red-900/50"><AlertCircle className="h-4 w-4" /><span>Error de conexión</span></div>

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between gap-3 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-md border border-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <div className="flex items-center gap-2 overflow-hidden flex-1">
            <div className="p-1 bg-indigo-500/20 rounded text-indigo-400 flex-shrink-0">
              <Building2 className="h-4 w-4" />
            </div>
            <div className="flex flex-col items-start overflow-hidden flex-1 text-left">
              <span className="text-sm font-bold truncate w-full" title={entidadActiva?.nombre_fantasia}>
                {entidadActiva?.nombre_fantasia || "Seleccionar..."}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">CUIT: {entidadActiva?.cuit || "---"}</span>
            </div>
          </div>
          <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)}></div>
            <div className="absolute top-full left-0 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg z-50 py-1 animate-in fade-in slide-in-from-top-2 duration-200">

              <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100 mb-1 flex justify-between items-center bg-slate-50">
                <span>Mis Empresas</span>
                <span className="text-[10px] bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-bold">
                  {entidades.length} / {features?.max_entidades || 1}
                </span>
              </div>

              <div className="max-h-60 overflow-y-auto">
                {entidades.map((entidad) => (
                  <button
                    key={entidad.id}
                    onClick={() => handleSelect(entidad)}
                    className="w-full flex items-center justify-between px-3 py-3 min-h-[48px] text-sm text-left hover:bg-indigo-50 active:bg-indigo-100 transition-colors"
                  >
                    <div className="flex flex-col items-start flex-1 overflow-hidden pr-2">
                      <span className="text-sm font-bold leading-tight text-left line-clamp-2">{entidad.nombre_fantasia}</span>
                      <span className="text-[10px] text-slate-400 font-mono mt-0.5">CUIT: {entidad.cuit}</span>
                    </div>
                    {entidadActiva?.id === entidad.id && <Check className="h-4 w-4 text-indigo-600 flex-shrink-0" />}
                  </button>
                ))}
              </div>

              {user?.role === 'admin' && (
                <div className="p-2 border-t border-slate-100 mt-1 bg-white">
                  <button
                    onClick={handleAddCompanyClick}
                    className="w-full flex items-center justify-center gap-2 px-3 py-3 min-h-[48px] text-sm font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 active:bg-indigo-200 rounded-md transition-colors border border-indigo-100"
                  >
                    <Plus className="h-4 w-4" />
                    Agregar Nueva Empresa
                  </button>
                </div>
              )}

            </div>
          </>
        )}
      </div>

      <NuevaEmpresaModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          setIsCreateModalOpen(false);
          if (tenant_id) fetchEntidades(tenant_id);
        }}
      />
    </>
  )
}

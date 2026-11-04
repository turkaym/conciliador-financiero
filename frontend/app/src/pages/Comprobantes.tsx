import { useEffect, useState } from "react"
import { useAuthStore } from "@/store/useAuthStore"
import { useComprobantes, type ComprobanteFilters } from "../features/comprobantes/hooks/useComprobantes"
import { ComprobanteFormModal } from "../features/comprobantes/components/ComprobanteFormModal"
import { DeleteConfirmModal } from "../features/comprobantes/components/DeleteConfirmModal"
import { ComprobantesTable } from "../features/comprobantes/components/ComprobantesTable"
import DataGuard from "@/components/ui/DataGuard"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { RefreshCw, AlertCircle, Building2, CloudDownload, Loader2, Filter, Search, X } from "lucide-react"
import type { Comprobante } from "../features/comprobantes/types"

export default function ComprobantesPage() {
  const { entidadActiva } = useAuthStore()
  const {
    comprobantes,
    remitosPendientes,
    cajasDisponibles,
    isLoading,
    isSaving,
    isSyncingAfip,
    deletingId,
    errorMsg,
    setErrorMsg,
    globalMessage,
    syncFeedback,
    fetchComprobantes,
    fetchRemitosPendientes,
    createComprobante,
    deleteComprobante,
    syncAfip,
    clearData
  } = useComprobantes()

  const [comprobanteToDelete, setComprobanteToDelete] = useState<Comprobante | null>(null)
  const [page, setPage] = useState(0)

  // 🌟 ESTADO DE FILTROS DEL DASHBOARD
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<ComprobanteFilters>({
    tipo_operacion: "ALL",
    clase_documento: "ALL",
    estado: "ALL",
    cuit_receptor: "",
    fecha_desde: "",
    fecha_hasta: ""
  })

  useEffect(() => useAuthStore.subscribe((state, previousState) => {
    if (state.entidadActiva?.id !== previousState.entidadActiva?.id) {
      setPage(0)
    }
  }), [])

  // 🌟 REACTIVIDAD AL CAMBIO DE EMPRESA
  useEffect(() => {
    if (entidadActiva) {
      fetchComprobantes(0, filters)
    } else {
      clearData()
    }
  }, [entidadActiva, clearData]) // Quitamos fetchComprobantes para evitar render loops

  // 🌟 MOTOR DE APLICACIÓN DE FILTROS
  const handleApplyFilters = () => {
    setPage(0)
    fetchComprobantes(0, filters)
  }

  const handleClearFilters = () => {
    const emptyFilters = {
      tipo_operacion: "ALL", clase_documento: "ALL", estado: "ALL", cuit_receptor: "", fecha_desde: "", fecha_hasta: ""
    }
    setFilters(emptyFilters)
    setPage(0)
    fetchComprobantes(0, emptyFilters)
  }

  const handleConfirmarEliminacion = async () => {
    if (!comprobanteToDelete) return;
    const success = await deleteComprobante(comprobanteToDelete.id);
    if (success) {
      setComprobanteToDelete(null);
      fetchComprobantes(page, filters);
    }
  }

  const handleSyncClick = () => {
    // FIX B2B: Pasamos Punto de Venta 1 y Tipo Cbte 1 por defecto (A futuro esto puede ser un modal)
    // También le pasamos los filtros activos para que al terminar el polling, respete la vista del usuario
    syncAfip(1, 1, filters);
  }

  if (!entidadActiva) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] text-center px-4">
        <div className="bg-slate-100 p-4 rounded-full mb-4">
          <Building2 className="h-12 w-12 text-slate-400" />
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Seleccioná una Empresa</h2>
        <p className="text-slate-500 max-w-md">Para ver o cargar comprobantes, primero necesitás elegir una empresa.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <DeleteConfirmModal
        comprobante={comprobanteToDelete}
        onClose={() => setComprobanteToDelete(null)}
        onConfirm={handleConfirmarEliminacion}
      />

      <DataGuard>
        {/* CABECERA Y BOTONERA SUPERIOR */}
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4 mb-2">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Comprobantes</h1>
            <p className="text-slate-500 mt-1">
              Gestioná las facturas de <span className="font-semibold text-slate-700">{entidadActiva.nombre_fantasia}</span>.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 sm:gap-3">
            <Button
              variant={showFilters ? "secondary" : "outline"}
              className={`transition-colors ${showFilters ? 'bg-indigo-100 text-indigo-800 border-indigo-200 hover:bg-indigo-200' : 'bg-white'}`}
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="mr-2 h-4 w-4" /> Filtros
            </Button>

            <Button
              variant="outline"
              className="border-emerald-200 text-emerald-700 hover:bg-emerald-50 bg-white"
              onClick={handleSyncClick}
              disabled={isLoading || isSyncingAfip}
              title={!entidadActiva.has_afip_credentials ? "Requiere configuración en Workspace Fiscal" : "Bajar comprobantes de AFIP"}
            >
              {isSyncingAfip ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CloudDownload className="mr-2 h-4 w-4" />}
              {isSyncingAfip ? "Encolando..." : "Sincronizar AFIP"}
            </Button>

            <Button variant="outline" className="bg-white" onClick={() => fetchComprobantes(page, filters)} disabled={isLoading || isSyncingAfip}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} /> Actualizar
            </Button>

            <ComprobanteFormModal
              entidadActiva={entidadActiva}
              remitosPendientes={remitosPendientes}
              cajasDisponibles={cajasDisponibles}
              isSaving={isSaving}
              errorMsg={errorMsg}
              onOpen={fetchRemitosPendientes}
              onClose={() => setErrorMsg(null)}
              onSubmit={async (payload) => {
                const success = await createComprobante(payload);
                if (success) {
                  setPage(0);
                  fetchComprobantes(0, filters);
                }
                return success;
              }}
            />
          </div>
        </div>

        {/* 🌟 PANEL DE CONTROL DE FILTROS (DASHBOARD) MOBILE-FIRST */}
        {showFilters && (
          <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm mb-6 animate-in fade-in slide-in-from-top-2">

            {/* 🌟 FIX UX: Grilla base de 6 columnas (las fechas ocupan 2) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 mb-5">

              <div className="space-y-1.5 lg:col-span-1">
                <Label className="text-[10px] uppercase font-bold text-slate-500">Operación</Label>
                <Select value={filters.tipo_operacion} onValueChange={(val) => setFilters({...filters, tipo_operacion: val})}>
                  <SelectTrigger className="h-9 w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">Todas</SelectItem>
                    <SelectItem value="VENTA">Ventas (Ingresos)</SelectItem>
                    <SelectItem value="COMPRA">Compras (Egresos)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5 lg:col-span-1">
                <Label className="text-[10px] uppercase font-bold text-slate-500">Documento</Label>
                <Select value={filters.clase_documento} onValueChange={(val) => setFilters({...filters, clase_documento: val})}>
                  <SelectTrigger className="h-9 w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">Todos</SelectItem>
                    <SelectItem value="FACTURA">Facturas y Tickets</SelectItem>
                    <SelectItem value="REMITO">Remitos</SelectItem>
                    <SelectItem value="NOTA_CREDITO">Notas de Crédito</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5 lg:col-span-1">
                <Label className="text-[10px] uppercase font-bold text-slate-500">Estado de Pago</Label>
                <Select value={filters.estado} onValueChange={(val) => setFilters({...filters, estado: val})}>
                  <SelectTrigger className="h-9 w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">Todos los estados</SelectItem>
                    <SelectItem value="PENDIENTE">Impagas (Pendiente)</SelectItem>
                    <SelectItem value="PAGADA">Pagadas</SelectItem>
                    <SelectItem value="EMITIDO">Emitidas / Enlazadas</SelectItem>
                    <SelectItem value="BORRADOR">Borradores</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5 lg:col-span-1">
                <Label className="text-[10px] uppercase font-bold text-slate-500">Buscar CUIT</Label>
                <Input
                  type="text"
                  placeholder="Ej: 30123456789"
                  className="h-9 text-xs font-mono w-full"
                  value={filters.cuit_receptor}
                  onChange={(e) => setFilters({...filters, cuit_receptor: e.target.value.replace(/\D/g, '')})}
                />
              </div>

              {/* 🌟 FIX UX: col-span-2 para darle el ancho necesario a los dos inputs de fecha */}
              <div className="space-y-1.5 sm:col-span-2 lg:col-span-2">
                <Label className="text-[10px] uppercase font-bold text-slate-500">Desde / Hasta</Label>
                <div className="grid grid-cols-2 gap-2 w-full">
                  <Input type="date" className="h-9 text-xs w-full min-w-0" value={filters.fecha_desde} onChange={(e) => setFilters({...filters, fecha_desde: e.target.value})} />
                  <Input type="date" className="h-9 text-xs w-full min-w-0" value={filters.fecha_hasta} onChange={(e) => setFilters({...filters, fecha_hasta: e.target.value})} />
                </div>
              </div>

            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-3 pt-4 border-t border-slate-100 mt-2">
              <Button variant="outline" className="w-full sm:w-auto h-9 bg-slate-50" onClick={handleClearFilters}>
                <X className="h-4 w-4 mr-2" /> Limpiar
              </Button>
              <Button className="w-full sm:w-[150px] h-9 bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm" onClick={handleApplyFilters}>
                <Search className="h-4 w-4 mr-2" /> Buscar
              </Button>
            </div>

          </div>
        )}

        {/* FEEDBACKS Y TABLA */}
        {globalMessage && (
          <div className={`mb-6 p-4 rounded-md flex items-center shadow-sm border ${globalMessage.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
            <AlertCircle className="h-5 w-5 mr-2" />
            {globalMessage.text}
          </div>
        )}

        {syncFeedback?.active && (
          <div className="mb-6 bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex items-center justify-between animate-in slide-in-from-top-4 fade-in duration-500 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
              </div>
              <p className="text-sm font-medium text-indigo-800">{syncFeedback.text}</p>
            </div>
            <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />
          </div>
        )}

        <ComprobantesTable
          comprobantes={comprobantes}
          isLoading={isLoading}
          deletingId={deletingId}
          onDeleteClick={setComprobanteToDelete}
        />
      </DataGuard>
    </div>
  )
}

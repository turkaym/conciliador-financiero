import { useEffect, useState } from "react";
import { useEgresosStore } from "@/store/useEgresosStore";
import { useAuthStore, type AuthState } from "@/store/useAuthStore";
import { Eye, Clock, CheckCircle2, FileText, AlertCircle, Loader2, X, Image as ImageIcon, ChevronLeft, ChevronRight, ExternalLink, Link2, XCircle, Send, Landmark, ShieldAlert } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import api from "@/api/axios";
import { toast } from "react-toastify";

// 🌟 TIPADO ESTRICTO: Interfaces para maestros
interface Proveedor {
  id: number;
  razon_social: string;
}

interface Concepto {
  id: number;
  nombre_descriptivo: string;
}

interface CuentaBancaria {
  id: number;
  banco: string;
  numero_cuenta: string;
  moneda: string;
}

// Interfaz auxiliar para manejar errores de API sin recurrir a 'any'
interface ApiError {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

export default function LogisticaTable() {
  const { ordenes, isLoading, paginacion, setPaginacion, fetchOrdenes, liquidarOrdenIndividual } = useEgresosStore();

  // 🌟 FIX FASE 4.1: Recuperación de Type-Safety inyectando AuthState
  const entidadActiva = useAuthStore((state: AuthState) => state.entidadActiva);
  const hasPermission = useAuthStore((state: AuthState) => state.hasPermission);

  const canLiquidar = hasPermission("liquidar_ordenes");
  const canAnular = hasPermission("anular_pagos_conciliados") || hasPermission("anular_ordenes");

  const [provMap, setProvMap] = useState<Record<number, string>>({});
  const [concMap, setConcMap] = useState<Record<number, string>>({});
  const [cuentasBancarias, setCuentasBancarias] = useState<CuentaBancaria[]>([]);
  const [isLoadingMaestros, setIsLoadingMaestros] = useState(true);

  const [visorImagenUrl, setVisorImagenUrl] = useState<string | null>(null);
  const [isAnulando, setIsAnulando] = useState<number | null>(null);

  // 🌟 ESTADOS DEL MODAL DE LIQUIDACIÓN
  const [modalLiquidar, setModalLiquidar] = useState<{ isOpen: boolean, ordenId: number | null }>({ isOpen: false, ordenId: null });
  const [cuentaSeleccionadaId, setCuentaSeleccionadaId] = useState<string>("");
  const [isSubmittingLiquidacion, setIsSubmittingLiquidacion] = useState(false);

  useEffect(() => {
    if (!entidadActiva?.id) return;

    let isMounted = true;
    const fetchMaestros = async () => {
      try {
        const headers = { 'x-entity-id': entidadActiva.id };
        const [resConceptos, resProveedores, resCuentas] = await Promise.all([
          api.get('/v1/pagos/conceptos', { headers }),
          api.get('/v1/pagos/proveedores', { headers }),
          api.get('/v1/bancos/cuentas', { headers })
        ]);

        if (isMounted) {
          const pMap: Record<number, string> = {};
          resProveedores.data.forEach((p: Proveedor) => pMap[p.id] = p.razon_social);

          const cMap: Record<number, string> = {};
          resConceptos.data.forEach((c: Concepto) => cMap[c.id] = c.nombre_descriptivo);

          setProvMap(pMap);
          setConcMap(cMap);
          setCuentasBancarias(resCuentas.data || []);
        }
      } catch (error: unknown) {
        console.error("Error cargando maestros:", error);
        toast.error("Hubo un problema al cargar los catálogos de proveedores y cuentas.");
      } finally {
        if (isMounted) setIsLoadingMaestros(false);
      }
    };
    fetchMaestros();
    return () => { isMounted = false; };
  }, [entidadActiva?.id]);

  const handlePrevPage = () => {
    if (paginacion.page > 1) {
      setPaginacion(paginacion.page - 1);
      fetchOrdenes();
    }
  };

  const handleNextPage = () => {
    if (paginacion.hasMore) {
      setPaginacion(paginacion.page + 1);
      fetchOrdenes();
    }
  };

  const handleAnularOrden = async (id: number) => {
    if (!entidadActiva) return;
    if (!window.confirm("¿Estás seguro de que deseas anular esta Orden de Pago?\n\nSi la orden ya fue pagada pero no conciliada, los fondos retornarán virtualmente a la caja y la deuda con el proveedor se reabrirá. Esta acción quedará registrada en la auditoría.")) {
      return;
    }

    setIsAnulando(id);
    try {
      await api.post(`/v1/pagos/ordenes/${id}/anular`, {}, { headers: { 'x-entity-id': entidadActiva.id } });
      toast.success("Orden anulada correctamente. Saldos revertidos al centavo.");
      fetchOrdenes();
    } catch (error: unknown) {
      const err = error as ApiError;
      console.error("Error en anulación:", err);
      toast.error(err.response?.data?.detail || "Fallo crítico al intentar anular la orden de pago.");
    } finally {
      setIsAnulando(null);
    }
  };

  const handleLiquidarConfirm = async () => {
    if (!modalLiquidar.ordenId || !cuentaSeleccionadaId) return;

    setIsSubmittingLiquidacion(true);
    try {
      await liquidarOrdenIndividual(modalLiquidar.ordenId, parseInt(cuentaSeleccionadaId));
      toast.success("Orden liquidada y contabilizada en tesorería.");
      setModalLiquidar({ isOpen: false, ordenId: null });
      setCuentaSeleccionadaId("");
      fetchOrdenes();
    } catch (error: unknown) {
      const err = error as ApiError;
      toast.error(err.response?.data?.detail || "Error matemático o de liquidez al intentar pagar esta orden.");
    } finally {
      setIsSubmittingLiquidacion(false);
    }
  };

  if ((isLoading && ordenes.length === 0) || isLoadingMaestros) {
    return (
      <div className="flex h-64 items-center justify-center bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="flex flex-col items-center text-slate-500 transition-opacity duration-300">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-4" />
          <p className="text-sm font-medium">Cargando datos de Logística...</p>
        </div>
      </div>
    );
  }

  if (ordenes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center bg-slate-50 border border-slate-200 border-dashed rounded-lg">
        <div className="text-center text-slate-500 animate-in fade-in duration-500">
          <FileText className="w-10 h-10 mx-auto text-slate-300 mb-3" />
          <p className="text-sm font-medium text-slate-600">No hay órdenes en la logística</p>
          <p className="text-xs text-slate-400 mt-1">Generá una nueva Orden de Pago para visualizarla aquí.</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden animate-in fade-in duration-300 flex flex-col">

        {/* 🌟 VISTA MOBILE-FIRST: Tarjetas Apiladas (Ocultas en Desktop) */}
        <div className="block md:hidden divide-y divide-slate-100">
          {ordenes.map((orden) => {
            const isLiquidable = canLiquidar && ["BORRADOR", "FACTURA_ASIGNADA", "PENDIENTE_PAGO", "EN_LOTE", "PENDIENTE_AUTORIZACION"].includes(orden.estado_orden);
            const isAnulable = canAnular && orden.estado_orden !== "ANULADA" && orden.estado_orden !== "CERRADA";

            return (
              <div key={orden.id} className="p-4 bg-white hover:bg-slate-50 transition-colors flex flex-col gap-3">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold text-indigo-700 text-sm">{orden.codigo_trazabilidad}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{new Date(orden.created_at).toLocaleDateString('es-AR')}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-black text-slate-800 text-base">{formatCurrency(Number(orden.monto_estimado), orden.moneda)}</div>
                  </div>
                </div>

                <div className="bg-slate-50 p-2.5 rounded border border-slate-100">
                  <div className="font-semibold text-slate-800 text-sm line-clamp-1">{provMap[orden.proveedor_id] || `Prov #${orden.proveedor_id}`}</div>
                  <div className="text-xs text-slate-500 line-clamp-1">{concMap[orden.concepto_id] || `Concepto #${orden.concepto_id}`}</div>
                </div>

                <div className="flex items-center justify-between mt-1">
                  {orden.estado_orden === "BORRADOR" ? (
                    <span className="inline-flex items-center px-2 py-1 bg-slate-50 text-slate-600 border border-slate-200 rounded-md text-[10px] font-bold uppercase"><Clock className="w-3 h-3 mr-1" /> Borrador</span>
                  ) : orden.estado_orden === "FACTURA_ASIGNADA" || orden.estado_orden === "PENDIENTE_PAGO" ? (
                    <span className="inline-flex items-center px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-md text-[10px] font-bold uppercase"><Clock className="w-3 h-3 mr-1" /> Pendiente</span>
                  ) : orden.estado_orden === "EN_LOTE" || orden.estado_orden === "PENDIENTE_AUTORIZACION" ? (
                    <span className="inline-flex items-center px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-md text-[10px] font-bold uppercase"><Link2 className="w-3 h-3 mr-1" /> En Lote</span>
                  ) : orden.estado_orden === "AUTORIZADA" || orden.estado_orden === "CERRADA" ? (
                    <span className="inline-flex items-center px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md text-[10px] font-bold uppercase"><CheckCircle2 className="w-3 h-3 mr-1" /> Pagada</span>
                  ) : orden.estado_orden === "ANULADA" ? (
                    <span className="inline-flex items-center px-2 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded-md text-[10px] font-bold uppercase"><XCircle className="w-3 h-3 mr-1" /> Anulada</span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-1 bg-red-50 text-red-800 border border-red-300 rounded-md text-[10px] font-bold uppercase"><AlertCircle className="w-3 h-3 mr-1" /> {orden.estado_orden}</span>
                  )}

                  {orden.comprobante_interno_url && (
                    <button onClick={() => setVisorImagenUrl(orden.comprobante_interno_url!)} className="text-indigo-600 bg-indigo-50 p-1.5 rounded border border-indigo-100 active:scale-95 transition-transform" title="Ver comprobante adjunto">
                      <Eye className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="flex gap-2 w-full mt-1">
                  {isLiquidable && (
                    <button
                      onClick={() => { setCuentaSeleccionadaId(""); setModalLiquidar({ isOpen: true, ordenId: orden.id }); }}
                      className="flex-1 flex items-center justify-center px-2 py-2 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md text-[11px] font-bold uppercase transition-colors"
                    >
                      <Send className="w-3.5 h-3.5 mr-1" /> Liquidar
                    </button>
                  )}
                  {isAnulable && (
                    <button
                      onClick={() => handleAnularOrden(orden.id)}
                      disabled={isAnulando === orden.id}
                      className="flex-1 flex items-center justify-center px-2 py-2 text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-md text-[11px] font-bold uppercase disabled:opacity-50 transition-colors"
                    >
                      {isAnulando === orden.id ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <XCircle className="w-3.5 h-3.5 mr-1" />}
                      {isAnulando === orden.id ? "Anulando..." : "Anular"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* 🌟 VISTA DESKTOP: Tabla Tradicional (Oculta en Mobile) */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-semibold">Trazabilidad / ID</th>
                <th className="px-4 py-3 font-semibold">Creación</th>
                <th className="px-4 py-3 font-semibold">Concepto y Beneficiario</th>
                <th className="px-4 py-3 font-semibold text-right">Monto Neto</th>
                <th className="px-4 py-3 font-semibold text-center">Estado de Liquidación</th>
                <th className="px-4 py-3 font-semibold text-center">Auditoría y Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {ordenes.map((orden) => {
                const isLiquidable = canLiquidar && ["BORRADOR", "FACTURA_ASIGNADA", "PENDIENTE_PAGO", "EN_LOTE", "PENDIENTE_AUTORIZACION"].includes(orden.estado_orden);
                const isAnulable = canAnular && orden.estado_orden !== "ANULADA" && orden.estado_orden !== "CERRADA";

                return (
                  <tr key={orden.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-4 font-medium text-indigo-700 align-top">{orden.codigo_trazabilidad}</td>
                    <td className="px-4 py-4 text-slate-600 align-top">{new Date(orden.created_at).toLocaleDateString('es-AR')}</td>
                    <td className="px-4 py-4 align-top">
                      <div className="font-semibold text-slate-800">{provMap[orden.proveedor_id] || `Prov #${orden.proveedor_id}`}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{concMap[orden.concepto_id] || `Concepto #${orden.concepto_id}`}</div>
                    </td>
                    <td className="px-4 py-4 text-right font-bold text-slate-700 align-top">{formatCurrency(Number(orden.monto_estimado), orden.moneda)}</td>
                    <td className="px-4 py-4 text-center align-top">
                      <div className="flex justify-center">
                        {orden.estado_orden === "BORRADOR" ? (
                          <span className="inline-flex items-center px-2 py-1 bg-slate-50 text-slate-600 border border-slate-200 rounded-full text-[10px] font-bold uppercase"><Clock className="w-3 h-3 mr-1" /> Borrador</span>
                        ) : orden.estado_orden === "FACTURA_ASIGNADA" || orden.estado_orden === "PENDIENTE_PAGO" ? (
                          <span className="inline-flex items-center px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full text-[10px] font-bold uppercase"><Clock className="w-3 h-3 mr-1" /> Pendiente de Pago</span>
                        ) : orden.estado_orden === "EN_LOTE" || orden.estado_orden === "PENDIENTE_AUTORIZACION" ? (
                          <span className="inline-flex items-center px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase"><Link2 className="w-3 h-3 mr-1" /> Ensamblada (Lote)</span>
                        ) : orden.estado_orden === "AUTORIZADA" || orden.estado_orden === "CERRADA" ? (
                          <span className="inline-flex items-center px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase shadow-sm"><CheckCircle2 className="w-3 h-3 mr-1" /> Pagada / Cerrada</span>
                        ) : orden.estado_orden === "ANULADA" ? (
                          <span className="inline-flex items-center px-2 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded-full text-[10px] font-bold uppercase"><XCircle className="w-3 h-3 mr-1" /> Anulada / Extornada</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 bg-red-50 text-red-800 border border-red-300 rounded-full text-[10px] font-bold uppercase"><AlertCircle className="w-3 h-3 mr-1" /> {orden.estado_orden}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center align-top min-w-[160px]">
                      <div className="flex flex-col items-center space-y-1.5 w-full">
                        {orden.comprobante_interno_url ? (
                          <button onClick={() => setVisorImagenUrl(orden.comprobante_interno_url!)} className="inline-flex items-center justify-center p-1.5 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors border border-indigo-100 w-full group">
                            <Eye className="w-4 h-4 mr-1 group-hover:scale-110 transition-transform" /><span className="text-xs font-bold">Ver Ticket</span>
                          </button>
                        ) : <span className="text-slate-400 text-[11px] font-medium py-1">- Sin Ticket Adjunto -</span>}

                        <div className="text-[10px] text-slate-500 bg-slate-50 px-2 py-1 rounded border border-slate-200 text-center w-full shadow-sm">
                          Autor: <span className="font-semibold text-slate-700">{orden.creado_por_id || "Anónimo"}</span>
                        </div>

                        {isLiquidable && (
                          <button
                            onClick={() => { setCuentaSeleccionadaId(""); setModalLiquidar({ isOpen: true, ordenId: orden.id }); }}
                            className="mt-1 inline-flex items-center justify-center px-2 py-1.5 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition-colors text-[10px] font-bold uppercase w-full shadow-sm"
                            title="Descontar fondos de tesorería y marcar como pagada"
                          >
                            <Send className="w-3.5 h-3.5 mr-1" /> Liquidar Ahora
                          </button>
                        )}

                        {isAnulable && (
                          <button
                            onClick={() => handleAnularOrden(orden.id)}
                            disabled={isAnulando === orden.id}
                            className="mt-1 inline-flex items-center justify-center px-2 py-1.5 text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-md transition-colors text-[10px] font-bold uppercase w-full shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Revertir el pago y reabrir la deuda (Soft Delete)"
                          >
                            {isAnulando === orden.id ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <XCircle className="w-3.5 h-3.5 mr-1" />}
                            {isAnulando === orden.id ? "Anulando..." : "Anular Orden"}
                          </button>
                        )}

                        {!isAnulable && orden.estado_orden === "CERRADA" && (
                           <div className="mt-1 inline-flex items-center justify-center px-2 py-1 text-slate-400 text-[9px] uppercase font-bold text-center w-full" title="No se puede anular porque ya fue cruzada en Conciliación Bancaria.">
                             <ShieldAlert className="w-3 h-3 mr-1" /> Conciliada
                           </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* 🌟 PAGINACIÓN */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t border-slate-200 sm:px-6">
          <div className="flex items-center">
            <p className="text-sm text-slate-500">
              Página <span className="font-bold text-slate-700">{paginacion.page}</span>
            </p>
          </div>
          <div className="flex flex-1 justify-end space-x-2">
            <button
              onClick={handlePrevPage}
              disabled={paginacion.page === 1 || isLoading}
              className="relative inline-flex items-center rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
            </button>
            <button
              onClick={handleNextPage}
              disabled={!paginacion.hasMore || isLoading}
              className="relative inline-flex items-center rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              Siguiente <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>
      </div>

      {/* 🌟 FASE 4.2: MODAL RESPONSIVE (Bottom Sheet en Mobile, Modal en Desktop) */}
      {modalLiquidar.isOpen && (
        <div
          className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm sm:p-4 animate-in fade-in transition-all"
          onClick={() => !isSubmittingLiquidacion && setModalLiquidar({ isOpen: false, ordenId: null })}
        >
          <div
            className="bg-white rounded-t-2xl sm:rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-in slide-in-from-bottom-full sm:slide-in-from-bottom-0 sm:zoom-in-95 duration-300"
            onClick={e => e.stopPropagation()}
          >
            {/* Handle del Bottom Sheet (Mobile Only) */}
            <div className="w-full flex justify-center py-2 bg-emerald-600 sm:hidden">
              <div className="w-12 h-1.5 bg-white/30 rounded-full"></div>
            </div>

            <div className="bg-emerald-600 px-4 py-3 sm:py-4 text-white flex justify-between items-center shadow-sm">
              <h3 className="font-bold text-lg flex items-center">
                <Send className="w-5 h-5 mr-2" /> Liquidación Directa
              </h3>
              <button disabled={isSubmittingLiquidacion} onClick={() => setModalLiquidar({ isOpen: false, ordenId: null })} className="text-emerald-100 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 sm:p-6 space-y-5 pb-8 sm:pb-6 overflow-y-auto max-h-[80vh]">
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-lg text-sm flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <p>Estás a punto de pagar esta orden sin pasar por un Lote Interbanking. Seleccioná la cuenta que proveerá la liquidez para generar el impacto en tesorería.</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 flex items-center">
                  <Landmark className="w-4 h-4 mr-1 text-slate-500" /> Cuenta Bancaria de Origen
                </label>
                {/* Altura incrementada para áreas táctiles móviles */}
                <select
                  className="w-full h-12 sm:h-11 rounded-lg border border-slate-300 bg-white px-3 text-base sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all shadow-sm"
                  value={cuentaSeleccionadaId}
                  onChange={(e) => setCuentaSeleccionadaId(e.target.value)}
                  disabled={isSubmittingLiquidacion}
                >
                  <option value="">-- Seleccione el origen de los fondos --</option>
                  {cuentasBancarias.map(cb => (
                    <option key={cb.id} value={cb.id}>
                      {cb.banco} - {cb.numero_cuenta} ({cb.moneda})
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex flex-col-reverse sm:flex-row gap-3 sm:space-x-3 sm:gap-0">
                <button
                  onClick={() => setModalLiquidar({ isOpen: false, ordenId: null })}
                  disabled={isSubmittingLiquidacion}
                  className="w-full sm:flex-1 px-4 py-3 sm:py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 rounded-lg font-bold text-sm transition-colors shadow-sm"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleLiquidarConfirm}
                  disabled={isSubmittingLiquidacion || !cuentaSeleccionadaId}
                  className="w-full sm:flex-1 px-4 py-3 sm:py-2 bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg font-bold text-sm transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                >
                  {isSubmittingLiquidacion ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  {isSubmittingLiquidacion ? "Procesando..." : "Confirmar Débito"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 🌟 VISOR FOTOGRÁFICO DE AUDITORÍA */}
      {visorImagenUrl && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={() => setVisorImagenUrl(null)}>
          <div className="bg-white rounded-xl shadow-2xl overflow-hidden max-w-5xl w-full flex flex-col border border-slate-700" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center p-4 border-b border-slate-200 bg-slate-50 shadow-sm z-10">
              <div className="flex items-center text-slate-800 font-bold">
                <ImageIcon className="w-5 h-5 mr-2 text-indigo-600" />
                Auditoría Fotográfica
              </div>
              <div className="flex items-center space-x-3">
                <a
                  href={visorImagenUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 rounded-md font-bold text-xs transition-colors shadow-sm"
                >
                  <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                  Forzar Extracción
                </a>
                <button onClick={() => setVisorImagenUrl(null)} className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="p-6 bg-slate-200/50 flex flex-col items-center justify-center min-h-[60vh] relative">
              <img
                src={visorImagenUrl}
                alt="Ticket Original"
                referrerPolicy="no-referrer"
                className="max-h-[65vh] max-w-full object-contain rounded-md shadow-md bg-white border border-slate-300"
                onError={(e) => {
                  (e.target as HTMLImageElement).onerror = null;
                  (e.target as HTMLImageElement).src = "https://placehold.co/800x400/f8fafc/64748b?text=Bloqueo+de+Seguridad+del+Navegador.%5Cn%5CnHaz+clic+en+%27Forzar+Extracci%C3%B3n%27+arriba.";
                }}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

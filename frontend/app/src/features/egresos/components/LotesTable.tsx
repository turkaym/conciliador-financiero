import { useEffect, useState, Fragment } from "react";
import { useEgresosStore } from "@/store/useEgresosStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2, ArrowRightCircle, CheckCircle2, Download, AlertCircle, ChevronDown, ChevronRight, Eye, Image as ImageIcon, X, ExternalLink, ChevronLeft, Landmark } from "lucide-react";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import api from "@/api/axios";

export default function LotesTable() {
  const { lotes, fetchLotes, isLoading, solicitarAutorizacionLote, autorizarLote, exportarLote, paginacion, setPaginacion } = useEgresosStore();
  const user = useAuthStore((state) => state.user);
  const entidadId = useAuthStore((state) => state.entidadActiva?.id);

  const isAdmin = ["admin", "editor", "dueño"].includes(user?.role?.toLowerCase() || "");

  const lotesVisibles = lotes.filter(lote => {
    if (isAdmin) {
      // El Admin ve lo que está pendiente de firma Y lo que ya está listo para el banco.
      return ['PENDING_APPROVAL', 'AUTHORIZED_FOR_PAYMENT'].includes(lote.estado_lote);
    } else {
      // El Operador ve lo suyo
      return ['DRAFT', 'PENDING_APPROVAL'].includes(lote.estado_lote);
    }
  });

  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [visorImagenUrl, setVisorImagenUrl] = useState<string | null>(null);

  // 🌟 ESTADOS DEL MODAL DE AUTORIZACIÓN
  const [cuentasBancarias, setCuentasBancarias] = useState<any[]>([]);
  const [modalAutorizacion, setModalAutorizacion] = useState<{isOpen: boolean, loteId: number | null}>({isOpen: false, loteId: null});
  const [cuentaSeleccionadaId, setCuentaSeleccionadaId] = useState<string>("");
  const [isSubmittingAuth, setIsSubmittingAuth] = useState(false);

  useEffect(() => {
    void fetchLotes();
  }, [entidadId, fetchLotes, paginacion.page]);

  // 🌟 HIDRATACIÓN DE CUENTAS BANCARIAS
  useEffect(() => {
    let isMounted = true;
    const fetchCuentas = async () => {
      if (!isAdmin) return;
      try {
        const response = await api.get('/v1/bancos/cuentas');
        if (isMounted) setCuentasBancarias(response.data);
      } catch (error) {
        console.error("Error cargando cuentas bancarias:", error);
      }
    };
    fetchCuentas();
    return () => { isMounted = false; };
  }, [entidadId, isAdmin]);

  const handlePrevPage = () => {
    if (paginacion.page > 1) {
      setPaginacion(paginacion.page - 1);
    }
  };

  const handleNextPage = () => {
    if (paginacion.hasMore) {
      setPaginacion(paginacion.page + 1);
    }
  };

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) newExpanded.delete(id);
    else newExpanded.add(id);
    setExpandedRows(newExpanded);
  };

  const handleSolicitarFirma = async (lote_id: number) => {
    if (confirm("¿Estás seguro de enviar este lote a autorización gerencial? No podrás agregar más facturas a este bloque.")) {
      await solicitarAutorizacionLote(lote_id);
    }
  };

  const triggerAutorizacion = (lote_id: number) => {
    setModalAutorizacion({ isOpen: true, loteId: lote_id });
    setCuentaSeleccionadaId("");
  };

  const confirmarAutorizacion = async () => {
    if (!modalAutorizacion.loteId) return;
    if (!cuentaSeleccionadaId) {
        alert("Debe seleccionar una cuenta bancaria de origen para continuar.");
        return;
    }

    setIsSubmittingAuth(true);
    try {
        await autorizarLote(modalAutorizacion.loteId, parseInt(cuentaSeleccionadaId));
        setModalAutorizacion({ isOpen: false, loteId: null });
    } catch (error) {
        // El error ya es manejado por el store, no hacemos nada extra aquí
    } finally {
        setIsSubmittingAuth(false);
    }
  };

  const handleExportar = async (lote_id: number) => {
    if (confirm("Se iniciará la descarga del archivo TXT posicional para Interbanking. ¿Continuar?")) {
      await exportarLote(lote_id);
    }
  };

  if (isLoading && lotesVisibles.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-slate-200 border-dashed">
        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
      </div>
    );
  }

  if (lotesVisibles.length === 0) {
    return (
      <div className="flex flex-col h-48 items-center justify-center rounded-lg border border-slate-200 border-dashed bg-slate-50">
        <AlertCircle className="w-8 h-8 text-slate-400 mb-2" />
        <p className="text-sm font-medium text-slate-500">
          {isAdmin ? "Bandeja limpia. No hay lotes pendientes de autorización." : "No hay lotes en su área de trabajo."}
        </p>
      </div>
    );
  }

  return (
    <>
      <Card className="border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="block md:hidden divide-y divide-slate-100">
          {lotesVisibles.map((lote) => {
            const isExpanded = expandedRows.has(lote.id);
            return (
              <div key={lote.id} className="p-4 bg-white flex flex-col space-y-3">
                <div className="flex justify-between items-center">
                  <span className="font-mono text-sm font-bold text-slate-900 cursor-pointer" onClick={() => toggleRow(lote.id)}>
                    {lote.codigo_lote}
                  </span>
                  <button onClick={() => toggleRow(lote.id)} className="p-1 text-slate-400">
                    {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  </button>
                </div>

                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500">Estado</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    lote.estado_lote === 'DRAFT' ? 'bg-slate-100 text-slate-700' :
                    lote.estado_lote === 'PENDING_APPROVAL' ? 'bg-amber-100 text-amber-700' :
                    lote.estado_lote === 'AUTHORIZED_FOR_PAYMENT' ? 'bg-emerald-100 text-emerald-700' :
                    'bg-indigo-100 text-indigo-700'
                  }`}>
                    {lote.estado_lote.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="flex justify-between items-center text-sm font-bold">
                  <span className="text-slate-500">Monto Lote</span>
                  <span className="text-slate-800 text-base">{formatCurrency(lote.monto_total_lote, 'ARS')}</span>
                </div>

                <div className="pt-2 flex justify-end">
                  {lote.estado_lote === 'DRAFT' && (
                    <button onClick={() => handleSolicitarFirma(lote.id)} disabled={isLoading} className="w-full inline-flex items-center justify-center px-3 py-2 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-md">
                      Solicitar Firma
                    </button>
                  )}
                  {lote.estado_lote === 'PENDING_APPROVAL' && isAdmin && (
                    <button onClick={() => triggerAutorizacion(lote.id)} disabled={isLoading} className="w-full inline-flex items-center justify-center px-3 py-2 text-xs font-medium text-white bg-emerald-600 border border-transparent rounded-md shadow-sm">
                      Autorizar Pago
                    </button>
                  )}
                  {lote.estado_lote === 'AUTHORIZED_FOR_PAYMENT' && (
                    <button onClick={() => handleExportar(lote.id)} disabled={isLoading} className="w-full inline-flex items-center justify-center px-3 py-2 text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-md">
                      Exportar TXT
                    </button>
                  )}
                </div>

                {isExpanded && (
                  <div className="mt-2 pt-3 border-t border-slate-100 space-y-3">
                    <p className="text-xs font-bold text-slate-500 uppercase">Órdenes del Lote</p>
                    {lote.detalles && lote.detalles.length > 0 ? (
                      lote.detalles.map((det: any) => (
                        <div key={det.id} className="bg-slate-50 p-2 rounded border border-slate-200 flex flex-col space-y-1 text-xs">
                          <div className="flex justify-between font-medium">
                            <span className="text-indigo-600 font-mono">{det.orden_pago?.codigo_trazabilidad}</span>
                            <span className="text-slate-700">{formatCurrency(Number(det.monto_asignado_ars), 'ARS')}</span>
                          </div>
                          <div className="flex justify-between text-slate-500">
                            <span>Autor: {det.orden_pago?.creado_por_id || "Sistema"}</span>
                            {det.orden_pago?.comprobante_interno_url && (
                              <button onClick={() => setVisorImagenUrl(det.orden_pago!.comprobante_interno_url!)} className="text-indigo-600 underline">Auditar Ticket</button>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-400 italic text-center">No hay detalles.</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="hidden md:block overflow-x-auto scrollbar-hide">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-xs font-semibold">
              <tr>
                <th className="px-4 py-3 min-w-[180px]">Lote ID (Hub)</th>
                <th className="px-4 py-3 min-w-[120px]">Estado FSM</th>
                <th className="px-4 py-3 min-w-[140px] text-right">Monto Consolidado</th>
                <th className="px-4 py-3 min-w-[180px] text-right">Acciones de Aprobación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {lotesVisibles.map((lote) => {
                const isExpanded = expandedRows.has(lote.id);
                return (
                  <Fragment key={lote.id}>
                    <tr className={`transition-colors ${isExpanded ? 'bg-slate-50' : 'hover:bg-slate-50/50'}`}>
                      <td className="px-4 py-3 font-mono font-medium text-slate-900 flex items-center space-x-2">
                        <button
                          onClick={() => toggleRow(lote.id)}
                          className="p-1 hover:bg-slate-200 rounded-md transition-colors text-slate-500"
                        >
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                        <span className="cursor-pointer" onClick={() => toggleRow(lote.id)}>
                          {lote.codigo_lote}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          lote.estado_lote === 'DRAFT' ? 'bg-slate-100 text-slate-700' :
                          lote.estado_lote === 'PENDING_APPROVAL' ? 'bg-amber-100 text-amber-700' :
                          lote.estado_lote === 'AUTHORIZED_FOR_PAYMENT' ? 'bg-emerald-100 text-emerald-700' :
                          'bg-indigo-100 text-indigo-700'
                        }`}>
                          {lote.estado_lote.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-bold text-slate-800 text-right text-base">
                        {formatCurrency(lote.monto_total_lote, 'ARS')}
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        {lote.estado_lote === 'DRAFT' && (
                          <button onClick={() => handleSolicitarFirma(lote.id)} disabled={isLoading} className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-md hover:bg-amber-100">
                            <ArrowRightCircle className="w-3.5 h-3.5 mr-1" /> Solicitar Firma
                          </button>
                        )}
                        {lote.estado_lote === 'PENDING_APPROVAL' && isAdmin && (
                          <button onClick={() => triggerAutorizacion(lote.id)} disabled={isLoading} className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 border border-transparent rounded-md shadow-sm hover:bg-emerald-700">
                            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Autorizar Pago
                          </button>
                        )}
                        {lote.estado_lote === 'AUTHORIZED_FOR_PAYMENT' && (
                          <button onClick={() => handleExportar(lote.id)} disabled={isLoading} className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-md hover:bg-indigo-100">
                            <Download className="w-3.5 h-3.5 mr-1" /> Exportar TXT
                          </button>
                        )}
                      </td>
                    </tr>

                    {isExpanded && (
                      <tr className="bg-slate-50/50 border-b border-slate-100">
                        <td colSpan={4} className="p-0">
                          <div className="px-12 py-4 animate-in slide-in-from-top-2 duration-200">
                            <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
                              <div className="bg-slate-100/50 px-4 py-2 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                                Desglose de Operaciones (Auditoría)
                              </div>
                              <table className="w-full text-xs text-left">
                                <thead className="bg-white text-slate-400">
                                  <tr>
                                    <th className="px-4 py-2 font-medium">OP Origen</th>
                                    <th className="px-4 py-2 font-medium text-right">Monto Original</th>
                                    <th className="px-4 py-2 font-medium text-center">Autor</th>
                                    <th className="px-4 py-2 font-medium text-center">Comprobante Interno</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {lote.detalles && lote.detalles.length > 0 ? (
                                    lote.detalles.map((det: any) => (
                                      <tr key={det.id} className="hover:bg-slate-50">
                                        <td className="px-4 py-2 font-mono text-indigo-600 font-medium">
                                          {det.orden_pago?.codigo_trazabilidad || "OP Desconocida"}
                                        </td>
                                        <td className="px-4 py-2 text-right font-semibold text-slate-700">
                                          {formatCurrency(Number(det.monto_asignado_ars), 'ARS')}
                                        </td>
                                        <td className="px-4 py-2 text-center text-slate-500">
                                          {det.orden_pago?.creado_por_id || "Sistema"}
                                        </td>
                                        <td className="px-4 py-2 text-center">
                                          {det.orden_pago?.comprobante_interno_url ? (
                                            <button onClick={() => setVisorImagenUrl(det.orden_pago!.comprobante_interno_url!)} className="inline-flex items-center justify-center p-1.5 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded transition-colors border border-indigo-100">
                                              <Eye className="w-3.5 h-3.5 mr-1" /> <span className="font-bold">Auditar</span>
                                            </button>
                                          ) : (
                                            <span className="text-slate-300 font-medium italic">Bypass Fiscal</span>
                                          )}
                                        </td>
                                      </tr>
                                    ))
                                  ) : (
                                    <tr>
                                      <td colSpan={4} className="px-4 py-4 text-center text-slate-400 italic">No se encontraron detalles.</td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t border-slate-200 mt-auto">
          <div className="flex items-center text-sm text-slate-500">
            Página <span className="font-bold text-slate-700 ml-1">{paginacion.page}</span>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handlePrevPage}
              disabled={paginacion.page === 1 || isLoading}
              className="inline-flex items-center px-3 py-1.5 text-sm font-semibold text-slate-700 bg-white ring-1 ring-inset ring-slate-300 hover:bg-slate-50 rounded-md disabled:opacity-50"
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
            </button>
            <button
              onClick={handleNextPage}
              disabled={!paginacion.hasMore || isLoading}
              className="inline-flex items-center px-3 py-1.5 text-sm font-semibold text-slate-700 bg-white ring-1 ring-inset ring-slate-300 hover:bg-slate-50 rounded-md disabled:opacity-50"
            >
              Siguiente <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>
      </Card>

      {/* 🌟 MODAL DE AUTORIZACIÓN FINANCIERA */}
      {modalAutorizacion.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in" onClick={() => !isSubmittingAuth && setModalAutorizacion({ isOpen: false, loteId: null })}>
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="bg-emerald-600 p-4 text-white flex justify-between items-center">
              <h3 className="font-bold text-lg flex items-center">
                <CheckCircle2 className="w-5 h-5 mr-2" /> Autorización Gerencial
              </h3>
              <button disabled={isSubmittingAuth} onClick={() => setModalAutorizacion({ isOpen: false, loteId: null })} className="text-emerald-100 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div className="bg-amber-50 border border-amber-200 text-amber-800 p-3 rounded-lg text-sm flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <p>La autorización es irrevocable y habilitará el egreso real de fondos. Seleccione la cuenta de origen para registrar contablemente este desembolso.</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 flex items-center">
                  <Landmark className="w-4 h-4 mr-1 text-slate-500" /> Caja / Cuenta Bancaria de Origen
                </label>
                <select
                  className="w-full h-11 rounded-md border border-slate-300 bg-white px-3 text-sm focus:ring-2 focus:ring-emerald-500 outline-none transition-shadow"
                  value={cuentaSeleccionadaId}
                  onChange={(e) => setCuentaSeleccionadaId(e.target.value)}
                  disabled={isSubmittingAuth}
                >
                  <option value="">-- Seleccione el origen de los fondos --</option>
                  {cuentasBancarias.map(cb => (
                    <option key={cb.id} value={cb.id}>
                      {cb.banco} - {cb.numero_cuenta}
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex space-x-3">
                <button
                  onClick={() => setModalAutorizacion({ isOpen: false, loteId: null })}
                  disabled={isSubmittingAuth}
                  className="flex-1 px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-md font-semibold text-sm transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={confirmarAutorizacion}
                  disabled={isSubmittingAuth || !cuentaSeleccionadaId}
                  className="flex-1 px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-700 rounded-md font-semibold text-sm transition-colors flex items-center justify-center disabled:opacity-50"
                >
                  {isSubmittingAuth ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirmar Firma"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {visorImagenUrl && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={() => setVisorImagenUrl(null)}>
          <div className="bg-white rounded-xl shadow-2xl overflow-hidden max-w-5xl w-full flex flex-col border border-slate-700" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center p-4 border-b border-slate-200 bg-slate-50 shadow-sm z-10">
              <div className="flex items-center text-slate-800 font-bold">
                <ImageIcon className="w-5 h-5 mr-2 text-indigo-600" />
                Auditoría Fotográfica
              </div>
              <div className="flex items-center space-x-3">
                <a href={visorImagenUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-4 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 rounded-md font-bold text-xs shadow-sm">
                  <ExternalLink className="w-3.5 h-3.5 mr-1.5" /> Forzar Extracción (Nueva Pestaña)
                </a>
                <button onClick={() => setVisorImagenUrl(null)} className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="p-6 bg-slate-200/50 flex flex-col items-center justify-center min-h-[60vh] relative">
              <img
                src={visorImagenUrl}
                alt="Ticket de Respaldo"
                referrerPolicy="no-referrer"
                className="max-h-[65vh] max-w-full object-contain rounded-md shadow-md bg-white border border-slate-300"
                onError={(e) => {
                  (e.target as HTMLImageElement).onerror = null;
                  (e.target as HTMLImageElement).src = "https://placehold.co/800x400/f8fafc/64748b?text=Bloqueo+de+Seguridad+del+Navegador.%5Cn%5CnHaz+clic+en+%27Forzar+Extracci%C3%B3n%27+arriba.";
                }}
              />
              <div className="mt-4 bg-white px-3 py-2 rounded border border-slate-200 w-full max-w-3xl text-center shadow-sm">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest block mb-1">Ruta de Origen de Datos</span>
                <span className="font-mono text-[10px] text-slate-600 break-all select-all">{visorImagenUrl}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

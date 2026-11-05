import React, { useState, useEffect } from "react"
import { usePadrones } from "@/features/padrones/hooks/usePadrones"
import { useAuthStore } from "@/store/useAuthStore"

// Componentes
import { ImportarPadronModal } from "@/features/padrones/components/ImportarPadronModal"
import AfipVaultForm from "@/components/AfipVaultForm"
import ConfiguracionFiscalABM from "@/features/padrones/components/ConfiguracionFiscalABM"
// 🌟 FIX FASE C: Importación del nuevo Exportador Dedicado
import ExportadorFiscal from "@/features/reportes/components/ExportadorFiscal"

// Iconos (Limpiados de importaciones sin uso)
import { FileText, Database, ShieldAlert, CheckCircle2, Landmark, ShieldCheck, Loader2, Settings, Search, RefreshCw, XCircle } from "lucide-react"

export default function Padrones() {
  const {
    isLoading, isPolling, errorMsg, globalMessage, setErrorMsg, uploadPadron,
    historial, isFetchingHistorial, fetchHistorial,
    searchResult, isSearching, buscarCuit
  } = usePadrones();

  const user = useAuthStore((state) => state.user);
  const isAdmin = ["admin", "dueño", "editor"].includes(user?.role?.toLowerCase() || "");
  const [activeTab, setActiveTab] = useState(isAdmin ? "reglas" : "ingesta");

  // Estados locales para el Inspector Fiscal
  const [searchCuit, setSearchCuit] = useState("");
  const [searchJur, setSearchJur] = useState("ARBA");
  const [searchPer, setSearchPer] = useState("");

  // Cargar historial al montar la pestaña
  useEffect(() => {
    if (activeTab === "ingesta") {
      fetchHistorial();
    }
  }, [activeTab, fetchHistorial]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchCuit && searchPer) {
      buscarCuit(searchCuit.replace(/\D/g, ''), searchJur, searchPer.replace("-", ""));
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500 pb-12 relative h-full flex flex-col">

      {/* Header Fijo */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-6 shrink-0">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Landmark className="h-6 w-6 sm:h-8 sm:w-8 text-indigo-600" />
            Workspace Fiscal
          </h1>
          <p className="text-sm sm:text-base text-slate-500 mt-1">
            Gestión de padrones, matriz impositiva y conectividad AFIP/ARCA.
          </p>
        </div>

        <ImportarPadronModal
          isLoading={isLoading}
          isPolling={isPolling}
          errorMsg={errorMsg}
          onSubmit={uploadPadron}
          onClearError={() => setErrorMsg(null)}
        />
      </div>

      {globalMessage && (
        <div className={`p-4 rounded-lg border flex items-center gap-3 shrink-0 ${
          globalMessage.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          {globalMessage.type === 'success' ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <ShieldAlert className="h-5 w-5 shrink-0" />}
          <span className="font-medium text-sm">{globalMessage.text}</span>
        </div>
      )}

      {/* 🌟 ENRUTADOR RBAC (TABS MOBILE-FIRST) */}
      <div className="flex space-x-1 border-b border-slate-200 overflow-x-auto scrollbar-hide shrink-0 pb-px">
        {isAdmin && (
          <button onClick={() => setActiveTab("reglas")} className={`flex items-center px-4 py-2 text-sm font-bold border-b-2 whitespace-nowrap transition-colors ${activeTab === "reglas" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"}`}>
            <Settings className="w-4 h-4 mr-2" /> Matriz Impositiva
          </button>
        )}

        <button onClick={() => setActiveTab("ingesta")} className={`flex items-center px-4 py-2 text-sm font-bold border-b-2 whitespace-nowrap transition-colors ${activeTab === "ingesta" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"}`}>
          <Database className="w-4 h-4 mr-2" /> Padrones de Riesgo
        </button>

        {isAdmin && (
          <button onClick={() => setActiveTab("sire")} className={`flex items-center px-4 py-2 text-sm font-bold border-b-2 whitespace-nowrap transition-colors ${activeTab === "sire" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"}`}>
            <FileText className="w-4 h-4 mr-2" /> Exportador DDJJ
          </button>
        )}

        {isAdmin && (
          <button onClick={() => setActiveTab("boveda")} className={`flex items-center px-4 py-2 text-sm font-bold border-b-2 whitespace-nowrap transition-colors ${activeTab === "boveda" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"}`}>
            <ShieldCheck className="w-4 h-4 mr-2" /> Bóveda AFIP
          </button>
        )}
      </div>

      {/* 🌟 RENDERIZADO DINÁMICO */}
      <div className="flex-1 overflow-y-auto">

        {activeTab === "reglas" && isAdmin && (
          <div className="animate-in fade-in duration-300 py-2">
            <ConfiguracionFiscalABM />
          </div>
        )}

        {/* CENTRO DE CONTROL DE PADRONES Y BUSCADOR */}
        {activeTab === "ingesta" && (
          <div className="space-y-8 animate-in fade-in duration-300 py-2">

            {/* Inspector Fiscal */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="bg-slate-50 border-b border-slate-200 p-4">
                <h3 className="font-bold text-slate-800 flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-600" /> Inspector Fiscal
                </h3>
                <p className="text-xs text-slate-500 mt-1">Busque la alícuota aplicable a un proveedor en un padrón específico.</p>
              </div>
              <div className="p-4 sm:p-5">
                <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4 items-end">
                  <div className="w-full sm:w-1/3">
                    <label className="text-[11px] font-bold text-slate-500 uppercase block mb-1">CUIT del Proveedor</label>
                    <input
                      type="text" required maxLength={11} placeholder="Ej: 30111111118"
                      value={searchCuit} onChange={(e) => setSearchCuit(e.target.value)}
                      className="w-full h-10 rounded-md border border-slate-300 px-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                  <div className="w-full sm:w-1/4">
                    <label className="text-[11px] font-bold text-slate-500 uppercase block mb-1">Jurisdicción</label>
                    <select value={searchJur} onChange={(e) => setSearchJur(e.target.value)} className="w-full h-10 rounded-md border border-slate-300 px-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                      <option value="ARBA">ARBA</option>
                      <option value="AGIP">AGIP</option>
                    </select>
                  </div>
                  <div className="w-full sm:w-1/4">
                    <label className="text-[11px] font-bold text-slate-500 uppercase block mb-1">Período (YYYYMM)</label>
                    <input
                      type="month" required value={searchPer} onChange={(e) => setSearchPer(e.target.value)}
                      className="w-full h-10 rounded-md border border-slate-300 px-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                  <button type="submit" disabled={isSearching || !searchCuit || !searchPer} className="w-full sm:w-auto h-10 px-6 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-md shadow-md flex items-center justify-center transition-all disabled:opacity-60">
                    {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Consultar"}
                  </button>
                </form>

                {searchResult && (
                  <div className="mt-6 p-4 bg-indigo-50 border border-indigo-100 rounded-lg flex flex-col sm:flex-row gap-6">
                    <div>
                      <p className="text-xs text-indigo-500 font-bold uppercase">CUIT Encontrado</p>
                      <p className="font-mono text-lg font-bold text-indigo-900">{searchResult.cuit}</p>
                    </div>
                    <div>
                      <p className="text-xs text-indigo-500 font-bold uppercase">% Retención</p>
                      <p className="text-lg font-bold text-indigo-900">{searchResult.alicuota_retencion}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-indigo-500 font-bold uppercase">% Percepción</p>
                      <p className="text-lg font-bold text-indigo-900">{searchResult.alicuota_percepcion}%</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Monitor de Ingestas */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="bg-slate-50 border-b border-slate-200 p-4 flex justify-between items-center">
                <div>
                  <h3 className="font-bold text-slate-800 flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-600" /> Monitor de Ingestas
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">Bitácora histórica de carga y procesamiento masivo.</p>
                </div>
                <button onClick={fetchHistorial} disabled={isFetchingHistorial} className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors">
                  <RefreshCw className={`w-5 h-5 ${isFetchingHistorial ? 'animate-spin' : ''}`} />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/50 border-b border-slate-200 text-slate-500 text-[11px] uppercase tracking-wider">
                      <th className="px-4 sm:px-6 py-3 font-bold whitespace-nowrap">Fecha / Hora</th>
                      <th className="px-4 sm:px-6 py-3 font-bold whitespace-nowrap">Archivo</th>
                      <th className="px-4 sm:px-6 py-3 font-bold whitespace-nowrap">Período</th>
                      <th className="px-4 sm:px-6 py-3 font-bold whitespace-nowrap">Filas</th>
                      <th className="px-4 sm:px-6 py-3 font-bold whitespace-nowrap">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {historial.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-8 text-center text-slate-400 text-sm">
                          No hay registros de ingesta para mostrar.
                        </td>
                      </tr>
                    ) : (
                      historial.map((row) => (
                        <tr key={row.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 sm:px-6 py-3 text-xs sm:text-sm text-slate-600 whitespace-nowrap">
                            {new Date(row.iniciado_el).toLocaleString()}
                          </td>
                          <td className="px-4 sm:px-6 py-3 text-xs sm:text-sm font-medium text-slate-900 max-w-[150px] sm:max-w-[200px] truncate" title={row.nombre_archivo}>
                            {row.nombre_archivo.split('/').pop()}
                          </td>
                          <td className="px-4 sm:px-6 py-3 text-xs sm:text-sm text-slate-600 whitespace-nowrap">
                            <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded font-mono text-[10px] sm:text-xs">{row.jurisdiccion} {row.periodo}</span>
                          </td>
                          <td className="px-4 sm:px-6 py-3 text-xs sm:text-sm text-slate-600 font-mono whitespace-nowrap">
                            {row.registros_insertados.toLocaleString()}
                          </td>
                          <td className="px-4 sm:px-6 py-3 text-xs sm:text-sm whitespace-nowrap">
                            {row.estado === 'EXITO' && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <CheckCircle2 className="w-3 h-3 shrink-0" /> Completado
                              </span>
                            )}
                            {row.estado === 'PROCESANDO' && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                                <Loader2 className="w-3 h-3 animate-spin shrink-0" /> Procesando
                              </span>
                            )}
                            {row.estado === 'FALLO' && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200" title={row.mensaje_error}>
                                <XCircle className="w-3 h-3 shrink-0" /> Error
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* 🌟 FIX FASE C: COMPONENTE EXPORTADOR DEDICADO */}
        {activeTab === "sire" && isAdmin && (
          <div className="animate-in fade-in duration-300 py-4 max-w-4xl">
             <ExportadorFiscal />
          </div>
        )}

        {/* BÓVEDA AFIP */}
        {activeTab === "boveda" && isAdmin && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start animate-in fade-in duration-300 py-4">
            <div className="w-full">
              <AfipVaultForm />
            </div>
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-6 flex flex-col justify-center h-full shadow-inner">
              <h3 className="font-bold text-slate-800 mb-3 flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-indigo-600 shrink-0" />
                Arquitectura Zero Trust
              </h3>
              <p className="text-sm text-slate-600 mb-4 leading-relaxed">
                Por normativas de cumplimiento, las credenciales operan bajo aislamiento estricto. La llave privada nunca se almacena en texto plano.
              </p>
              <ul className="text-sm text-slate-600 space-y-3">
                <li className="flex items-start gap-2">
                  <span className="text-indigo-500 font-bold mt-0.5">•</span>
                  <span><strong>Cifrado Simétrico:</strong> AES-128 (Fernet) para proteger el archivo `.key` en reposo.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-500 font-bold mt-0.5">•</span>
                  <span><strong>Aislamiento Inquilino:</strong> Credenciales atadas exclusivamente al CUIT de la Razón Social.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-500 font-bold mt-0.5">•</span>
                  <span><strong>Delegación Asíncrona:</strong> Celery desencripta la llave al vuelo en memoria RAM al firmar el XML.</span>
                </li>
              </ul>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
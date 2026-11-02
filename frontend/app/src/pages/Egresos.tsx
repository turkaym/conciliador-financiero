import { useEffect, useState } from "react";
import { useAuthStore } from "../store/useAuthStore";
import { useEgresosStore } from "../store/useEgresosStore";
import { Receipt, Search, Loader2, PlusCircle, CheckSquare, Building, FileText, Coffee } from "lucide-react";
import { Card, CardContent } from "../components/ui/card";

// Componentes
import SifonFiscalForm from "../features/egresos/components/SifonFiscalForm";
import OrdenPagoForm from "../features/egresos/components/OrdenPagoForm";
import LogisticaTable from "../features/egresos/components/LogisticaTable";
import LotesTable from "../features/egresos/components/LotesTable";
import EnsambladoraLotes from "../features/egresos/components/EnsambladoraLotes";

export default function EgresosPage() {
  const user = useAuthStore((state) => state.user);
  const entidadActiva = useAuthStore((state) => state.entidadActiva);

  const { destroyState, filtros, setFiltros, fetchOrdenes, isLoading } = useEgresosStore();
  const [searchTerm, setSearchTerm] = useState(filtros.q || "");

  // 🌟 FIX UX: Sub-estado para el toggler de tipo de carga
  const [tipoCarga, setTipoCarga] = useState<'factura' | 'gasto_menor'>('factura');

  // RBAC Estricto
  const isChecker = ["admin", "editor", "dueño"].includes(user?.role?.toLowerCase() || "");
  const [activeTab, setActiveTab] = useState("historial");

  useEffect(() => {
    return () => {
      destroyState();
    };
  }, [entidadActiva?.id, destroyState]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (filtros.q !== searchTerm) {
        setFiltros({ q: searchTerm });
        fetchOrdenes(true);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm, filtros.q, setFiltros, fetchOrdenes]);

  const handleDateChange = (type: 'inicio' | 'fin', value: string) => {
    const newFiltros = { ...filtros, [type === 'inicio' ? 'fecha_inicio' : 'fecha_fin']: value };
    const start = new Date(newFiltros.fecha_inicio);
    const end = new Date(newFiltros.fecha_fin);
    const diffDays = Math.ceil(Math.abs(end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays > 180) {
      alert("🛑 El rango máximo de búsqueda histórica es de 6 meses para proteger el rendimiento de su dispositivo.");
      return;
    }
    setFiltros(newFiltros);
  };

  return (
    <div className="flex-1 space-y-4 p-4 md:p-6 lg:p-8 pt-4 overflow-y-auto overflow-x-hidden flex flex-col relative bg-slate-50/50 min-h-screen">

      {/* 🌟 ENCABEZADO MOBILE-FIRST */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Pagos y Egresos</h2>
          <p className="text-sm text-slate-500">Gestión de proveedores, gastos operativos e Interbanking.</p>
        </div>
      </div>

      {/* 🌟 SISTEMA DE PESTAÑAS (TABS) MOBILE-FIRST & RBAC ESTRICTO */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-1.5 flex flex-wrap lg:flex-nowrap gap-1 shrink-0">
        <button
          onClick={() => setActiveTab("historial")}
          className={`flex-1 min-w-[140px] flex items-center justify-center space-x-2 px-3 py-2.5 text-sm font-medium rounded-lg transition-all ${activeTab === "historial" ? "bg-slate-900 text-white shadow-md" : "text-slate-600 hover:bg-slate-100"}`}
        >
          <Receipt className="w-4 h-4 shrink-0" />
          <span className="truncate">Historial General</span>
        </button>

        <button
          onClick={() => setActiveTab("carga")}
          className={`flex-1 min-w-[140px] flex items-center justify-center space-x-2 px-3 py-2.5 text-sm font-medium rounded-lg transition-all ${activeTab === "carga" ? "bg-indigo-600 text-white shadow-md" : "text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"}`}
        >
          <PlusCircle className="w-4 h-4 shrink-0" />
          <span className="truncate">Nuevo Egreso</span>
        </button>

        {isChecker && (
          <>
            <button
              onClick={() => setActiveTab("autorizaciones")}
              className={`flex-1 min-w-[140px] flex items-center justify-center space-x-2 px-3 py-2.5 text-sm font-medium rounded-lg transition-all ${activeTab === "autorizaciones" ? "bg-emerald-600 text-white shadow-md" : "text-slate-600 hover:bg-emerald-50 hover:text-emerald-700"}`}
            >
              <CheckSquare className="w-4 h-4 shrink-0" />
              <span className="truncate">Bandeja de Lotes</span>
            </button>

            <button
              onClick={() => setActiveTab("interbanking")}
              className={`flex-1 min-w-[140px] flex items-center justify-center space-x-2 px-3 py-2.5 text-sm font-medium rounded-lg transition-all ${activeTab === "interbanking" ? "bg-blue-600 text-white shadow-md" : "text-slate-600 hover:bg-blue-50 hover:text-blue-700"}`}
            >
              <Building className="w-4 h-4 shrink-0" />
              <span className="truncate">Hub Interbanking</span>
            </button>
          </>
        )}
      </div>

      {/* 🌟 BARRA DE FILTROS (Se oculta inteligentemente si no estamos en Historial) */}
      {activeTab === "historial" && (
        <Card className="border-slate-200 shadow-sm shrink-0 animate-in fade-in slide-in-from-top-2">
          <CardContent className="p-4 sm:p-5 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Desde</label>
                <input
                  type="date"
                  className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                  value={filtros.fecha_inicio}
                  onChange={(e) => handleDateChange('inicio', e.target.value)}
                />
              </div>
              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Hasta</label>
                <input
                  type="date"
                  className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                  value={filtros.fecha_fin}
                  onChange={(e) => handleDateChange('fin', e.target.value)}
                />
              </div>
              <div className="flex flex-col space-y-1.5 lg:col-span-2">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Búsqueda General (Proveedor/CUIT)</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Ej: Servicios IT S.A..."
                    className="flex h-10 w-full rounded-md border border-slate-300 bg-white pl-10 pr-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-col-reverse sm:flex-row justify-end items-center gap-3 pt-4 border-t border-slate-100 mt-2">
              <button
                onClick={() => { setSearchTerm(""); destroyState(); }}
                className="w-full sm:w-auto px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-md shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                Limpiar Filtros
              </button>
              <button
                onClick={() => fetchOrdenes(true)}
                disabled={isLoading}
                className="w-full sm:w-auto px-6 py-2 text-sm font-bold text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition-all flex items-center justify-center"
              >
                {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Search className="w-4 h-4 mr-2" />}
                {isLoading ? "Buscando..." : "Aplicar y Buscar"}
              </button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 🌟 ÁREA DE RENDERIZADO DINÁMICO */}
      <div className="flex-1 relative">

        {/* 1. VISOR HISTÓRICO */}
        {activeTab === "historial" && (
          <div className="animate-in fade-in duration-300 h-full">
            <LogisticaTable />
          </div>
        )}

        {/* 2. HUB DE CARGA (Con Toggler Interno para UX limpia) */}
        {activeTab === "carga" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-300 space-y-4">

            <div className="flex bg-white rounded-lg shadow-sm border border-slate-200 p-1 w-full max-w-md mx-auto">
              <button
                onClick={() => setTipoCarga('factura')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-all ${tipoCarga === 'factura' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <FileText className="w-4 h-4" /> Pago de Factura B2B
              </button>
              <button
                onClick={() => setTipoCarga('gasto_menor')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-all ${tipoCarga === 'gasto_menor' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <Coffee className="w-4 h-4" /> Gasto de Caja Chica
              </button>
            </div>

            {tipoCarga === 'factura' ? (
              <OrdenPagoForm key={`factura_${entidadActiva?.id}`} />
            ) : (
              <SifonFiscalForm key={`gasto_${entidadActiva?.id}`} />
            )}
          </div>
        )}

        {/* 3. BANDEJA DE AUTORIZACIONES (Solo Tesorero/Admin) */}
        {activeTab === "autorizaciones" && isChecker && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-300">
            {/* LotesTable ahora asume el rol de Bandeja de Aprobaciones de Órdenes Sueltas */}
            <LotesTable />
          </div>
        )}

        {/* 4. HUB INTERBANKING (Solo Tesorero/Admin) */}
        {activeTab === "interbanking" && isChecker && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-300">
            {/* EnsambladoraLotes recupera su rol verdadero: Agrupar por Banco y exportar TXT */}
            <EnsambladoraLotes />
          </div>
        )}

      </div>
    </div>
  );
}
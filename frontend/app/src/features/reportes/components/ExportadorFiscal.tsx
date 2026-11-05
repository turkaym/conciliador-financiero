import { useState } from "react";
import { Download, FileText, Building2, Calendar, Loader2, Landmark } from "lucide-react";
import api from "@/api/axios";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "react-toastify";

export default function ExportadorFiscal() {
  const { entidadActiva, tenant_id } = useAuthStore();
  const [periodo, setPeriodo] = useState("");
  const [jurisdiccion, setJurisdiccion] = useState("AFIP");
  const [claseTributo, setClaseTributo] = useState("RETENCION_EMITIDA");
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    if (!periodo || !entidadActiva?.id || !tenant_id) {
      toast.warning("Seleccione un período fiscal válido.");
      return;
    }

    // Formatear YYYY-MM a YYYYMM (Ej: 2026-06 -> 202606)
    const formattedPeriodo = periodo.replace("-", "");

    setIsExporting(true);
    try {
      // Consumo de tu endpoint en fiscal.py
      const response = await api.get(`/v1/fiscal/export/sire`, {
        params: {
          periodo_fiscal: formattedPeriodo,
          jurisdiccion,
          clase_tributo: claseTributo
        },
        responseType: 'blob' // Clave para manejar archivos binarios/texto
      });

      // Zero-Disk Download en Frontend
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `DDJJ_${jurisdiccion}_${claseTributo}_${formattedPeriodo}.txt`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success("Declaración Jurada exportada con éxito. Lista para subir a ARCA.");
    } catch (error: any) {
      toast.error("Error al generar el archivo. Verifique que existan retenciones en el período seleccionado.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="bg-slate-50 border-b border-slate-200 p-6 flex items-center gap-4">
        <div className="p-3 bg-indigo-100 text-indigo-700 rounded-lg shrink-0">
          <Landmark className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-800">Exportador de DDJJ y Padrones</h2>
          <p className="text-sm text-slate-500">
            Generación de archivos posicionales (TXT) para aplicativos SIRE/SICORE de ARCA y ARBA.
          </p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" /> Período Fiscal
            </label>
            <input
              type="month"
              className="w-full h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-slate-400" /> Jurisdicción
            </label>
            <select
              className="w-full h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={jurisdiccion}
              onChange={(e) => setJurisdiccion(e.target.value)}
            >
              <option value="AFIP">Nacional (ARCA / AFIP)</option>
              <option value="ARBA">Buenos Aires (ARBA)</option>
              <option value="AGIP">CABA (AGIP)</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" /> Tipo de Padrón
            </label>
            <select
              className="w-full h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={claseTributo}
              onChange={(e) => setClaseTributo(e.target.value)}
            >
              <option value="RETENCION_EMITIDA">Retenciones Practicadas a Proveedores</option>
              <option value="PERCEPCION_SUFRIDA">Percepciones Sufridas</option>
            </select>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-100 flex justify-end">
          <button
            onClick={handleExport}
            disabled={isExporting || !periodo}
            className="w-full sm:w-auto px-6 py-2.5 text-sm font-bold text-white bg-indigo-600 border border-transparent rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
          >
            {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {isExporting ? "Compilando TXT..." : "Descargar Lote Validador"}
          </button>
        </div>
      </div>
    </div>
  );
}
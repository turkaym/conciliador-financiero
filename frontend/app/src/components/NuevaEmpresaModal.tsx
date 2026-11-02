import { useState } from "react";
import api from "@/api/axios";
import { useAuthStore } from "@/store/useAuthStore";
import { X, Loader2, Building2, AlertCircle } from "lucide-react";
import { isValidCUIT } from "@/lib/utils";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function NuevaEmpresaModal({ isOpen, onClose, onSuccess }: Props) {
  const { tenant_id } = useAuthStore();

  // 🌟 FIX FASE 11: Inyección de condicion_fiscal obligatoria
  const [formData, setFormData] = useState({
    cuit: "",
    razon_social: "",
    nombre_fantasia: "",
    condicion_fiscal: "RESPONSABLE_INSCRIPTO"
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleCuitChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const onlyNumbers = e.target.value.replace(/\D/g, '');
    if (onlyNumbers.length <= 11) {
      setFormData({ ...formData, cuit: onlyNumbers });
    }
  };

  const isCuitComplete = formData.cuit.length === 11;
  const isCuitValid = isCuitComplete && isValidCUIT(formData.cuit);
  const showCuitError = isCuitComplete && !isCuitValid;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isCuitValid) return;

    setError("");
    setLoading(true);

    try {
      await api.post(`/v1/entidades/${tenant_id}`, {
        cuit: formData.cuit,
        razon_social: formData.razon_social.trim(),
        nombre_fantasia: formData.nombre_fantasia.trim() || formData.razon_social.trim(),
        condicion_fiscal: formData.condicion_fiscal // 🌟 PAYLOAD E2E
      });
      onSuccess();
      setFormData({ cuit: "", razon_social: "", nombre_fantasia: "", condicion_fiscal: "RESPONSABLE_INSCRIPTO" });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Fallo al crear la entidad. Verifique los datos.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90dvh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">

        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
              <Building2 className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-slate-800">Nueva Razón Social</h2>
          </div>
          <button onClick={onClose} disabled={loading} className="text-slate-400 hover:text-slate-600 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4 overflow-y-auto">
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-md flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1">
            <label htmlFor="cuit" className="text-sm font-semibold text-slate-700">CUIT *</label>
            <input
              id="cuit" required autoFocus type="text" inputMode="numeric"
              placeholder="Ej: 30123456789" value={formData.cuit}
              onChange={handleCuitChange} disabled={loading}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 transition-colors disabled:opacity-50 ${
                showCuitError ? "border-red-300 focus:ring-red-500 bg-red-50/50" : "border-slate-200 focus:ring-indigo-500"
              }`}
            />
            {showCuitError && <p className="text-xs text-red-500 mt-1 font-medium">El CUIT ingresado no es válido.</p>}
          </div>

          <div className="space-y-1">
            <label htmlFor="razon_social" className="text-sm font-semibold text-slate-700">Razón Social *</label>
            <input
              id="razon_social" required type="text"
              placeholder="Ej: TechCorp S.A." value={formData.razon_social}
              onChange={(e) => setFormData({ ...formData, razon_social: e.target.value })}
              disabled={loading}
              className="w-full px-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="nombre_fantasia" className="text-sm font-semibold text-slate-700">Nombre de Fantasía (Opcional)</label>
            <input
              id="nombre_fantasia" type="text"
              placeholder="Ej: TechCorp" value={formData.nombre_fantasia}
              onChange={(e) => setFormData({ ...formData, nombre_fantasia: e.target.value })}
              disabled={loading}
              className="w-full px-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
            />
          </div>

          {/* 🌟 FIX FASE 11: Selector de Condición Fiscal */}
          <div className="space-y-1">
            <label htmlFor="condicion_fiscal" className="text-sm font-semibold text-slate-700">Condición Fiscal AFIP *</label>
            <select
              id="condicion_fiscal" required
              value={formData.condicion_fiscal}
              onChange={(e) => setFormData({ ...formData, condicion_fiscal: e.target.value })}
              disabled={loading}
              className="w-full px-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 bg-white"
            >
              <option value="RESPONSABLE_INSCRIPTO">Responsable Inscripto</option>
              <option value="MONOTRIBUTO">Monotributo</option>
              <option value="EXENTO">Exento</option>
            </select>
            <p className="text-xs text-slate-500">Este dato es inmutable y determinará la letra de sus comprobantes E2E.</p>
          </div>

          <div className="pt-4 flex gap-3">
            <button
              type="button" onClick={onClose} disabled={loading}
              className="flex-1 px-4 py-2 text-sm font-semibold text-slate-600 bg-white border border-slate-200 rounded-md hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !isCuitValid || !formData.razon_social.trim()}
              className="flex-1 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-700 flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:bg-indigo-400"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Crear Empresa"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
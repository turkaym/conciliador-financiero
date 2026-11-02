import { useState } from 'react';
import { useReglasFiscales } from '../hooks/useReglasFiscales';
import type { ReglaImpuesto } from '../hooks/useReglasFiscales';
import { Card } from '@/components/ui/card';
import { Loader2, Plus, Edit2, ShieldAlert, Power, PowerOff } from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

export default function ConfiguracionFiscalABM() {
  const { reglas, isLoading, createRegla, updateRegla } = useReglasFiscales();
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    tipo_impuesto: 'RETENCION_IIBB',
    jurisdiccion: 'ARBA',
    codigo_regimen_afip: 217,
    alicuota_defecto: 0.0,
    monto_minimo_sujeto: 0.0,
    aplica_padron: true
  });

  const resetForm = () => {
    setFormData({ tipo_impuesto: 'RETENCION_IIBB', jurisdiccion: 'ARBA', codigo_regimen_afip: 217, alicuota_defecto: 0.0, monto_minimo_sujeto: 0.0, aplica_padron: true });
    setIsEditing(false);
    setEditingId(null);
  };

  const handleEditClick = (regla: ReglaImpuesto) => {
    setFormData({
      tipo_impuesto: regla.tipo_impuesto,
      jurisdiccion: regla.jurisdiccion,
      codigo_regimen_afip: regla.codigo_regimen_afip,
      alicuota_defecto: regla.alicuota_defecto,
      monto_minimo_sujeto: regla.monto_minimo_sujeto,
      aplica_padron: regla.aplica_padron
    });
    setEditingId(regla.id!);
    setIsEditing(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = isEditing
      ? await updateRegla(editingId!, formData)
      : await createRegla(formData);

    if (success) resetForm();
  };

  const toggleActiveStatus = async (id: number, currentStatus: boolean) => {
    await updateRegla(id, { is_active: !currentStatus });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

      {/* PANEL IZQUIERDO: FORMULARIO */}
      <Card className="p-4 shadow-sm border-slate-200">
        <h3 className="font-bold text-slate-800 border-b border-slate-100 pb-2 mb-4 flex items-center">
          <ShieldAlert className="w-4 h-4 mr-2 text-indigo-600" />
          {isEditing ? "Editar Regla Matriz" : "Nueva Regla de Retención"}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Impuesto</label>
              <select className="w-full h-9 rounded-md border border-slate-300 px-3 text-sm focus:ring-1 focus:ring-indigo-500"
                value={formData.tipo_impuesto} onChange={(e) => setFormData({...formData, tipo_impuesto: e.target.value})} disabled={isEditing}
              >
                <option value="RETENCION_IIBB">Retención IIBB</option>
                <option value="RETENCION_GANANCIAS">Retención Ganancias</option>
                <option value="RETENCION_IVA">Retención IVA</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Jurisdicción</label>
              <input type="text" className="w-full h-9 rounded-md border border-slate-300 px-3 text-sm uppercase focus:ring-1 focus:ring-indigo-500"
                value={formData.jurisdiccion} onChange={(e) => setFormData({...formData, jurisdiccion: e.target.value.toUpperCase()})} disabled={isEditing} placeholder="Ej: ARBA" required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 uppercase">Cód. Régimen AFIP (SIRE/SICORE)</label>
            <input type="number" className="w-full h-9 rounded-md border border-slate-300 px-3 text-sm focus:ring-1 focus:ring-indigo-500 font-mono"
              value={formData.codigo_regimen_afip} onChange={(e) => setFormData({...formData, codigo_regimen_afip: parseInt(e.target.value) || 0})} required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Alícuota Defecto (%)</label>
              <input type="number" step="0.01" className="w-full h-9 rounded-md border border-slate-300 px-3 text-sm focus:ring-1 focus:ring-indigo-500"
                value={formData.alicuota_defecto} onChange={(e) => setFormData({...formData, alicuota_defecto: parseFloat(e.target.value) || 0})} required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Mínimo Sujeto ($)</label>
              <input type="number" step="1" className="w-full h-9 rounded-md border border-slate-300 px-3 text-sm focus:ring-1 focus:ring-indigo-500"
                value={formData.monto_minimo_sujeto} onChange={(e) => setFormData({...formData, monto_minimo_sujeto: parseFloat(e.target.value) || 0})} required
              />
            </div>
          </div>

          <label className="flex items-center space-x-2 bg-slate-50 p-2 rounded-md border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors">
            <input type="checkbox" className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
              checked={formData.aplica_padron} onChange={(e) => setFormData({...formData, aplica_padron: e.target.checked})}
            />
            <span className="text-xs font-medium text-slate-700">Forzar escaneo contra Padrones de Riesgo Mensual (AGIP/ARBA)</span>
          </label>

          <div className="flex space-x-2 pt-2">
            {isEditing && (
              <button type="button" onClick={resetForm} className="flex-1 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-md text-sm font-bold">
                Cancelar
              </button>
            )}
            <button type="submit" className="flex-1 py-2 bg-indigo-600 text-white hover:bg-indigo-700 rounded-md text-sm font-bold flex items-center justify-center">
              {isEditing ? <Edit2 className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
              {isEditing ? "Guardar Cambios" : "Inyectar Regla"}
            </button>
          </div>
        </form>
      </Card>

      {/* PANEL DERECHO: MATRIZ ACTIVA */}
      <Card className="lg:col-span-2 shadow-sm border-slate-200 overflow-hidden flex flex-col">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
          <h3 className="font-bold text-slate-800 text-sm">Matriz de Retenciones Vigentes</h3>
        </div>

        <div className="flex-1 overflow-x-auto">
          {isLoading ? (
             <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>
          ) : reglas.length === 0 ? (
             <div className="p-8 text-center text-slate-500 text-sm italic">No hay reglas impositivas configuradas. El Sifón Fiscal está apagado.</div>
          ) : (
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-100/50 text-slate-500 uppercase text-[10px] font-bold">
                <tr>
                  <th className="px-4 py-2">Impuesto</th>
                  <th className="px-4 py-2">Régimen</th>
                  <th className="px-4 py-2 text-right">Alícuota Base</th>
                  <th className="px-4 py-2 text-right">Mínimo Exento</th>
                  <th className="px-4 py-2 text-center">Padrón</th>
                  <th className="px-4 py-2 text-right">Control</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {reglas.map((r) => (
                  <tr key={r.id} className={`${!r.is_active ? 'opacity-50 bg-slate-50' : 'hover:bg-slate-50'}`}>
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900">{r.tipo_impuesto.replace('RETENCION_', '')}</div>
                      <div className="text-xs text-slate-500">{r.jurisdiccion}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">AFIP {r.codigo_regimen_afip}</td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-800">{r.alicuota_defecto}%</td>
                    <td className="px-4 py-3 text-right text-slate-600">{formatCurrency(r.monto_minimo_sujeto)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.aplica_padron ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                        {r.aplica_padron ? 'SI' : 'NO'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button onClick={() => handleEditClick(r)} disabled={!r.is_active} className="p-1.5 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded">
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => toggleActiveStatus(r.id!, r.is_active)} className={`p-1.5 rounded ${r.is_active ? 'text-rose-600 bg-rose-50 hover:bg-rose-100' : 'text-emerald-600 bg-emerald-50 hover:bg-emerald-100'}`}>
                        {r.is_active ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
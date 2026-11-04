import { useState, useEffect, useCallback } from "react";
import api from "@/api/axios";
import { useAuthStore } from "@/store/useAuthStore";
import { Users, Search, Building2, Landmark, AlertTriangle, ShieldCheck, Edit, Plus, Loader2, X } from "lucide-react";
import { toast } from "react-toastify";

export default function ProveedoresPage() {
  const entidadActiva = useAuthStore((state: any) => state.entidadActiva);

  const [proveedores, setProveedores] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Estados para el Modal ABM
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // 🌟 FIX: Se agregó is_entidad_financiera al estado inicial
  const [formData, setFormData] = useState({
    cuit: "",
    razon_social: "",
    cbu: "",
    condicion_fiscal: "RESPONSABLE_INSCRIPTO",
    is_entidad_financiera: false
  });

  const fetchProveedores = useCallback(async () => {
    if (!entidadActiva?.id) return;
    setIsLoading(true);
    try {
      const { data } = await api.get('/v1/pagos/proveedores', { headers: { 'x-entity-id': entidadActiva.id }});
      setProveedores(data);
    } catch (error) {
      toast.error("Error al cargar el directorio de proveedores.");
    } finally {
      setIsLoading(false);
    }
  }, [entidadActiva?.id]);

  useEffect(() => {
    void fetchProveedores();
  }, [fetchProveedores]);

  const handleOpenModal = (prov: any = null) => {
    if (prov) {
      setEditingId(prov.id);
      setFormData({
        cuit: prov.cuit,
        razon_social: prov.razon_social,
        cbu: prov.cbu || "",
        condicion_fiscal: prov.condicion_fiscal || "RESPONSABLE_INSCRIPTO",
        is_entidad_financiera: prov.is_entidad_financiera || false
      });
    } else {
      setEditingId(null);
      setFormData({
        cuit: "",
        razon_social: "",
        cbu: "",
        condicion_fiscal: "RESPONSABLE_INSCRIPTO",
        is_entidad_financiera: false
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entidadActiva?.id) return;

    if (formData.cbu && formData.cbu.length !== 22) {
      return toast.warning("El CBU debe contener exactamente 22 dígitos numéricos.");
    }

    setIsSubmitting(true);
    try {
      const headers = { 'x-entity-id': entidadActiva.id };

      if (editingId) {
        // ACTUALIZAR (PATCH) - 🌟 FIX: Enviamos el nuevo flag
        await api.patch(`/v1/pagos/proveedores/${editingId}`, {
          razon_social: formData.razon_social,
          cbu: formData.cbu || null,
          condicion_fiscal: formData.condicion_fiscal,
          is_entidad_financiera: formData.is_entidad_financiera
        }, { headers });
        toast.success("Proveedor actualizado exitosamente.");
      } else {
        // CREAR (POST) - 🌟 FIX: Enviamos el nuevo flag
        await api.post('/v1/pagos/proveedores', {
          ...formData,
          cbu: formData.cbu || null,
          is_proveedor: true,
          is_entidad_financiera: formData.is_entidad_financiera
        }, { headers });
        toast.success("Proveedor dado de alta en el sistema.");
      }

      setIsModalOpen(false);
      fetchProveedores();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Fallo al guardar el proveedor.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const provsFiltrados = proveedores.filter(p => p.razon_social.toLowerCase().includes(search.toLowerCase()) || p.cuit.includes(search));
  const provsSinCbu = proveedores.filter(p => !p.cbu || p.cbu.length !== 22).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 p-4 md:p-8">

      {/* HEADER & METRICS */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Building2 className="h-6 w-6 text-indigo-600" /> Directorio de Proveedores (MDM)
          </h1>
          <p className="text-sm text-slate-500 font-medium">Gestión de datos maestros, condición fiscal y ruteo bancario.</p>
        </div>
        <button onClick={() => handleOpenModal()} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-sm flex items-center transition-colors">
          <Plus className="w-5 h-5 mr-2" /> Nuevo Proveedor
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex items-center justify-between border-l-4 border-l-indigo-500">
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase">Total Proveedores</p>
            <p className="text-2xl font-black text-slate-800">{proveedores.length}</p>
          </div>
          <Users className="w-8 h-8 text-indigo-100" />
        </div>
        <div className={`bg-white border p-4 rounded-xl shadow-sm flex items-center justify-between border-l-4 ${provsSinCbu > 0 ? 'border-l-rose-500 border-rose-200 bg-rose-50/30' : 'border-l-emerald-500 border-emerald-200 bg-emerald-50/30'}`}>
          <div>
            <p className={`text-xs font-bold uppercase ${provsSinCbu > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>Riesgo Bancario (Sin CBU)</p>
            <p className={`text-2xl font-black ${provsSinCbu > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>{provsSinCbu}</p>
          </div>
          {provsSinCbu > 0 ? <AlertTriangle className="w-8 h-8 text-rose-200" /> : <ShieldCheck className="w-8 h-8 text-emerald-200" />}
        </div>
      </div>

      {/* TABLE SECTION */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-100 bg-slate-50">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input type="text" placeholder="Buscar por Razón Social o CUIT..." className="w-full pl-9 pr-4 py-2 bg-white border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-white border-b border-slate-200 text-slate-500 uppercase text-[11px] font-black tracking-wider">
              <tr>
                <th className="px-6 py-4">Razón Social y CUIT</th>
                <th className="px-6 py-4">Condición Fiscal</th>
                <th className="px-6 py-4">Ruteo Bancario (CBU)</th>
                <th className="px-6 py-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={4} className="h-32 text-center"><Loader2 className="w-6 h-6 animate-spin text-indigo-500 mx-auto" /></td></tr>
              ) : provsFiltrados.length === 0 ? (
                <tr><td colSpan={4} className="h-32 text-center text-slate-500 font-medium">No se encontraron proveedores.</td></tr>
              ) : (
                provsFiltrados.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      {/* 🌟 FIX: Badge visual para identificar Entidades Financieras rápidamente */}
                      <div className="font-bold text-slate-800 text-base flex items-center gap-2">
                        {p.razon_social}
                        {p.is_entidad_financiera && (
                          <span className="bg-indigo-100 text-indigo-700 text-[9px] font-black uppercase px-2 py-0.5 rounded-full">
                            Pasarela
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">CUIT: {p.cuit}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-600 border border-slate-200">
                        {p.condicion_fiscal.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {p.cbu && p.cbu.length === 22 ? (
                        <div className="flex items-center text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded w-fit">
                          <Landmark className="w-3.5 h-3.5 mr-1.5" />
                          <span className="font-mono text-xs font-bold">{p.cbu}</span>
                        </div>
                      ) : (
                        <div className="flex items-center text-rose-700 bg-rose-50 border border-rose-200 px-2 py-1 rounded w-fit">
                          <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
                          <span className="text-xs font-bold">CBU Faltante (Bloquea Interbanking)</span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => handleOpenModal(p)} className="inline-flex items-center px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded border border-indigo-200 transition-colors">
                        <Edit className="w-3.5 h-3.5 mr-1" /> Editar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL ABM */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in" onClick={() => setIsModalOpen(false)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="bg-indigo-600 p-4 text-white flex justify-between items-center">
              <h3 className="font-bold text-lg flex items-center">
                <Building2 className="w-5 h-5 mr-2" /> {editingId ? "Editar Proveedor" : "Alta de Proveedor"}
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-indigo-100 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5 col-span-2 sm:col-span-1">
                  <label className="text-xs font-bold text-slate-500 uppercase">CUIT (11 dígitos) *</label>
                  <input required disabled={!!editingId} type="text" maxLength={11} className="w-full h-10 px-3 rounded-md border border-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none disabled:bg-slate-100 disabled:text-slate-500" value={formData.cuit} onChange={e => setFormData({...formData, cuit: e.target.value.replace(/\D/g, '')})} />
                </div>
                <div className="space-y-1.5 col-span-2 sm:col-span-1">
                  <label className="text-xs font-bold text-slate-500 uppercase">Condición Fiscal *</label>
                  <select required className="w-full h-10 px-3 rounded-md border border-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none bg-white" value={formData.condicion_fiscal} onChange={e => setFormData({...formData, condicion_fiscal: e.target.value})}>
                    <option value="RESPONSABLE_INSCRIPTO">Responsable Inscripto</option>
                    <option value="MONOTRIBUTO">Monotributo</option>
                    <option value="EXENTO">Exento</option>
                    <option value="CONSUMIDOR_FINAL">Consumidor Final</option>
                  </select>
                </div>
                <div className="space-y-1.5 col-span-2">
                  <label className="text-xs font-bold text-slate-500 uppercase">Razón Social *</label>
                  <input required type="text" className="w-full h-10 px-3 rounded-md border border-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none" value={formData.razon_social} onChange={e => setFormData({...formData, razon_social: e.target.value})} />
                </div>
                <div className="space-y-1.5 col-span-2">
                  <label className="text-xs font-bold text-slate-500 uppercase flex items-center justify-between">
                    <span>CBU (22 Dígitos) <span className="text-rose-500">* Requerido para pagos</span></span>
                    <span className="text-[10px] font-mono text-indigo-600">{formData.cbu.length}/22</span>
                  </label>
                  <input type="text" maxLength={22} placeholder="Dejar vacío solo si se pagará en efectivo" className={`w-full h-10 px-3 rounded-md border ${formData.cbu.length > 0 && formData.cbu.length < 22 ? 'border-rose-400 focus:ring-rose-500' : 'border-slate-300 focus:ring-indigo-500'} outline-none font-mono tracking-widest`} value={formData.cbu} onChange={e => setFormData({...formData, cbu: e.target.value.replace(/\D/g, '')})} />
                </div>

                {/* 🌟 FIX: Nuevo bloque para tipificar Pasarelas */}
                <div className="col-span-2 bg-slate-50 border border-slate-200 p-3 rounded-md flex items-center justify-between mt-2">
                  <div>
                    <label className="text-sm font-bold text-slate-700 cursor-pointer" htmlFor="toggle-financiera">Entidad Financiera (Pasarela)</label>
                    <p className="text-[11px] text-slate-500 mt-0.5">Activá esto si el proveedor es un procesador de pagos (ej: Mercado Pago).</p>
                  </div>
                  <input
                    id="toggle-financiera"
                    type="checkbox"
                    className="w-5 h-5 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
                    checked={formData.is_entidad_financiera}
                    onChange={e => setFormData({...formData, is_entidad_financiera: e.target.checked})}
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-100 mt-6">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 bg-slate-100 text-slate-700 rounded-md font-bold text-sm hover:bg-slate-200">Cancelar</button>
                <button type="submit" disabled={isSubmitting} className="px-6 py-2 bg-indigo-600 text-white rounded-md font-bold text-sm hover:bg-indigo-700 flex items-center">
                  {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                  Guardar Datos Maestros
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

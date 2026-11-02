import React, { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Link2, ShieldAlert } from "lucide-react";
import api from "@/api/axios";
import type { Comprobante } from "../types";

interface ContactoAgenda {
  id: number;
  cuit: string;
  razon_social: string;
  condicion_fiscal: string;
}

interface SeccionTerceroProps {
  formData: any;
  setFormData: React.Dispatch<React.SetStateAction<any>>;
  cuitError: string | null;
  isVenta: boolean;
  isRemito: boolean;
  isNotaCreditoODebito: boolean; // 🌟 NUEVO: Prop para activar modo NC/ND
  remitosPendientes: Comprobante[];
  facturasAsociables: Comprobante[]; // 🌟 NUEVO: Prop para recibir las facturas del Hook
  handleSelectRemito: (remitoId: string) => void;
  handleSelectFactura: (facturaId: string) => void; // 🌟 NUEVO: Prop para manejar la selección de factura
}

export function SeccionTercero({
  formData,
  setFormData,
  cuitError,
  isVenta,
  isRemito,
  isNotaCreditoODebito,
  remitosPendientes,
  facturasAsociables,
  handleSelectRemito,
  handleSelectFactura
}: SeccionTerceroProps) {

  const [agendaContactos, setAgendaContactos] = useState<ContactoAgenda[]>([]);
  const [sugerencias, setSugerencias] = useState<ContactoAgenda[]>([]);
  const [campoActivo, setCampoActivo] = useState<"cuit" | "razon_social" | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchAgenda = async () => {
      try {
        const res = await api.get('/v1/pagos/proveedores');
        if (isMounted) setAgendaContactos(res.data);
      } catch (error) {
        console.error("No se pudo cargar la base de contactos B2B", error);
      }
    };
    fetchAgenda();
    return () => { isMounted = false; };
  }, []);

  useEffect(() => {
    if (!campoActivo) {
      setSugerencias([]);
      return;
    }

    const cuitSeguro = formData.cuit_tercero || "";
    const razonSocialSegura = formData.razon_social_receptor || "";

    if (campoActivo === "cuit" && cuitSeguro.length >= 5) {
      const match = agendaContactos.filter(c => (c.cuit || "").includes(cuitSeguro));
      setSugerencias(match);
    } else if (campoActivo === "razon_social" && razonSocialSegura.length >= 3) {
      const search = razonSocialSegura.toLowerCase();
      const match = agendaContactos.filter(c =>
        (c.razon_social || "").toLowerCase().includes(search)
      );
      setSugerencias(match);
    } else {
      setSugerencias([]);
    }
  }, [formData.cuit_tercero, formData.razon_social_receptor, campoActivo, agendaContactos]);

  const handleSeleccionarContacto = (contacto: ContactoAgenda) => {
    setFormData((prev: any) => ({
      ...prev,
      cuit_tercero: contacto.cuit,
      razon_social_receptor: contacto.razon_social,
      condicion_fiscal_receptor: contacto.condicion_fiscal || "CONSUMIDOR_FINAL"
    }));
    setCampoActivo(null);
    setSugerencias([]);
  };

  return (
    <div className="space-y-3 p-4 bg-indigo-50/40 rounded-xl border border-indigo-100">
      <Label className="text-indigo-900 font-bold block mb-2">
        Datos del {isVenta ? "Cliente" : "Proveedor"} *
      </Label>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

        {/* INPUT CUIT CON AUTOCOMPLETADO */}
        <div className="space-y-1.5 relative">
          <Label className="text-[11px] text-slate-500 uppercase">CUIT (Sin Guiones)</Label>
          <Input
            type="text"
            required
            placeholder="Busca o ingresa nuevo..."
            value={formData.cuit_tercero}
            onChange={(e) => setFormData({...formData, cuit_tercero: e.target.value.replace(/\D/g, '')})}
            onFocus={() => setCampoActivo("cuit")}
            onBlur={() => setCampoActivo(null)}
            className={`bg-white h-10 font-mono font-medium ${cuitError ? 'border-red-400 focus:ring-red-500' : 'border-indigo-200 focus:ring-indigo-500'}`}
          />

          {/* Dropdown nativo CUIT */}
          {campoActivo === "cuit" && sugerencias.length > 0 && (
            <ul className="absolute z-50 w-full sm:w-[150%] bg-white border border-indigo-100 shadow-xl rounded-md mt-1 max-h-48 overflow-y-auto top-full left-0">
              {sugerencias.map(c => (
                <li
                  key={c.id}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSeleccionarContacto(c);
                  }}
                  className="px-3 py-2 text-sm hover:bg-indigo-50 cursor-pointer border-b border-slate-50 last:border-0 flex flex-col"
                >
                  <span className="font-bold text-slate-800">{c.cuit}</span>
                  <span className="text-xs text-slate-500 truncate">{c.razon_social}</span>
                </li>
              ))}
            </ul>
          )}

          {cuitError && (
            <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded flex items-start border border-red-200 animate-in fade-in">
              <ShieldAlert className="w-4 h-4 mr-1 flex-shrink-0" /> {cuitError}
            </div>
          )}
        </div>

        {/* INPUT RAZÓN SOCIAL CON AUTOCOMPLETADO */}
        <div className="space-y-1.5 relative">
          <Label className="text-[11px] text-slate-500 uppercase">Razón Social / Nombre</Label>
          <Input
            type="text"
            required
            placeholder="Busca o ingresa nuevo..."
            value={formData.razon_social_receptor || ""}
            onChange={(e) => setFormData({...formData, razon_social_receptor: e.target.value})}
            onFocus={() => setCampoActivo("razon_social")}
            onBlur={() => setCampoActivo(null)}
            className="bg-white h-10 border-indigo-200 focus:ring-indigo-500"
          />

          {/* Dropdown nativo RAZON SOCIAL */}
          {campoActivo === "razon_social" && sugerencias.length > 0 && (
            <ul className="absolute z-50 w-full sm:w-[150%] bg-white border border-indigo-100 shadow-xl rounded-md mt-1 max-h-48 overflow-y-auto top-full left-0">
              {sugerencias.map(c => (
                <li
                  key={c.id}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSeleccionarContacto(c);
                  }}
                  className="px-3 py-2 text-sm hover:bg-indigo-50 cursor-pointer border-b border-slate-50 last:border-0 flex flex-col"
                >
                  <span className="font-bold text-slate-800 truncate">{c.razon_social}</span>
                  <span className="text-xs font-mono text-indigo-600">{c.cuit}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className={`space-y-1.5 transition-opacity ${isRemito ? 'opacity-60 grayscale' : ''}`}>
          <Label className="text-[11px] text-slate-500 uppercase">Condición Fiscal</Label>
          <Select
            disabled={isRemito}
            value={isRemito ? "NO_CATEGORIZADO" : formData.condicion_fiscal_receptor}
            onValueChange={(val) => setFormData({...formData, condicion_fiscal_receptor: val})}
          >
            <SelectTrigger className={`bg-white h-10 ${isRemito ? 'opacity-50' : 'border-indigo-200'}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="CONSUMIDOR_FINAL">Consumidor Final</SelectItem>
              <SelectItem value="RESPONSABLE_INSCRIPTO">Responsable Inscripto</SelectItem>
              <SelectItem value="MONOTRIBUTO">Monotributo</SelectItem>
              <SelectItem value="EXENTO">Exento</SelectItem>
              <SelectItem value="NO_CATEGORIZADO">Desconocido (Logístico)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 🌟 BLOQUE 1: FACTURA (Muestra el selector de Remitos) */}
      {!isRemito && !isNotaCreditoODebito && (
        <div className="pt-4 border-t border-indigo-200/50 mt-4 space-y-2 animate-in fade-in">
          <Label className="text-[11px] text-indigo-800 uppercase font-bold flex items-center">
            <Link2 className="w-3 h-3 mr-1 shrink-0" /> Documento Origen (Remito a Facturar)
          </Label>
          <Select value={formData.comprobante_origen_id} onValueChange={handleSelectRemito}>
            <SelectTrigger className="bg-white h-10 border-indigo-200 w-full">
              <SelectValue placeholder="Seleccionar Remito..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none" className="text-slate-500 italic">No vincular ningún remito (Factura Directa)</SelectItem>
              {formData.cuit_tercero.replace(/\D/g, '').length < 11 && (
                <SelectItem value="waiting" disabled className="text-slate-400">Ingrese un CUIT de 11 dígitos para buscar remitos pendientes...</SelectItem>
              )}
              {formData.cuit_tercero.replace(/\D/g, '').length === 11 && remitosPendientes.length === 0 && (
                <SelectItem value="empty" disabled className="text-amber-600 bg-amber-50">Este CUIT no tiene remitos pendientes.</SelectItem>
              )}
              {remitosPendientes.map(r => (
                <SelectItem key={r.id} value={r.id.toString()} className="font-medium text-indigo-700">
                  [ Remito {String(r.punto_venta).padStart(4,'0')}-{String(r.numero).padStart(8,'0')} ] - Valorizado: ${r.importe_total}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* 🌟 BLOQUE 2: NOTA DE CRÉDITO/DÉBITO (Muestra el selector obligatorio de Facturas) */}
      {isNotaCreditoODebito && (
        <div className="pt-4 border-t border-rose-200/50 mt-4 space-y-2 animate-in fade-in">
          <Label className="text-[11px] text-rose-800 uppercase font-bold flex items-center">
            <ShieldAlert className="w-3 h-3 mr-1 shrink-0" /> Factura de Origen (Obligatorio)
          </Label>
          <Select value={formData.comprobante_origen_id} onValueChange={handleSelectFactura}>
            <SelectTrigger className={`bg-white h-10 w-full ${formData.comprobante_origen_id === 'none' ? 'border-rose-300 ring-1 ring-rose-100' : 'border-emerald-200 bg-emerald-50/30'}`}>
              <SelectValue placeholder="Seleccione la Factura a modificar..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none" className="text-rose-600 font-bold italic">-- Seleccione una Factura --</SelectItem>
              {formData.cuit_tercero.replace(/\D/g, '').length < 11 && (
                <SelectItem value="waiting" disabled className="text-slate-400">Ingrese un CUIT de 11 dígitos para buscar facturas...</SelectItem>
              )}
              {formData.cuit_tercero.replace(/\D/g, '').length === 11 && facturasAsociables.length === 0 && (
                <SelectItem value="empty" disabled className="text-amber-600 bg-amber-50">Este CUIT no tiene facturas previas.</SelectItem>
              )}
              {facturasAsociables.map(f => (
                <SelectItem key={f.id} value={f.id.toString()} className="font-medium text-indigo-700">
                  [ Factura {String(f.punto_venta).padStart(4,'0')}-{String(f.numero).padStart(8,'0')} ] - {f.fecha_emision.split('-').reverse().join('/')} - Total: ${f.importe_total}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}
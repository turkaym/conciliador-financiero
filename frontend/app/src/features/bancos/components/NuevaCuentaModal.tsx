import { Switch } from "@/components/ui/switch"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog"
import { Loader2, Plus, Landmark } from "lucide-react"
import type { CuentaBancariaCreate, TipoCuentaEnum, MonedaEnum, TipoCanalEnum } from "../types"

interface NuevaCuentaModalProps {
  isLoading: boolean;
  errorMsg: string | null;
  onSubmit: (cuenta: CuentaBancariaCreate) => Promise<boolean>;
  proveedores: {id: number, razon_social: string, cuit: string}[];
  onOpen: () => void;
}

export function NuevaCuentaModal({ isLoading, errorMsg, onSubmit, proveedores = [], onOpen }: NuevaCuentaModalProps) {
  const [isOpen, setIsOpen] = useState(false);

  const [formCuenta, setFormCuenta] = useState<{
    tipo_canal: TipoCanalEnum | null;
    banco: string;
    numero_cuenta: string;
    cbu: string;
    alias: string;
    tipo_cuenta: TipoCuentaEnum | null;
    moneda: MonedaEnum;
    saldo_actual: string;
    is_virtual_clearing: boolean;
    proveedor_clearing_id: string;
  }>({
    tipo_canal: null,
    banco: "",
    numero_cuenta: "",
    cbu: "",
    alias: "",
    tipo_cuenta: null,
    moneda: "ARS" as MonedaEnum,
    saldo_actual: "0",
    is_virtual_clearing: false,
    proveedor_clearing_id: ""
  });

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);

    if (open && onOpen) {
      onOpen();
    } else if (!open) {
      setFormCuenta({
        tipo_canal: null,
        banco: "",
        numero_cuenta: "",
        cbu: "",
        alias: "",
        tipo_cuenta: null,
        moneda: "ARS" as MonedaEnum,
        saldo_actual: "0",
        is_virtual_clearing: false,
        proveedor_clearing_id: ""
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formCuenta.tipo_canal || !formCuenta.banco || !formCuenta.tipo_cuenta) {
      return;
    }

    if (formCuenta.is_virtual_clearing && !formCuenta.proveedor_clearing_id) {
      alert("Debés seleccionar la Entidad Financiera (Ej: Mercado Pago, Prisma) para el clearing virtual.");
      return;
    }

    const payload: CuentaBancariaCreate = {
      tipo_canal: formCuenta.tipo_canal,
      banco: formCuenta.banco,
      numero_cuenta: formCuenta.numero_cuenta,
      cbu: formCuenta.cbu.trim() === "" ? null : formCuenta.cbu,
      alias: formCuenta.alias.trim() === "" ? null : formCuenta.alias,
      tipo_cuenta: formCuenta.tipo_cuenta,
      moneda: formCuenta.moneda,
      saldo_actual: formCuenta.saldo_actual,
      is_virtual_clearing: formCuenta.is_virtual_clearing,
      proveedor_clearing_id: formCuenta.is_virtual_clearing ? parseInt(formCuenta.proveedor_clearing_id) : null
    };

    const success = await onSubmit(payload);
    if (success) {
      handleOpenChange(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white">
          <Plus className="h-4 w-4 mr-1" />
          Nueva Cuenta
        </Button>
      </DialogTrigger>

      {/* 🌟 FIX UX: Agregamos max-h y overflow-y-auto para evitar desborde */}
      <DialogContent
        className="sm:max-w-[500px] max-h-[85vh] overflow-y-auto"
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Landmark className="h-5 w-5 text-indigo-600" />
            <DialogTitle>Vincular Cuenta Bancaria</DialogTitle>
          </div>
        </DialogHeader>

        {errorMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4 mt-2">

          <div className="col-span-2 space-y-2">
            <Label>Naturaleza del Canal</Label>
            <Select required value={formCuenta.tipo_canal || ""} onValueChange={(v) => setFormCuenta(prev => ({
              ...prev,
              tipo_canal: v as TipoCanalEnum,
              is_virtual_clearing: v === "PASARELA",
              proveedor_clearing_id: v === "PASARELA" ? prev.proveedor_clearing_id : ""
            }))}>
              <SelectTrigger><SelectValue placeholder="¿Es un banco o una pasarela?" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="BANCO">Banco Tradicional (Santander, Galicia, etc.)</SelectItem>
                <SelectItem value="PASARELA">Pasarela de Pagos (Mercado Pago, Prisma, etc.)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="col-span-2 space-y-2">
            <Label>Nombre de la Entidad / Banco</Label>
            <Input
              required
              placeholder={formCuenta.tipo_canal === 'PASARELA' ? "Ej: Mercado Pago" : "Ej: Banco Santander"}
              value={formCuenta.banco}
              onChange={e => setFormCuenta({...formCuenta, banco: e.target.value.toUpperCase()})}
            />
          </div>

          <div className="space-y-2">
            <Label>Tipo de Cuenta</Label>
            <Select required value={formCuenta.tipo_cuenta || ""} onValueChange={(v) => setFormCuenta({...formCuenta, tipo_cuenta: v as TipoCuentaEnum})}>
              <SelectTrigger><SelectValue placeholder="Tipo" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="CC_ARS">Cuenta Corriente (ARS)</SelectItem>
                <SelectItem value="CA_ARS">Caja de Ahorro (ARS)</SelectItem>
                <SelectItem value="CC_USD">Cuenta Corriente (USD)</SelectItem>
                <SelectItem value="CA_USD">Caja de Ahorro (USD)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Moneda</Label>
            <Select required value={formCuenta.moneda} onValueChange={(v) => setFormCuenta({...formCuenta, moneda: v as MonedaEnum})}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ARS">Pesos (ARS)</SelectItem>
                <SelectItem value="USD">Dólares (USD)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Número de Cuenta</Label>
            <Input
              required
              placeholder="Ej: 123-45678/9"
              value={formCuenta.numero_cuenta}
              onChange={e => setFormCuenta({...formCuenta, numero_cuenta: e.target.value})}
            />
          </div>

          <div className="space-y-2">
            <Label>Alias (Opcional)</Label>
            <Input
              placeholder="Ej: mi.cuenta.banco"
              value={formCuenta.alias}
              onChange={e => setFormCuenta({...formCuenta, alias: e.target.value})}
            />
          </div>

          <div className="col-span-2 space-y-2">
            <Label>CBU / CVU / Identificador (22 dígitos)</Label>
            <Input
              maxLength={22}
              placeholder="007000..."
              value={formCuenta.cbu}
              onChange={e => setFormCuenta({...formCuenta, cbu: e.target.value})}
            />
          </div>

          <div className="col-span-2 space-y-2">
            <Label className="text-indigo-700 font-semibold">Saldo Inicial de Apertura</Label>
            <Input
              type="number"
              step="0.01"
              className="border-indigo-200 focus:border-indigo-500"
              required
              value={formCuenta.saldo_actual}
              onChange={e => setFormCuenta({...formCuenta, saldo_actual: e.target.value})}
            />
            <p className="text-[11px] text-muted-foreground">
              Se generará un movimiento automático de ajuste por este monto.
            </p>
          </div>

          {formCuenta.tipo_canal === "PASARELA" && (
            <div className="col-span-2 space-y-4 p-4 border border-indigo-100 bg-indigo-50/50 rounded-lg animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-indigo-900 font-semibold text-base">Motor de Auto-Emisión Fiscal</Label>
                  <p className="text-[12px] text-indigo-700/80 mt-1">
                    Obligatorio para pasarelas. Genera la factura automáticamente por las comisiones descontadas en el extracto.
                  </p>
                </div>
                <Switch
                  checked={formCuenta.is_virtual_clearing}
                  disabled={true}
                />
              </div>

              <div className="space-y-2">
                <Label>Vincular con Entidad Financiera (AFIP)</Label>
                <Select required value={formCuenta.proveedor_clearing_id} onValueChange={(v) => setFormCuenta({...formCuenta, proveedor_clearing_id: v})}>
                  <SelectTrigger className="bg-white border-indigo-200">
                    <SelectValue placeholder="Seleccioná la entidad para facturar..." />
                  </SelectTrigger>
                  <SelectContent>
                    {proveedores.length === 0 ? (
                      <div className="p-2 text-sm text-gray-500">No hay entidades financieras cargadas en Contactos.</div>
                    ) : (
                      proveedores.map(p => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.razon_social} <span className="text-xs text-muted-foreground ml-2">(CUIT: {p.cuit})</span>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <Button type="submit" className="col-span-2 w-full bg-slate-900 mt-2 mb-2" disabled={isLoading || !formCuenta.tipo_canal || !formCuenta.banco || !formCuenta.tipo_cuenta}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {isLoading ? "Vinculando..." : "Vincular Cuenta"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

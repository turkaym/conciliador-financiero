import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog"
import { Plus, Loader2, AlertCircle, BookOpenCheck } from "lucide-react"
import { usePlanCuentas } from "@/hooks/usePlanCuentas" // 🌟 FIX FASE A: Inyección del plan de cuentas
import type { MovimientoBancarioCreate } from "../types"

interface NuevoMovimientoModalProps {
  cuentaId: string;
  isLoading: boolean;
  errorMsg: string | null;
  onSubmit: (movimiento: MovimientoBancarioCreate) => Promise<boolean>;
  onClearError?: () => void;
}

export function NuevoMovimientoModal({
  cuentaId,
  isLoading,
  errorMsg,
  onSubmit,
  onClearError
}: NuevoMovimientoModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { cuentasImputables, fetchCuentasImputables, isLoadingCuentas } = usePlanCuentas();

  const [form, setForm] = useState({
    fecha: new Date().toISOString().split('T')[0],
    concepto: "",
    monto: "",
    tipo: "ingreso",
    cuenta_contable_id: "" // 🌟 FIX FASE A: Estado obligatorio para imputación
  });

  // Carga proactiva al abrir el modal
  useEffect(() => {
    if (isOpen && cuentasImputables.length === 0) {
      fetchCuentasImputables();
    }
  }, [isOpen, fetchCuentasImputables, cuentasImputables.length]);

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (!open) {
      setForm(prev => ({ ...prev, concepto: "", monto: "", cuenta_contable_id: "" }));
      if (onClearError) onClearError();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    let montoFinal = form.monto;
    if (form.tipo === "egreso") {
      montoFinal = form.monto.startsWith("-") ? form.monto : `-${form.monto}`;
    } else {
      montoFinal = form.monto.replace("-", "");
    }

    // 🌟 FIX FASE A: Mapeo exacto según el esquema de Ingesta Estricta del backend
    const payload = {
      cuenta_id: parseInt(cuentaId, 10),
      cuenta_contable_id: parseInt(form.cuenta_contable_id, 10),
      fecha: form.fecha,
      concepto_bancario_crudo: form.concepto,
      concepto_interno: null,
      monto: parseFloat(montoFinal),
      referencia_banco: ""
    };

    const success = await onSubmit(payload);
    if (success) {
      handleOpenChange(false);
    }
  };

  const isSubmitDisabled = isLoading || isLoadingCuentas || !form.cuenta_contable_id || !form.monto || !form.concepto;

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-slate-900 hover:bg-slate-800" disabled={!cuentaId}>
          <Plus className="mr-2 h-4 w-4" /> Cargar Movimiento
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>Registrar Movimiento</DialogTitle>
          <DialogDescription>Añadí un ingreso o egreso manual a la cuenta.</DialogDescription>
        </DialogHeader>

        {errorMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md flex items-start text-sm">
            <AlertCircle className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Tipo de Movimiento</Label>
              <Select value={form.tipo} onValueChange={(val) => setForm({...form, tipo: val})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ingreso">Cobro / Ingreso</SelectItem>
                  <SelectItem value="egreso">Pago / Egreso</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Fecha</Label>
              <Input type="date" required value={form.fecha} onChange={e => setForm({...form, fecha: e.target.value})} />
            </div>
          </div>

          {/* 🌟 FIX FASE A: Selector obligatorio de imputación contable */}
          <div className="space-y-2 bg-slate-50 p-3 rounded-lg border border-slate-200">
            <Label className="text-xs uppercase font-bold text-slate-700 flex items-center">
              <BookOpenCheck className="w-4 h-4 mr-1 text-indigo-600" /> Imputación Contable *
            </Label>
            <Select value={form.cuenta_contable_id} onValueChange={(val) => setForm({...form, cuenta_contable_id: val})}>
              <SelectTrigger className="bg-white">
                <SelectValue placeholder={isLoadingCuentas ? "Cargando rubros..." : "Seleccioná una cuenta contable..."} />
              </SelectTrigger>
              <SelectContent>
                {cuentasImputables.map(cta => (
                  <SelectItem key={cta.id} value={cta.id.toString()}>
                    <span className="text-slate-400 mr-2 text-xs font-mono">{cta.codigo}</span>
                    {cta.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Concepto (Descripción del banco)</Label>
            <Input required placeholder="TRF BANCARIA CBU..." value={form.concepto} onChange={e => setForm({...form, concepto: e.target.value})} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-500">Referencia / N° Transacción</Label>
              <Input
                disabled
                placeholder="Auto-generado"
                className="bg-slate-100 border-slate-200 text-slate-500 cursor-not-allowed focus-visible:ring-0"
                value=""
                readOnly
              />
            </div>
            <div className="space-y-2">
              <Label>Monto</Label>
              <Input type="number" step="0.01" min="0.01" required placeholder="5000.00" value={form.monto} onChange={e => setForm({...form, monto: e.target.value})} />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitDisabled}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {isLoading ? 'Registrando...' : 'Registrar Movimiento'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

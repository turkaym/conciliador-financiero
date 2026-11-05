import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { AlertTriangle } from "lucide-react"
import type { Comprobante } from "../types"

interface DeleteConfirmModalProps {
  comprobante: Comprobante | null;
  onClose: () => void;
  onConfirm: () => void;
}

export function DeleteConfirmModal({
  comprobante,
  onClose,
  onConfirm
}: DeleteConfirmModalProps) {

  const formatNumeroCbte = (pv: number, num: number) => {
    return `${pv.toString().padStart(4, '0')}-${num.toString().padStart(8, '0')}`;
  };

  return (
    <Dialog open={!!comprobante} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center text-red-600">
            <AlertTriangle className="mr-2 h-5 w-5" /> Confirmar Eliminación
          </DialogTitle>
          <DialogDescription className="pt-2">
            ¿Estás seguro que querés eliminar el comprobante <strong>{comprobante ? formatNumeroCbte(comprobante.punto_venta, comprobante.numero) : ''}</strong>?
            <br/><br/>
            Esta acción no se puede deshacer. Si este comprobante estaba vinculado a un Remito, el Remito volverá a estar disponible.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button variant="destructive" onClick={onConfirm}>Sí, eliminar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
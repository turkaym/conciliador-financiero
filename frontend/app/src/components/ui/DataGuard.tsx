import { useAuthStore } from '@/store/useAuthStore';
import { Lock, CreditCard, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ReactNode } from 'react';

interface DataGuardProps {
  children: ReactNode;
  isLoading?: boolean;
}

export default function DataGuard({ children, isLoading = false }: DataGuardProps) {
  const { isDataLocked } = useAuthStore();

  return (
    <div className="relative w-full h-full" aria-busy={isLoading}>
      {/* 🌟 El contenido real (Libro Mayor, Bancos, etc.) */}
      <div className={isDataLocked || isLoading ? "pointer-events-none select-none" : ""}>
        {children}
      </div>

      {isLoading && (
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-white/60 backdrop-blur-[1px] rounded-xl">
          <Loader2 className="h-7 w-7 animate-spin text-indigo-600" />
        </div>
      )}

      {/* 🌟 El Muro de Vidrio (Backdrop Blur) */}
      {isDataLocked && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/40 backdrop-blur-[3px] rounded-xl animate-in fade-in duration-500">
          <div className="flex flex-col items-center p-8 text-center bg-white/90 border shadow-2xl rounded-2xl border-slate-200 max-w-sm">
            <div className="p-4 mb-4 bg-red-50 text-red-500 rounded-full shadow-inner">
              <Lock className="w-8 h-8" />
            </div>
            <h3 className="mb-2 text-xl font-bold text-slate-800 tracking-tight">Acceso Suspendido</h3>
            <p className="mb-6 text-sm text-slate-500 leading-relaxed">
              El período de tu plan actual ha finalizado o presenta un pago pendiente.
              Tus datos están seguros, pero la operatividad está pausada.
            </p>
            <Button
              onClick={() => window.location.href = '/billing'}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-md flex gap-2 h-11"
            >
              <CreditCard className="w-5 h-5" />
              Regularizar Suscripción
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

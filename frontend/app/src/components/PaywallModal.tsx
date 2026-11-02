import { useAuthStore } from "@/store/useAuthStore";
import { Rocket, ShieldCheck, Zap, X, Building2 } from "lucide-react";
import { useEffect } from "react";

export default function PaywallModal() {
  const { isPaywallOpen, closePaywall, features } = useAuthStore();

  // Bloqueamos el scroll del body cuando el modal está abierto para evitar efecto rebote en mobile
  useEffect(() => {
    if (isPaywallOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isPaywallOpen]);

  if (!isPaywallOpen) return null;

  const currentPlan = features?.plan?.toUpperCase() || "STARTER";

  return (
    <div className="fixed inset-0 z-[100] flex sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">

      {/* 🌟 FIX MOBILE FIRST: h-[100dvh] garantiza que la barra de Safari no oculte los botones.
          En mobile ocupa el 100% de la pantalla, en desktop se adapta al contenido (h-auto) y se redondea. */}
      <div className="relative w-full h-[100dvh] sm:h-auto sm:max-w-lg flex flex-col bg-white sm:rounded-2xl shadow-2xl animate-in slide-in-from-bottom-full sm:zoom-in-95 duration-300">

        {/* Header Decorativo (Fijo en mobile) */}
        <div className="bg-gradient-to-br from-indigo-600 to-violet-700 px-6 py-8 sm:py-8 py-10 text-center shrink-0 rounded-b-3xl sm:rounded-none">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-white/20 backdrop-blur-md mb-4 shadow-inner">
            <Rocket className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">¡Tu negocio está creciendo!</h2>
          <p className="text-indigo-100 text-sm">
            Has alcanzado el límite máximo de entidades para tu plan actual ({currentPlan}).
          </p>
        </div>

        {/* Botón Cerrar */}
        <button
          onClick={closePaywall}
          className="absolute right-4 top-4 rounded-full bg-black/10 sm:bg-white/10 p-2 text-white hover:bg-black/20 sm:hover:bg-white/20 transition-colors z-10"
          aria-label="Cerrar modal"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Cuerpo del Modal (Scrollable en mobile si el contenido es muy largo) */}
        <div className="p-6 flex-1 overflow-y-auto flex flex-col">
          <h3 className="text-lg font-semibold text-slate-800 mb-4 text-center">
            Haz Upgrade a Plan Business y desbloquea:
          </h3>

          <div className="space-y-4 mb-8 flex-1">
            <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div className="p-3 bg-indigo-100 rounded-lg text-indigo-600 shrink-0">
                <Building2 className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-800">Hasta 3 Razones Sociales</p>
                <p className="text-xs text-slate-500">Opera múltiples empresas bajo una sola cuenta.</p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div className="p-3 bg-emerald-100 rounded-lg text-emerald-600 shrink-0">
                <Zap className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-800">10.000 Transacciones Mensuales</p>
                <p className="text-xs text-slate-500">Auto-matching avanzado y mayor ancho de banda.</p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div className="p-3 bg-blue-100 rounded-lg text-blue-600 shrink-0">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-800">Soporte Prioritario</p>
                <p className="text-xs text-slate-500">Atención técnica directa con nuestro equipo.</p>
              </div>
            </div>
          </div>

          {/* Botones de Acción (Siempre visibles al final del scroll) */}
          <div className="flex flex-col gap-3 shrink-0 pt-4 pb-safe">
            {/* min-h-[48px] garantiza el Touch Target ideal para pulgares en móviles */}
            <button
              onClick={() => window.location.href = "mailto:ventas@htsolutions.org?subject=Upgrade a Plan Business"}
              className="w-full min-h-[48px] rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 active:bg-indigo-700 transition-all flex items-center justify-center"
            >
              Contactar a Ventas para Upgrade
            </button>
            <button
              onClick={closePaywall}
              className="w-full min-h-[48px] rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-700 border border-slate-300 hover:bg-slate-50 active:bg-slate-100 transition-all flex items-center justify-center"
            >
              Quizás más tarde
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
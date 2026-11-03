import { useEffect, useState } from "react"
import api from "@/api/axios"
import { useAuthStore } from "@/store/useAuthStore"
import { Button } from "@/components/ui/button"
import { FeatureGuard } from "@/components/FeatureGuard"
import EntitySelector from "@/components/EntitySelector"
import NotificationBell from "@/components/NotificationBell"

// 🌟 FIX UX: Agregamos el ícono Building2 para el Directorio
import { LogOut, LayoutDashboard, FileText, Landmark, Lock, Calculator, Loader2, Users, Menu, X, ClipboardList, AlertCircle, CreditCard, Wallet, Building2 } from "lucide-react"
import { Outlet, useNavigate, useLocation } from "react-router-dom"
import { AxiosError } from "axios"

interface EntidadBackend {
  id: number;
  is_active: boolean;
}

export default function DashboardPage() {
  const { logout, tenant_id, isDataLocked, subscription_status, user } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  const [isVerifying, setIsVerifying] = useState(true)
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [isRedirectingToBilling, setIsRedirectingToBilling] = useState(false)

  const isAdmin = ["admin", "dueño", "editor"].includes(user?.role?.toLowerCase() || "");
  const isActive = (path: string) => location.pathname === path

  const handleNavigation = (path: string) => {
    navigate(path)
    setIsMobileOpen(false)
  }

  const handleUpgradePlan = async () => {
    setIsRedirectingToBilling(true);
    try {
      const { data } = await api.post('/v1/billing/checkout', { plan_name: 'starter' });
      window.location.href = data.checkout_url;
    } catch (error) {
      console.error("Error al generar Checkout:", error);
      setIsRedirectingToBilling(false);
    }
  }

  const requiresAttention = isDataLocked || subscription_status === 'past_due' || subscription_status === 'canceled';

  useEffect(() => {
    let isMounted = true;

    const checkUserStatus = async () => {
      try {
        if (!tenant_id) {
          if (isMounted) {
            setIsVerifying(false);
            logout();
          }
          return;
        }
        await api.get<EntidadBackend[]>(`/v1/entidades/${tenant_id}`)
      } catch (err) {
        const error = err as AxiosError;
        if (import.meta.env.DEV) {
          console.warn("Dashboard Warming Error:", error.response?.status);
        }
      } finally {
        if (isMounted) {
          setIsVerifying(false)
        }
      }
    }

    checkUserStatus();
    return () => { isMounted = false };
  }, [tenant_id, logout])

  if (isVerifying) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin mb-4 text-indigo-600" />
          <p>Cargando espacio de trabajo...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex overflow-hidden">

      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/60 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl transition-transform duration-300 ease-in-out
        md:relative md:translate-x-0 shrink-0
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>

        <div className="p-5 border-b border-slate-800 flex justify-between items-center">
          <div className="w-full">
            <h2 className="text-2xl font-bold text-white tracking-tight mb-4 flex items-center gap-2">
              <div className="h-6 w-6 bg-indigo-500 rounded-sm"></div>
              Conciliador
            </h2>
            <EntitySelector />
          </div>
          <button className="md:hidden text-slate-400 hover:text-white" onClick={() => setIsMobileOpen(false)}>
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
          <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard')}>
            <LayoutDashboard className={`mr-3 h-5 w-5 ${isActive('/dashboard') ? 'text-indigo-400' : 'text-slate-500'}`} /> Dashboard
          </Button>

          <FeatureGuard feature="b2b_directory">
          <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/directorio') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/directorio')}>
            <Building2 className={`mr-3 h-5 w-5 ${isActive('/dashboard/directorio') ? 'text-indigo-400' : 'text-slate-500'}`} /> Directorio B2B
          </Button>
          </FeatureGuard>

          <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/comprobantes') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/comprobantes')}>
            <FileText className={`mr-3 h-5 w-5 ${isActive('/dashboard/comprobantes') ? 'text-indigo-400' : 'text-slate-500'}`} /> Comprobantes
          </Button>

          <FeatureGuard feature="expenses_payments">
          <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/bancos') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/bancos')}>
            <Landmark className={`mr-3 h-5 w-5 ${isActive('/dashboard/bancos') ? 'text-indigo-400' : 'text-slate-500'}`} /> Bancos
          </Button>
          </FeatureGuard>

          <FeatureGuard feature="expenses_payments">
          <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/egresos') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/egresos')}>
            <Wallet className={`mr-3 h-5 w-5 ${isActive('/dashboard/egresos') ? 'text-indigo-400' : 'text-slate-500'}`} /> Egresos y Pagos
          </Button>
          </FeatureGuard>

          <FeatureGuard feature="reconciliation">
          <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/conciliacion') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/conciliacion')}>
            <Calculator className={`mr-3 h-5 w-5 ${isActive('/dashboard/conciliacion') ? 'text-indigo-400' : 'text-slate-500'}`} /> Conciliación
          </Button>
          </FeatureGuard>

          {isAdmin && (
            <>
              <FeatureGuard feature="tax_registries">
              <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/padrones') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/padrones')}>
                <ClipboardList className={`mr-3 h-5 w-5 ${isActive('/dashboard/padrones') ? 'text-indigo-400' : 'text-slate-500'}`} /> Padrones Fiscales
              </Button>
              </FeatureGuard>

              <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/reportes') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/reportes')}>
                <Calculator className={`mr-3 h-5 w-5 ${isActive('/dashboard/reportes') ? 'text-indigo-400' : 'text-slate-500'}`} /> Reportes Contables
              </Button>

              <FeatureGuard feature="team">
              <Button variant="ghost" className={`w-full justify-start hover:text-white hover:bg-slate-800 transition-colors ${isActive('/dashboard/equipo') ? 'bg-slate-800 text-white font-semibold' : ''}`} onClick={() => handleNavigation('/dashboard/equipo')}>
                <Users className={`mr-3 h-5 w-5 ${isActive('/dashboard/equipo') ? 'text-indigo-400' : 'text-slate-500'}`} /> Mi Equipo
              </Button>
              </FeatureGuard>
            </>
          )}

        </nav>

        <div className="p-4 bg-slate-950/50 mt-auto border-t border-slate-800 shrink-0">
          <Button variant="ghost" className="w-full justify-start text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors" onClick={logout}>
            <LogOut className="mr-3 h-5 w-5" /> Cerrar Sesión
          </Button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col h-screen bg-slate-50/50 relative w-full overflow-hidden">

        <header className="h-16 w-full bg-white border-b border-slate-200 flex items-center justify-between md:justify-end px-4 md:px-6 shrink-0 z-[60] shadow-sm relative">

          <button
            onClick={() => setIsMobileOpen(true)}
            className="md:hidden p-2 -ml-2 text-slate-600 hover:text-slate-900 focus:outline-none"
          >
            <Menu className="h-6 w-6" />
          </button>

          <div className="flex items-center gap-4">

            {requiresAttention && (
              <button
                onClick={handleUpgradePlan}
                disabled={isRedirectingToBilling}
                className="group flex items-center gap-2 px-3 py-1.5 md:px-4 text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-300 rounded-full hover:bg-emerald-100 hover:border-emerald-400 hover:shadow-md transition-all duration-300 disabled:opacity-50"
              >
                {isRedirectingToBilling ? (
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-emerald-600 animate-pulse" />
                )}

                <span className="hidden sm:inline">Mantén tus números al día</span>

                <span className="flex items-center gap-1.5 px-2.5 py-0.5 text-white bg-emerald-600 group-hover:bg-emerald-700 rounded-full transition-colors">
                  Pagar <CreditCard className="w-3 h-3" />
                </span>
              </button>
            )}

            <NotificationBell />
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 md:p-8 relative">
          {isDataLocked && (
            <div className="absolute inset-0 z-50 flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-500">
              <div className="absolute inset-0 bg-slate-100/40 backdrop-blur-md"></div>

              <div className="relative bg-white/90 p-8 rounded-3xl shadow-2xl max-w-md border border-slate-200/50">
                <div className="mx-auto w-16 h-16 bg-rose-50 rounded-full flex items-center justify-center mb-5 shadow-inner">
                  <Lock className="w-8 h-8 text-rose-500" />
                </div>
                <h3 className="text-xl font-black text-slate-900 mb-2 tracking-tight">Acceso Restringido</h3>
                <p className="text-sm text-slate-500 mb-8 leading-relaxed">
                  Tu suscripción se encuentra inactiva o presenta un saldo pendiente. Regulariza tu situación para recuperar el acceso a tu información operativa.
                </p>
                <Button
                  onClick={handleUpgradePlan}
                  disabled={isRedirectingToBilling}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-full h-12 font-bold shadow-lg shadow-emerald-600/20 transition-all hover:scale-[1.02]"
                >
                  {isRedirectingToBilling ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : <CreditCard className="w-5 h-5 mr-2" />}
                  {isRedirectingToBilling ? "Conectando al portal..." : "Gestionar Pagos y Suscripción"}
                </Button>
              </div>
            </div>
          )}

          <div className={`transition-all duration-500 h-full ${isDataLocked ? "pointer-events-none select-none blur-sm opacity-40 grayscale-[0.5]" : ""}`}>
            <Outlet />
          </div>
        </div>

      </main>
    </div>
  )
}

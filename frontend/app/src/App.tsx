import { Suspense, lazy } from "react"
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from "react-router-dom"
import { Loader2 } from "lucide-react"

// 🌟 CARGA SÍNCRONA: Solo el Core crítico para que la app inicie en milisegundos
import LoginPage from "./pages/Login"
import DashboardPage from "./pages/Dashboard"
import OnboardingWizard from "./components/OnboardingWizard"

// 🌟 FIX CRÍTICO: Importamos el Modal de Gobernanza Global
import PaywallModal from "./components/PaywallModal"

// 🌟 FIX UX: Importamos el contenedor global de notificaciones
import { ToastContainer } from "react-toastify"

const JoinPage = lazy(() => import("./pages/Join"))
// 🌟 CARGA ASÍNCRONA (Lazy Loading): Vite dividirá estas pantallas en "chunks" separados
const ComprobantesPage = lazy(() => import("./pages/Comprobantes"))
const BancosPage = lazy(() => import("./pages/Bancos"))
const ReportesPage = lazy(() => import("./pages/Reportes"))
const EquipoPage = lazy(() => import("./pages/Equipo"))
const ConciliacionPage = lazy(() => import("./pages/Conciliacion"))
const PadronesPage = lazy(() => import("./pages/Padrones"))
const EgresosPage = lazy(() => import("./pages/Egresos"))

// 🌟 FIX ARQUITECTURA: Importamos el nuevo módulo MDM de Proveedores
const ProveedoresPage = lazy(() => import("./pages/Proveedores"))

import { useAuthStore } from "./store/useAuthStore"
import { useSessionManager } from "./hooks/useSessionManager"

// 1. GUARDIA DIRECCIONAL ENTERPRISE: Autenticación, Zero Trust y Empty State
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore((state) => state.token)
  const tenant_id = useAuthStore((state) => state.tenant_id)
  const user = useAuthStore((state) => state.user)
  const entidadActiva = useAuthStore((state) => state.entidadActiva)

  // A. Control de Autenticación Base
  if (!token || !tenant_id || !user) {
    return <Navigate to="/login" replace />
  }

  // B. Control Zero Trust: Cuenta verificada pero sin aprobación del Super Admin
  if (user.account_status === "PENDING_SUPERADMIN_APPROVAL") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 sm:p-6 lg:p-8">
        <div className="w-full max-w-md space-y-6 rounded-2xl border border-slate-100 bg-white p-6 shadow-xl shadow-slate-200/50 text-center animate-in fade-in zoom-in-95 duration-300">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 border border-amber-100 text-amber-600">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-6 w-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z" />
            </svg>
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Aprobación en Proceso</h2>
            <p className="text-sm text-slate-500 leading-relaxed">
              Tu correo electrónico fue verificado con éxito. Tu espacio de trabajo <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{tenant_id}</span> se encuentra esperando la validación comercial del Super Admin.
            </p>
          </div>
          <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 text-xs text-slate-400">
            Recibirás una notificación automática por correo una vez habilitada la operatoria.
          </div>
          <button
            onClick={() => useAuthStore.getState().logout()}
            className="w-full inline-flex justify-center items-center px-4 py-2 border border-slate-200 shadow-sm text-sm font-medium rounded-lg text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            Volver al Login
          </button>
        </div>
      </div>
    )
  }

  // C. Control de Empty State: Cuenta activa pero sin configuración fiscal inicial
  if (user.account_status === "ACTIVE" && !entidadActiva) {
    return (
      <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-xl mx-auto">
          <OnboardingWizard />
        </div>
      </div>
    )
  }

  // D. Flujo Verde Nominal
  return <>{children}</>
}

// 2. SPINNER DE TRANSICIÓN
const PageLoader = () => (
  <div className="flex h-[60vh] w-full items-center justify-center">
    <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
  </div>
)

// 3. WELCOME PANEL
const WelcomePanel = () => {
  const user = useAuthStore((state) => state.user)
  const tenant_id = useAuthStore((state) => state.tenant_id)
  const entidadActiva = useAuthStore((state) => state.entidadActiva)

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Bienvenido al Panel</h1>
        <p className="text-slate-500">Aquí verás el resumen de tu conciliación operativa.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="bg-indigo-50/50 border border-indigo-100/80 p-4 rounded-xl">
          <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Identidad</p>
          <p className="text-sm text-slate-700 font-medium mt-1">
            Operador: <span className="font-normal text-slate-600">{user?.email}</span>
          </p>
          <p className="text-sm text-slate-700 font-medium mt-1">
            Entorno ID: <span className="font-mono bg-indigo-100/80 px-1 py-0.5 rounded text-indigo-700 text-xs">{tenant_id}</span>
          </p>
        </div>

        <div className="bg-emerald-50/50 border border-emerald-100/80 p-4 rounded-xl">
          <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Entidad en Operación</p>
          <p className="text-sm text-slate-700 font-medium mt-1">
            Razón Social: <span className="font-normal text-slate-600">{entidadActiva?.razon_social}</span>
          </p>
          <p className="text-sm text-slate-700 font-medium mt-1">
            CUIT Fiscal: <span className="font-mono bg-emerald-100/80 px-1 py-0.5 rounded text-emerald-700 text-xs">{entidadActiva?.cuit}</span>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  useSessionManager()

  return (
    <>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/verify-otp" element={<OnboardingWizard />} />
          <Route path="/join" element={
            <Suspense fallback={<PageLoader />}>
              <JoinPage />
            </Suspense>
          } />

          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }>
            <Route element={
              <Suspense fallback={<PageLoader />}>
                <Outlet />
              </Suspense>
            }>
              <Route index element={<WelcomePanel />} />

              {/* 🌟 FIX ARQUITECTURA: Rutas inyectadas */}
              <Route path="directorio" element={<ProveedoresPage />} />
              <Route path="comprobantes" element={<ComprobantesPage />} />
              <Route path="bancos" element={<BancosPage />} />
              <Route path="conciliacion" element={<ConciliacionPage />} />
              <Route path="reportes" element={<ReportesPage />} />
              <Route path="equipo" element={<EquipoPage />} />
              <Route path="padrones" element={<PadronesPage />} />
              <Route path="egresos" element={<EgresosPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>

      <PaywallModal />

      <ToastContainer
        position="top-right"
        autoClose={4000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
        style={{ zIndex: 99999 }}
      />
    </>
  )
}
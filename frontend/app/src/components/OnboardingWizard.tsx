import { useState } from "react"
import api from "@/api/axios"
import { useAuthStore } from "@/store/useAuthStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, KeyRound, AlertCircle, CheckCircle2 } from "lucide-react"
import { useNavigate, useLocation } from "react-router-dom"
import { AxiosError } from "axios"

interface ApiErrorResponse {
  detail?: string;
}

export default function OnboardingWizard() {
  const [codigoActivacion, setCodigoActivacion] = useState("")
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const navigate = useNavigate()
  const location = useLocation()

  const email = location.state?.email || ""
  const password = location.state?.password || ""

  const setAuth = useAuthStore((state) => state.setAuth)

  const handleVerificacion = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email) {
      setErrorMsg("La sesión segura expiró. Por favor, volvé a la pantalla de Login.")
      return
    }

    setLoading(true)
    setErrorMsg(null)
    setSuccessMsg(null)

    // ========================================================
    // 1️⃣ FASE: VERIFICACIÓN DEL CÓDIGO (Seguridad)
    // ========================================================
    try {
      await api.post("/v1/auth/verify-otp", {
        email: email,
        otp_code: codigoActivacion
      })
    } catch (err) {
      const error = err as AxiosError<ApiErrorResponse>;
      setErrorMsg(error.response?.data?.detail || "El código ingresado es incorrecto o ha expirado.")
      setLoading(false)
      return // 🛑 Cortamos la ejecución si el código es malo
    }

    // ========================================================
    // 2️⃣ FASE: AUTO-LOGIN B2B (Acceso al Dashboard)
    // ========================================================
    setSuccessMsg("¡Código validado! Preparando tu entorno de trabajo...")

    try {
      if (!password) throw new Error("Falta contraseña en memoria");

      const formData = new URLSearchParams()
      formData.append("username", email)
      formData.append("password", password)

      const loginResponse = await api.post("/v1/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      })

      const { access_token, tenant_id, user, features } = loginResponse.data

      // 🌟 FIX CONDICIÓN DE CARRERA (FRONTEND):
      // Guardamos en el estado global...
      setAuth(access_token, tenant_id, user, features)

      // ... y esperamos a que el ciclo de renderizado termine antes de navegar
      setTimeout(() => {
        navigate("/dashboard", { replace: true })
      }, 500)

    } catch (err) {
      setSuccessMsg("¡Cuenta activada con éxito! Redirigiendo al Login de acceso...")
      setTimeout(() => {
         navigate("/login", { replace: true })
      }, 2500)
    } finally {
      // Dejamos el loading en true si fue exitoso para que no parpadee el botón
    }
  }

  const handleReenviarCodigo = async () => {
    if (!email) return;
    setLoading(true);
    setErrorMsg(null);
    try {
       await api.post("/v1/auth/request-otp", { email });
       setSuccessMsg("Código reenviado. Por favor, revisá tu consola/casilla.");
    } catch (err) {
       setErrorMsg("No se pudo reenviar el código en este momento.");
    } finally {
       setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-96 bg-indigo-600 rounded-b-[20%] transform -translate-y-20 z-0"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="mx-auto w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-lg mb-4">
          <KeyRound className="h-8 w-8 text-indigo-600" />
        </div>
        <h2 className="mt-2 text-center text-3xl font-extrabold text-white">
          Activá tu Cuenta
        </h2>
        <p className="mt-2 text-center text-sm text-indigo-100">
          Ingresá el código de 6 dígitos que enviamos a <strong>{email || 'tu correo'}</strong>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-slate-100">

          {errorMsg && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md flex items-start text-sm">
              <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-md flex items-start text-sm">
              <CheckCircle2 className="h-5 w-5 mr-2 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          <form className="space-y-6" onSubmit={handleVerificacion}>
            <div>
              <Label htmlFor="codigo" className="text-slate-700 font-semibold">Código de Seguridad</Label>
              <Input
                id="codigo"
                required
                maxLength={6}
                placeholder="000000"
                className="text-center text-2xl font-mono tracking-[0.5em] mt-2 h-14"
                value={codigoActivacion}
                onChange={e => setCodigoActivacion(e.target.value.replace(/\D/g, '').substring(0, 6))}
              />
            </div>

            <Button type="submit" className="w-full bg-slate-900 hover:bg-slate-800 text-white h-12 text-lg" disabled={loading || codigoActivacion.length < 6}>
              {loading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : 'Verificar y Entrar'}
            </Button>

            <div className="text-center mt-4">
              <button type="button" onClick={handleReenviarCodigo} disabled={loading} className="text-sm text-indigo-600 hover:text-indigo-500 font-medium bg-transparent border-none cursor-pointer">
                ¿No recibiste el código? Reenviar
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
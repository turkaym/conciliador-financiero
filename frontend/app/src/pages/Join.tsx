import { useState, useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { ShieldCheck, Loader2, AlertCircle } from "lucide-react"
import api from "../api/axios"

export default function JoinPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const [token, setToken] = useState<string | null>(null)
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // 1. Intercepción del Magic Link al montar el componente
  useEffect(() => {
    const urlToken = searchParams.get("token")
    if (urlToken) {
      setToken(urlToken)
    } else {
      setError("Enlace de invitación inválido o ausente. Verifica que hayas copiado la URL completa.")
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden.")
      return
    }

    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres para cumplir con las políticas de seguridad.")
      return
    }

    setIsLoading(true)
    try {
      // 2. Consumo del endpoint receptor que construimos en auth.py
      await api.post("/v1/auth/accept-invite", {
        token: token,
        password: password
      })

      setSuccess(true)
      // 3. Redirección táctica tras el éxito
      setTimeout(() => navigate("/login"), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Fallo al procesar la invitación. El enlace puede haber expirado.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!token && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="h-12 w-12 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
            <ShieldCheck className="h-8 w-8 text-white" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-slate-900 tracking-tight">
          Configura tu acceso
        </h2>
        <p className="mt-2 text-center text-sm text-slate-600">
          Has sido invitado a operar en Conciliador ERP.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-xl sm:px-10 border border-slate-100">
          {success ? (
            <div className="rounded-md bg-emerald-50 p-4 animate-in fade-in zoom-in duration-300">
              <div className="flex">
                <div className="flex-shrink-0">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-emerald-800">Acceso configurado</h3>
                  <div className="mt-2 text-sm text-emerald-700">
                    <p>Tu cuenta está lista. Redirigiendo al inicio de sesión...</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <form className="space-y-6" onSubmit={handleSubmit}>
              {error && (
                <div className="rounded-md bg-red-50 p-4 border border-red-100 animate-in shake">
                  <div className="flex">
                    <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">{error}</h3>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700">Nueva Contraseña</label>
                <div className="mt-1">
                  <input
                    type="password"
                    required
                    disabled={!token}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-lg shadow-sm placeholder-slate-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Confirmar Contraseña</label>
                <div className="mt-1">
                  <input
                    type="password"
                    required
                    disabled={!token}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-lg shadow-sm placeholder-slate-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading || !token}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Guardar y Entrar"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
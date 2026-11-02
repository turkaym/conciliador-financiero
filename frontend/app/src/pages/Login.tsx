import { useState } from "react"
import api from "@/api/axios"
import { useAuthStore } from "@/store/useAuthStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, AlertCircle, CheckCircle2, ShieldCheck, Building2, FileText } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { AxiosError } from "axios"

interface ApiErrorResponse {
  detail?: string | Array<{ msg: string; loc: string[] }>;
}

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  const [companyName, setCompanyName] = useState("")
  const [cuit, setCuit] = useState("")

  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setErrorMsg(null)
    setSuccessMsg(null)

    // 🌟 SANITIZACIÓN CRÍTICA: Eliminamos espacios accidentales del email y la contraseña
    const sanitizedEmail = username.trim().toLowerCase().replace(/\s/g, '');
    const sanitizedPassword = password.trim();

    if (isLogin) {
      // ================= FLUJO DE LOGIN =================
      try {
        const formData = new URLSearchParams()
        formData.append("username", sanitizedEmail)
        formData.append("password", sanitizedPassword) // Inyección sanitizada

        const response = await api.post("/v1/auth/login", formData, {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        })

        const { access_token, tenant_id, user, features } = response.data
        setAuth(access_token, tenant_id, user, features)
        navigate("/dashboard")

      } catch (err) {
        const error = err as AxiosError<ApiErrorResponse>;
        const status = error.response?.status;

        if (status === 422) {
          setErrorMsg("Formato de envío no reconocido.");
        } else if (status === 401) {
          setErrorMsg("Usuario o contraseña incorrectos.");
        } else if (status === 403) {
          // 🌟 FIX: Enviamos email Y password sanitizados en memoria al OTP
          setErrorMsg("Debes activar tu cuenta. Redirigiendo...");
          setTimeout(() => {
            navigate("/verify-otp", { state: { email: sanitizedEmail, password: sanitizedPassword } });
          }, 1500);
        } else if (status === 404) {
          setErrorMsg("El espacio de trabajo se encuentra inactivo.");
        } else {
          setErrorMsg(error.response?.data?.detail as string || "Error de conexión. Intente más tarde.");
        }
      } finally {
        setLoading(false)
      }

    } else {
      // ================= FLUJO DE REGISTRO =================
      try {
        await api.post("/v1/auth/register", {
          email: sanitizedEmail,
          password: sanitizedPassword, // Inyección sanitizada
          company_name: companyName.trim(),
          cuit: cuit.trim()
        })

        // 🌟 FIX: Enviamos email Y password sanitizados en memoria al OTP
        setSuccessMsg("¡Cuenta creada! Redirigiendo para activación...")
        setTimeout(() => {
          navigate("/verify-otp", { state: { email: sanitizedEmail, password: sanitizedPassword } });
        }, 1500);

      } catch (err) {
        const error = err as AxiosError<ApiErrorResponse>;
        const status = error.response?.status;
        const apiDetail = error.response?.data?.detail;

        if (status === 400 || status === 409) {
          setErrorMsg(typeof apiDetail === 'string' ? apiDetail : "Este correo o CUIT ya se encuentra registrado.")
        } else if (status === 422) {
          if (Array.isArray(apiDetail) && apiDetail.length > 0) {
            setErrorMsg(`Error en el campo: ${apiDetail[0].loc[apiDetail[0].loc.length - 1]} - ${apiDetail[0].msg}`)
          } else {
            setErrorMsg("Los datos ingresados no cumplen con el formato requerido.")
          }
        } else {
          setErrorMsg(typeof apiDetail === 'string' ? apiDetail : "Ocurrió un error al crear la cuenta.")
        }
      } finally {
        setLoading(false)
      }
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50 p-4">
      <div className="w-full max-w-md">

        <div className="mx-auto w-16 h-16 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg mb-6">
          <ShieldCheck className="h-10 w-10 text-white" />
        </div>

        <Card className="shadow-lg border-slate-200">
          <CardHeader className="space-y-1 text-center">
            <CardTitle className="text-2xl font-bold tracking-tight text-slate-900">
              {isLogin ? 'Bienvenido' : 'Crear Cuenta'}
            </CardTitle>
            <CardDescription>
              {isLogin
                ? <>Ingresá tus credenciales de <strong>htsolution.org</strong></>
                : 'Registrá tu empresa para acceder al panel'
              }
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="grid gap-4">

              {errorMsg && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md flex items-start text-sm animate-in fade-in slide-in-from-top-2">
                  <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {successMsg && (
                <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-md flex items-start text-sm animate-in fade-in slide-in-from-top-2">
                  <CheckCircle2 className="h-5 w-5 mr-2 flex-shrink-0" />
                  <span>{successMsg}</span>
                </div>
              )}

              {!isLogin && (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="companyName" className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-slate-500" />
                      Razón Social
                    </Label>
                    <Input
                      id="companyName"
                      type="text"
                      placeholder="Empresa S.A."
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      required={!isLogin}
                      className="bg-white"
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="cuit" className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-500" />
                      CUIT
                    </Label>
                    <Input
                      id="cuit"
                      type="text"
                      placeholder="30123456789"
                      value={cuit}
                      onChange={(e) => setCuit(e.target.value)}
                      required={!isLogin}
                      pattern="^\d{11}$"
                      title="Debe contener 11 dígitos sin guiones"
                      className="bg-white"
                    />
                  </div>
                </>
              )}

              <div className="grid gap-2">
                <Label htmlFor="username">Correo Electrónico</Label>
                <Input
                  id="username"
                  type="email"
                  autoComplete="username" // 🌟 FIX DOM: Resuelve la alerta del navegador
                  placeholder="admin@htsolution.org"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="bg-white"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="password">Contraseña</Label>
                <Input
                  id="password"
                  type="password"
                  // 🌟 FIX 360 (Gestores de Contraseñas): Diferenciamos login de registro
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="bg-white"
                />
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-4">
              <Button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-700 transition-all shadow-md active:scale-[0.98]"
                disabled={loading}
              >
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {loading ? "Procesando..." : (isLogin ? "Iniciar Sesión" : "Registrar Empresa")}
              </Button>

              <div className="text-center text-sm w-full border-t border-slate-100 pt-4">
                <button
                  type="button"
                  className="font-medium text-indigo-600 hover:text-indigo-500 transition-colors"
                  onClick={() => {
                    setIsLogin(!isLogin)
                    setErrorMsg(null)
                    setSuccessMsg(null)
                  }}
                >
                  {isLogin ? '¿No tenés cuenta? Registrá tu empresa' : '¿Ya tenés cuenta? Iniciá sesión'}
                </button>
              </div>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  )
}
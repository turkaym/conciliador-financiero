import { useCallback, useEffect, useState } from "react"
import api from "@/api/axios"
import { useAuthStore } from "@/store/useAuthStore"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Loader2, Calculator, ArrowRightLeft, BookOpen, AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react"

// --- INTERFACES ---
interface CuentaBalance {
  codigo: string
  nombre: string
  tipo: string
  sumas: { debe: number; haber: number }
  saldos: { deudor: number; acreedor: number }
}

interface BalanceResponse {
  tenant: string
  cuentas_activas: number
  totales: { sumas_debe: number; sumas_haber: number; balance_cuadrado: boolean }
  balance: CuentaBalance[]
}

interface MovimientoMayor {
  fecha: string
  asiento_id: number
  concepto: string
  debe: number
  haber: number
  saldo: number
}

interface MayorResponse {
  cuenta: { codigo: string; nombre: string; tipo: string; naturaleza: string }
  saldo_inicial_periodo: number
  saldo_actual: number
  movimientos: MovimientoMayor[]
}

export default function ReportesPage() {
  const { user, entidadActiva } = useAuthStore()

  // 🌟 FIX RBAC: Determinamos si el usuario tiene autoridad financiera
  const isAdmin = ["admin", "dueño", "editor"].includes(user?.role?.toLowerCase() || "");

  // --- ESTADOS ---
  const [balanceData, setBalanceData] = useState<BalanceResponse | null>(null)
  const [loadingBalance, setLoadingBalance] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [isLedgerOpen, setIsLedgerOpen] = useState(false)
  const [ledgerData, setLedgerData] = useState<MayorResponse | null>(null)
  const [loadingLedger, setLoadingLedger] = useState(false)

  // --- PETICIONES API ---
  const fetchTrialBalance = useCallback(async () => {
    setLoadingBalance(true)
    setError(null)
    try {
      const schema = user?.tenant_id || "tenant_001"
      const { data } = await api.get(`/v1/reports/trial-balance/${schema}`)
      setBalanceData(data)
    } catch (err: any) {
      console.error("Error cargando balance:", err)
      setError(err.response?.data?.detail || "No se pudo conectar con el servicio de reportes contables.")
    } finally {
      setLoadingBalance(false)
    }
  }, [user?.tenant_id])

  // --- EFECTOS ---
  useEffect(() => {
    // 🌟 FIX FAIL-FAST & RBAC: Solo disparamos si es Admin y la entidad ya cargó
    if (isAdmin && user?.tenant_id && entidadActiva?.id) {
      void fetchTrialBalance()
    }
  }, [entidadActiva?.id, fetchTrialBalance, isAdmin, user?.tenant_id])

  const fetchLedger = async (codigoCuenta: string) => {
    setIsLedgerOpen(true)
    setLoadingLedger(true)
    setLedgerData(null)
    try {
      const schema = user?.tenant_id || "tenant_001"
      const { data } = await api.get(`/v1/reports/ledger/${schema}?cuenta_codigo=${codigoCuenta}`)
      setLedgerData(data)
    } catch (err: any) {
      console.error("Error cargando libro mayor:", err)
    } finally {
      setLoadingLedger(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(amount)
  }

  // 🌟 ESCUDO VISUAL (UI State para Operadores)
  if (!isAdmin) {
    return (
      <div className="flex h-[80vh] items-center justify-center p-6 animate-in fade-in duration-500">
        <div className="max-w-md w-full bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center shadow-sm">
          <div className="mx-auto w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mb-6">
            <ShieldAlert className="w-8 h-8 text-slate-500" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight mb-2">Acceso Restringido</h2>
          <p className="text-slate-500 leading-relaxed text-sm">
            Tu nivel de acceso actual (<span className="font-bold text-slate-700">{user?.role}</span>) no cuenta con privilegios para auditar el Balance de Sumas y Saldos.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500 p-4 md:p-8">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Calculator className="h-6 w-6 text-indigo-600" /> Reportes Financieros
          </h1>
          <p className="text-sm text-slate-500 font-medium">Contabilidad automatizada por el Motor de Conciliación.</p>
        </div>
        <Button onClick={fetchTrialBalance} variant="outline" disabled={loadingBalance} className="shadow-sm w-full sm:w-auto">
          {loadingBalance ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRightLeft className="mr-2 h-4 w-4 text-slate-500" />}
          Recalcular Estados
        </Button>
      </div>

      {/* ERROR FEEDBACK */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg flex items-center text-sm shadow-sm">
          <AlertTriangle className="h-5 w-5 mr-3 text-red-500 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI WIDGETS */}
      {!loadingBalance && balanceData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="shadow-sm border-slate-200 overflow-hidden">
            <div className={`h-1 w-full ${balanceData.totales.balance_cuadrado ? 'bg-emerald-500' : 'bg-orange-500'}`} />
            <CardContent className="p-5 flex items-center gap-4">
              <div className={`p-3 rounded-xl ${balanceData.totales.balance_cuadrado ? 'bg-emerald-100 text-emerald-600' : 'bg-orange-100 text-orange-600'}`}>
                {balanceData.totales.balance_cuadrado ? <CheckCircle2 className="h-6 w-6" /> : <AlertTriangle className="h-6 w-6" />}
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Integridad Contable</p>
                <p className={`text-lg font-bold leading-tight ${balanceData.totales.balance_cuadrado ? 'text-emerald-700' : 'text-orange-700'}`}>
                  {balanceData.totales.balance_cuadrado ? 'BALANCE CUADRADO' : 'DESCUADRE DETECTADO'}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-200">
            <CardContent className="p-5">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Sumas Totales (Debe)</p>
              <p className="text-2xl font-bold text-slate-900 tracking-tight">{formatCurrency(balanceData.totales.sumas_debe)}</p>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-200">
            <CardContent className="p-5">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Sumas Totales (Haber)</p>
              <p className="text-2xl font-bold text-slate-900 tracking-tight">{formatCurrency(balanceData.totales.sumas_haber)}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TABLA: BALANCE DE SUMAS Y SALDOS */}
      <Card className="shadow-md border-slate-200 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100">
          <CardTitle className="text-lg font-bold text-slate-800">Balance de Sumas y Saldos</CardTitle>
          <CardDescription>Resumen consolidado del Plan de Cuentas para el ejercicio actual.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[800px]">
            <TableHeader>
              <TableRow className="bg-slate-100/50 hover:bg-slate-100/50">
                <TableHead className="w-24 font-bold text-slate-700">Código</TableHead>
                <TableHead className="font-bold text-slate-700">Cuenta Contable</TableHead>
                <TableHead className="text-right border-l border-slate-200 bg-slate-50 font-bold text-slate-600">Debe</TableHead>
                <TableHead className="text-right bg-slate-50 font-bold text-slate-600">Haber</TableHead>
                <TableHead className="text-right border-l border-slate-200 font-bold text-slate-800">S. Deudor</TableHead>
                <TableHead className="text-right pr-4 font-bold text-slate-800">S. Acreedor</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingBalance ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-48 text-center text-slate-500">
                    <Loader2 className="mx-auto h-8 w-8 animate-spin mb-4 text-indigo-500" />
                    <span className="font-medium">Consolidando registros contables...</span>
                  </TableCell>
                </TableRow>
              ) : balanceData?.balance.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-slate-500 italic">No se encontraron movimientos contables en el sistema.</TableCell>
                </TableRow>
              ) : (
                balanceData?.balance.map((cuenta) => (
                  <TableRow key={cuenta.codigo} className="hover:bg-indigo-50/30 transition-colors group">
                    <TableCell className="font-mono text-xs text-slate-400 font-bold">{cuenta.codigo}</TableCell>
                    <TableCell>
                      <div className="font-bold text-slate-700">{cuenta.nombre}</div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-tighter">{cuenta.tipo}</div>
                    </TableCell>
                    <TableCell className="text-right text-slate-600 border-l border-slate-100">{formatCurrency(cuenta.sumas.debe)}</TableCell>
                    <TableCell className="text-right text-slate-600">{formatCurrency(cuenta.sumas.haber)}</TableCell>
                    <TableCell className="text-right font-bold text-indigo-900 border-l border-slate-100 bg-slate-50/50">
                      {cuenta.saldos.deudor > 0 ? formatCurrency(cuenta.saldos.deudor) : '—'}
                    </TableCell>
                    <TableCell className="text-right font-bold text-indigo-900 pr-4 bg-slate-50/50">
                      {cuenta.saldos.acreedor > 0 ? formatCurrency(cuenta.saldos.acreedor) : '—'}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100 text-indigo-600 hover:bg-indigo-100 transition-all rounded-full" onClick={() => fetchLedger(cuenta.codigo)}>
                        <BookOpen className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* MODAL: LIBRO MAYOR (Audit Trail) */}
      <Dialog open={isLedgerOpen} onOpenChange={setIsLedgerOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col p-0 overflow-hidden border-none shadow-2xl">
          <DialogHeader className="p-4 sm:p-6 bg-indigo-600 text-white">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg hidden sm:block">
                <BookOpen className="h-6 w-6 text-white" />
              </div>
              <div>
                <DialogTitle className="text-xl sm:text-2xl font-bold">Libro Mayor Detallado</DialogTitle>
                <DialogDescription className="text-indigo-100 font-medium text-xs sm:text-sm">
                  {ledgerData ? `${ledgerData.cuenta.nombre} (${ledgerData.cuenta.codigo})` : "Obteniendo movimientos..."}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-white">
            <div className="overflow-x-auto">
              <Table className="min-w-[700px]">
                <TableHeader className="bg-slate-50 sticky top-0 z-10">
                  <TableRow>
                    <TableHead className="w-24 sm:w-32 font-bold uppercase text-[10px] sm:text-xs">Fecha</TableHead>
                    <TableHead className="font-bold uppercase text-[10px] sm:text-xs">Concepto / Glosa</TableHead>
                    <TableHead className="text-right w-24 sm:w-36 font-bold uppercase text-[10px] sm:text-xs text-slate-600">Debe</TableHead>
                    <TableHead className="text-right w-24 sm:w-36 font-bold uppercase text-[10px] sm:text-xs text-slate-600">Haber</TableHead>
                    <TableHead className="text-right w-32 sm:w-40 pr-4 font-bold uppercase text-[10px] sm:text-xs text-indigo-600">Saldo Acum.</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loadingLedger ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-48 text-center"><Loader2 className="mx-auto h-8 w-8 animate-spin text-indigo-500" /></TableCell>
                    </TableRow>
                  ) : (
                    <>
                      {/* Arrastre de Saldo */}
                      {ledgerData && (
                        <TableRow className="bg-slate-50/50">
                          <TableCell colSpan={4} className="text-right pr-4 font-bold text-slate-400 text-[10px] sm:text-xs uppercase tracking-widest">Saldo Inicial Arrastrado</TableCell>
                          <TableCell className="text-right pr-4 font-bold text-slate-500 tracking-tight text-xs sm:text-sm">{formatCurrency(ledgerData.saldo_inicial_periodo)}</TableCell>
                        </TableRow>
                      )}
                      {/* Cuerpo de Movimientos */}
                      {ledgerData?.movimientos.map((mov, idx) => (
                        <TableRow key={idx} className="hover:bg-slate-50/80 transition-colors border-b border-slate-100">
                          <TableCell className="text-slate-500 font-medium text-xs sm:text-sm">{mov.fecha}</TableCell>
                          <TableCell>
                            <div className="font-bold text-slate-800 leading-tight text-xs sm:text-sm">{mov.concepto}</div>
                            <div className="text-[9px] sm:text-[10px] text-indigo-500 font-bold uppercase mt-0.5">Asiento Ref: {mov.asiento_id}</div>
                          </TableCell>
                          <TableCell className="text-right text-slate-600 font-medium text-xs sm:text-sm">{mov.debe > 0 ? formatCurrency(mov.debe) : ''}</TableCell>
                          <TableCell className="text-right text-slate-600 font-medium text-xs sm:text-sm">{mov.haber > 0 ? formatCurrency(mov.haber) : ''}</TableCell>
                          <TableCell className={`text-right font-bold pr-4 tracking-tight text-xs sm:text-sm ${mov.saldo < 0 ? 'text-red-600' : 'text-slate-900'}`}>
                            {formatCurrency(mov.saldo)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
          <div className="p-4 bg-slate-50 border-t flex justify-end">
            <Button onClick={() => setIsLedgerOpen(false)} variant="secondary" className="font-bold w-full sm:w-auto">Cerrar Reporte</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

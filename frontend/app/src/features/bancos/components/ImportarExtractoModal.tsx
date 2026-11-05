import { useState, useRef, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { UploadCloud, FileSpreadsheet, AlertCircle, CheckCircle2, Loader2, X, AlertTriangle, ScanLine, BookOpenCheck } from "lucide-react"

import type { XRayResponse, XRayColumn } from "../hooks/useBancos"
import { usePlanCuentas } from "@/hooks/usePlanCuentas" // 🌟 FIX FASE A

interface ImportarExtractoModalProps {
  cuentaId: string
  isLoading: boolean
  errorMsg: string | null
  // 🌟 FIX FASE A: Modificamos las firmas para obligar el envío de la cuenta contable
  onSubmit: (cuentaId: string, cuentaContableId: number, parserCode: string, file: File) => Promise<boolean>
  onAnalyzeFormat: (file: File) => Promise<{ objectName: string, analysis: XRayResponse } | null>
  onConfirmDynamic: (cuentaId: string, cuentaContableId: number, objectName: string, parserCode: string, mapping: Record<string, number>) => Promise<boolean>
  isPolling: boolean
  progress?: number
  statusMsg?: string
  onClearError?: () => void
  onCancelProcess?: (cuentaId: string, taskId: string) => Promise<boolean>
}

const PARSERS_DISPONIBLES = [
  { id: "SANTANDER_CSV", label: "Santander (CSV)", hint: "Exportá el CSV directo desde Online Banking." },
  { id: "GALICIA_XLSX", label: "Banco Galicia (Excel)", hint: "Descargá el formato estándar .xlsx de movimientos." },
  { id: "MERCADO_PAGO_CSV", label: "Mercado Pago (CSV)", hint: "Reporte de Todas las Transacciones (Liquidación)." },
  { id: "MACRO_CSV", label: "Banco Macro (CSV)", hint: "Exportación de movimientos en formato CSV." },
  { id: "PRISMA_V1", label: "Prisma / Payway (Clearing Sintético)", hint: "Desempaqueta Ventas Brutas, Comisiones y Retenciones en tiempo real." },
  { id: "DYNAMIC_XRAY", label: "Formato Desconocido (X-Ray)", hint: "Auto-detección Inteligente. Ideal para nuevos bancos o ERPs." }
]

export function ImportarExtractoModal({
  cuentaId, isLoading, errorMsg, onSubmit, onAnalyzeFormat, onConfirmDynamic,
  isPolling, progress = 0, statusMsg, onClearError, onCancelProcess
}: ImportarExtractoModalProps) {
  const [open, setOpen] = useState(false)
  const [selectedParser, setSelectedParser] = useState<string>("")
  const [cuentaContableId, setCuentaContableId] = useState<string>("") // 🌟 FIX FASE A
  const [file, setFile] = useState<File | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [showConfirmCancel, setShowConfirmCancel] = useState(false)

  const [xrayData, setXrayData] = useState<XRayResponse | null>(null)
  const [tempObjectName, setTempObjectName] = useState<string>("")
  const [dynamicMapping, setDynamicMapping] = useState<Record<string, number>>({})

  const fileInputRef = useRef<HTMLInputElement>(null)

  // 🌟 FIX FASE A: Hook del plan de cuentas
  const { cuentasImputables, fetchCuentasImputables, isLoadingCuentas } = usePlanCuentas();

  useEffect(() => {
    if (open && cuentasImputables.length === 0) {
      fetchCuentasImputables();
    }
  }, [open, fetchCuentasImputables, cuentasImputables.length]);

  useEffect(() => {
    if (isPolling) {
        setOpen(true)
        setIsSubmitted(true)
    } else {
        setShowConfirmCancel(false)
    }
  }, [isPolling])

  useEffect(() => {
    if (isSubmitted && !isPolling && !isLoading && !errorMsg && !xrayData) {
        cerrarModalLimpiamente()
    }
  }, [isPolling, isLoading, errorMsg, isSubmitted, xrayData])

  const cerrarModalLimpiamente = () => {
    setOpen(false)
    setFile(null)
    setSelectedParser("")
    setCuentaContableId("")
    setIsSubmitted(false)
    setShowConfirmCancel(false)
    setXrayData(null)
    setTempObjectName("")
    setDynamicMapping({})
    if (onClearError) onClearError()
  }

  const executeForceCancel = async () => {
    if (onCancelProcess) {
      await onCancelProcess(cuentaId, "");
      setShowConfirmCancel(false);
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragActive(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) setFile(e.dataTransfer.files[0])
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) setFile(e.target.files[0])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedParser || !file || !cuentaContableId) return
    setIsSubmitted(true)

    if (selectedParser === "DYNAMIC_XRAY") {
        const result = await onAnalyzeFormat(file)
        if (result) {
            setTempObjectName(result.objectName)
            setXrayData(result.analysis)

            const cacheKey = `xray_map_${file.name}_${cuentaId}`
            const cachedMap = sessionStorage.getItem(cacheKey)

            if (cachedMap) {
                try { setDynamicMapping(JSON.parse(cachedMap)); }
                catch(e) { setDynamicMapping(result.analysis.inferred_mapping); }
            } else {
                setDynamicMapping(result.analysis.inferred_mapping)
            }
        } else {
            setIsSubmitted(false)
        }
    } else {
        const isEncolado = await onSubmit(cuentaId, parseInt(cuentaContableId, 10), selectedParser, file)
        if (!isEncolado) setIsSubmitted(false)
    }
  }

  const handleConfirmarXRay = async () => {
    if (dynamicMapping["fecha"] === undefined || dynamicMapping["monto"] === undefined) {
       alert("Error: Debes mapear al menos la Fecha y el Monto para continuar.");
       return;
    }

    if (file) {
      sessionStorage.setItem(`xray_map_${file.name}_${cuentaId}`, JSON.stringify(dynamicMapping));
    }

    const isEncolado = await onConfirmDynamic(cuentaId, parseInt(cuentaContableId, 10), tempObjectName, "DYNAMIC_XRAY", dynamicMapping);
    if (isEncolado) {
        setXrayData(null);
        if (file) sessionStorage.removeItem(`xray_map_${file.name}_${cuentaId}`);
    } else {
        setIsSubmitted(false);
    }
  }

  const openFileExplorer = () => {
    if (fileInputRef.current) fileInputRef.current.click()
  }

  const parserHint = PARSERS_DISPONIBLES.find(p => p.id === selectedParser)?.hint
  const isFormIncomplete = !selectedParser || !file || !cuentaContableId || isLoading || isPolling;

  // ==========================================
  // RENDER: PANTALLA X-RAY (UI MOBILE-FIRST)
  // ==========================================
  if (xrayData && !isPolling) {
    return (
      <Dialog open={open} onOpenChange={(newOpen) => { if (!isLoading && !newOpen) cerrarModalLimpiamente() }}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col p-0 overflow-hidden">
          <DialogHeader className="px-6 pt-6 pb-2">
            <DialogTitle className="flex items-center gap-2 text-xl text-indigo-700">
              <ScanLine className="h-5 w-5" /> Análisis X-Ray Completado
            </DialogTitle>
            <DialogDescription>
              Hemos escaneado el archivo. Validá la estructura antes de la inserción masiva.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto px-6 space-y-4">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-sm">
                <span className="font-bold text-slate-700">Comienzo de Datos:</span> Fila {xrayData.start_row}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {xrayData.columns.map((col: XRayColumn) => (
                <div key={col.index} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-indigo-300 transition-colors min-w-0">
                  <div className="flex justify-between items-center gap-2 mb-3">
                    <div className="flex-1 min-w-0">
                      <h4
                        className="font-bold text-slate-800 text-sm truncate"
                        title={col.header || `Columna ${col.index}`}
                      >
                        {col.header || `Columna ${col.index}`}
                      </h4>
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mt-0.5">Col #{col.index}</p>
                    </div>

                    <Select
                      value={Object.keys(dynamicMapping).find(k => dynamicMapping[k] === col.index) || "omitir"}
                      onValueChange={(val) => {
                          const newMap = { ...dynamicMapping };
                          Object.keys(newMap).forEach(k => { if (newMap[k] === col.index) delete newMap[k]; });
                          if (val !== "omitir") newMap[val] = col.index;
                          setDynamicMapping(newMap);
                      }}
                    >
                      <SelectTrigger className="h-8 text-xs w-[120px] shrink-0 font-bold border-indigo-200 bg-indigo-50 text-indigo-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="omitir" className="text-slate-400 italic">Omitir</SelectItem>
                        <SelectItem value="fecha">📅 Fecha</SelectItem>
                        <SelectItem value="monto">💲 Monto</SelectItem>
                        <SelectItem value="concepto">📝 Concepto</SelectItem>
                        <SelectItem value="referencia">🔑 Referencia</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="bg-slate-50 rounded-md p-2 space-y-1 border border-slate-100 min-w-0">
                    <p className="text-[10px] text-slate-400 font-bold mb-1">MUESTRA DE DATOS:</p>
                    {col.sample_values.map((val, idx) => (
                      <div key={idx} className="text-xs text-slate-600 truncate font-mono bg-white p-1 rounded border border-slate-100" title={val}>
                        {val || "- vacio -"}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="px-6 pb-6 pt-4 bg-white border-t mt-auto flex justify-end gap-3 shadow-[0_-10px_20px_-15px_rgba(0,0,0,0.1)]">
            <Button variant="outline" onClick={cerrarModalLimpiamente} disabled={isLoading}>Cancelar</Button>
            <Button onClick={handleConfirmarXRay} disabled={isLoading} className="gap-2">
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <><CheckCircle2 className="h-4 w-4" /> Confirmar Ingesta</>}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  // ==========================================
  // RENDER: PANTALLA PRINCIPAL DE CARGA
  // ==========================================
  return (
    <Dialog open={open} onOpenChange={(newOpen) => {
        if (!isLoading && !isPolling) {
            if (!newOpen) cerrarModalLimpiamente();
            else setOpen(true);
        }
    }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2 border-indigo-200 text-indigo-700 hover:bg-indigo-50 hover:text-indigo-800">
          <UploadCloud className="h-4 w-4" /> Importar
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <FileSpreadsheet className="h-5 w-5 text-indigo-600" /> Ingesta Masiva
          </DialogTitle>
          <DialogDescription>
            Subí tu extracto bancario. El sistema filtrará duplicados automáticamente.
          </DialogDescription>
        </DialogHeader>

        {errorMsg && (
          <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm font-medium flex items-center gap-2 border border-red-200">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="leading-tight">{errorMsg}</span>
          </div>
        )}

        {showConfirmCancel && (
          <div className="bg-amber-50 border border-amber-200 p-4 rounded-md mb-2 mt-2">
            <h4 className="font-bold text-amber-800 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5"/> ¿Detener ingesta en curso?
            </h4>
            <p className="text-sm text-amber-700 mt-2">
              Esta acción forzará la detención del worker y revertirá los cambios no guardados.
            </p>
            <div className="flex justify-end gap-3 mt-4">
              <Button variant="ghost" size="sm" onClick={() => setShowConfirmCancel(false)} className="text-amber-800 hover:bg-amber-100">
                Seguir procesando
              </Button>
              <Button variant="destructive" size="sm" onClick={executeForceCancel}>
                Sí, Abortar proceso
              </Button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6 pt-2">

          {/* 🌟 FIX FASE A: Selector obligatorio de imputación madre */}
          <div className="space-y-2 bg-indigo-50/50 p-3 rounded-lg border border-indigo-100">
            <Label className="text-xs uppercase font-bold text-indigo-900 flex items-center">
              <BookOpenCheck className="w-4 h-4 mr-1 text-indigo-600" /> Cuenta Contable Madre *
            </Label>
            <Select value={cuentaContableId} onValueChange={setCuentaContableId} disabled={isLoading || isPolling}>
              <SelectTrigger className="bg-white border-indigo-200">
                <SelectValue placeholder={isLoadingCuentas ? "Cargando rubros..." : "Seleccioná la cuenta del banco..."} />
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
            <p className="text-[10px] text-indigo-600/70 mt-1 pl-1">
              Todos los movimientos de este archivo ingresarán con este rubro por defecto.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="parser_select">Formato / Origen de Datos</Label>
            <Select value={selectedParser} onValueChange={setSelectedParser} disabled={isLoading || isPolling}>
              <SelectTrigger id="parser_select" className={selectedParser === "DYNAMIC_XRAY" ? "border-indigo-500 bg-indigo-50" : ""}>
                <SelectValue placeholder="Seleccioná el formato..." />
              </SelectTrigger>
              <SelectContent>
                {PARSERS_DISPONIBLES.map(p => (
                  <SelectItem key={p.id} value={p.id} className={p.id === "DYNAMIC_XRAY" ? "font-bold text-indigo-700 bg-indigo-50/50 mt-2" : ""}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {parserHint && <p className="text-xs text-slate-500 mt-1 pl-1">ℹ️ {parserHint}</p>}
          </div>

          <div className="space-y-2">
            <Label>Archivo</Label>
            <div
              className={`
                relative border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center transition-colors
                ${isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-slate-50 hover:bg-slate-100'}
                ${file ? 'border-emerald-500 bg-emerald-50' : ''}
                ${(isLoading || isPolling) ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
              `}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={openFileExplorer}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
                accept=".csv, .txt, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
              />

              {!file ? (
                <>
                  <div className="bg-white p-3 rounded-full shadow-sm mb-3">
                    <UploadCloud className={`h-6 w-6 ${isDragActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                  </div>
                  <p className="text-sm font-medium text-slate-700">Arrastrá o hacé clic para subir</p>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-8 w-8 text-emerald-500 mb-2" />
                  <p className="text-sm font-bold text-slate-800">{file.name}</p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 text-slate-400 hover:text-red-500 rounded-full h-8 w-8"
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    disabled={isLoading || isPolling}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </>
              )}
            </div>
          </div>

          {isPolling && (
            <div className="space-y-2 p-4 bg-indigo-50 rounded-md border border-indigo-100 animate-in fade-in slide-in-from-bottom-4">
              <div className="flex justify-between text-sm font-medium text-indigo-800">
                <span className="truncate mr-4">{statusMsg || 'Procesando archivo...'}</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-indigo-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              type="button"
              onClick={() => isPolling ? setShowConfirmCancel(true) : cerrarModalLimpiamente()}
              disabled={isLoading && !isPolling}
              className={isPolling ? "text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200" : ""}
            >
              {isPolling ? 'Detener' : 'Cancelar'}
            </Button>
            <Button type="submit" disabled={isFormIncomplete} className="min-w-[140px] gap-2">
              {(isLoading || isPolling) ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isPolling ? 'Encolado' : selectedParser === "DYNAMIC_XRAY" ? <><ScanLine className="h-4 w-4" /> Analizar</> : 'Procesar'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
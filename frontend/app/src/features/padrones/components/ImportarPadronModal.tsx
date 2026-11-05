import { useState, useRef, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { UploadCloud, FileText, AlertCircle, CheckCircle2, Loader2, X } from "lucide-react"

interface ImportarPadronModalProps {
  isLoading: boolean
  errorMsg: string | null
  onSubmit: (jurisdiccion: string, periodo: string, file: File) => Promise<boolean>
  isPolling: boolean
  onClearError?: () => void
}

const JURISDICCIONES = [
  { id: "ARBA", label: "ARBA (Buenos Aires)" },
  { id: "AGIP", label: "AGIP (CABA)" },
  { id: "API", label: "API (Santa Fe)" },
  { id: "RENTAS_CBA", label: "Rentas (Córdoba)" }
]

export function ImportarPadronModal({ isLoading, errorMsg, onSubmit, isPolling, onClearError }: ImportarPadronModalProps) {
  const [open, setOpen] = useState(false)
  const [jurisdiccion, setJurisdiccion] = useState<string>("")
  const [periodo, setPeriodo] = useState<string>("") // Formato YYYY-MM
  const [file, setFile] = useState<File | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-abrir si estamos escuchando eventos SSE tras un F5
  useEffect(() => {
    if (isPolling) {
        setOpen(true)
        setIsSubmitted(true)
    }
  }, [isPolling])

  // Limpieza y cierre automático al detectar éxito
  useEffect(() => {
    if (isSubmitted && !isPolling && !isLoading && !errorMsg) {
        cerrarModalLimpiamente();
    }
  }, [isPolling, isLoading, errorMsg, isSubmitted]);

  const cerrarModalLimpiamente = () => {
    setOpen(false);
    setFile(null);
    setJurisdiccion("");
    setPeriodo("");
    setIsSubmitted(false);
    if (onClearError) onClearError();
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
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!jurisdiccion || !periodo || !file) return

    setIsSubmitted(true)
    const isEncolado = await onSubmit(jurisdiccion, periodo, file)

    if (!isEncolado) {
        setIsSubmitted(false)
    }
  }

  const openFileExplorer = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }

  return (
    <Dialog open={open} onOpenChange={(newOpen) => {
        if (!isLoading && !isPolling) {
            if (!newOpen) {
                cerrarModalLimpiamente();
            } else {
                setOpen(true);
            }
        }
    }}>
      <DialogTrigger asChild>
        <Button className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white">
          <UploadCloud className="h-4 w-4" /> Subir Padrón
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <FileText className="h-5 w-5 text-indigo-600" /> Ingesta de Padrones de Recaudación
          </DialogTitle>
          <DialogDescription>
            Subí el archivo crudo (.txt o .csv) descargado del fisco. El procesamiento de 600MB se hará en chunks asíncronos.
          </DialogDescription>
        </DialogHeader>

        {errorMsg && (
          <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm font-medium flex items-center gap-2 border border-red-200">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="leading-tight">{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5 pt-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="jurisdiccion_select">Jurisdicción</Label>
              <Select value={jurisdiccion} onValueChange={setJurisdiccion} disabled={isLoading || isPolling}>
                <SelectTrigger id="jurisdiccion_select">
                  <SelectValue placeholder="Seleccionar..." />
                </SelectTrigger>
                <SelectContent>
                  {JURISDICCIONES.map(j => (
                    <SelectItem key={j.id} value={j.id}>{j.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="periodo">Período Fiscal</Label>
              <Input
                id="periodo"
                type="month"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                disabled={isLoading || isPolling}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Archivo del Fisco (.txt, .csv)</Label>
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
                accept=".txt, .csv"
              />

              {!file ? (
                <>
                  <div className="bg-white p-3 rounded-full shadow-sm mb-3">
                    <UploadCloud className={`h-6 w-6 ${isDragActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                  </div>
                  <p className="text-sm font-medium text-slate-700">Arrastrá el padrón acá o hacé clic</p>
                  <p className="text-xs text-slate-500 mt-1">Límite por chunk: 600MB</p>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-8 w-8 text-emerald-500 mb-2" />
                  <p className="text-sm font-bold text-slate-800">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
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

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" type="button" onClick={cerrarModalLimpiamente} disabled={isLoading || isPolling}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!jurisdiccion || !periodo || !file || isLoading || isPolling} className="min-w-[150px]">
              {(isLoading || isPolling) ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Normalizando...</> : 'Ingestar Padrón'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
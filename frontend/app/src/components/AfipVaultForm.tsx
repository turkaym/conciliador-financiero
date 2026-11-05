import { useState, useRef } from "react";
import { UploadCloud, FileKey, ShieldCheck, Loader2, CheckCircle, Activity, RefreshCw, ServerCrash, Trash2, AlertTriangle, Clock } from "lucide-react";
import api from "@/api/axios";
import { useAuthStore } from "@/store/useAuthStore";
import { Button } from "@/components/ui/button";
import { toast } from "react-toastify";
import { extractApiError, getApiErrorDetail } from "@/lib/utils";

export default function AfipVaultForm() {
  const { entidadActiva, setEntidadActiva } = useAuthStore();

  const [certFile, setCertFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<{ type: 'idle' | 'success' | 'error', message: string }>({ type: 'idle', message: '' });

  const [isTesting, setIsTesting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [showConfirmRevoke, setShowConfirmRevoke] = useState(false);

  const [healthStatus, setHealthStatus] = useState<'idle' | 'ok' | 'fail'>('idle');
  const [healthMsg, setHealthMsg] = useState("");

  const certInputRef = useRef<HTMLInputElement>(null);
  const keyInputRef = useRef<HTMLInputElement>(null);

  const isConfigured = entidadActiva?.has_afip_credentials;
  const tenant_id = useAuthStore(state => state.tenant_id);

  const handleUpload = async () => {
    if (!certFile || !keyFile || !entidadActiva?.id || !tenant_id) return;

    setIsUploading(true);
    setStatus({ type: 'idle', message: '' });

    const formData = new FormData();
    formData.append("certificate", certFile);
    formData.append("private_key", keyFile);

    try {
      await api.post(`/v1/afip-vault/${tenant_id}/entidad/${entidadActiva.id}/upload-credentials`, formData);
      setStatus({ type: 'success', message: "Credenciales aseguradas exitosamente." });
      setEntidadActiva({ ...entidadActiva, has_afip_credentials: true });
    } catch (error: unknown) {
      const detail = getApiErrorDetail(error);
      let errorMsg = "Fallo en la comunicación con el servidor.";
      if (Array.isArray(detail) && detail.length > 0 && typeof detail[0] === "object" && detail[0] !== null &&
        "loc" in detail[0] && Array.isArray(detail[0].loc) && "msg" in detail[0] && typeof detail[0].msg === "string") {
        errorMsg = `Error de formato: ${detail[0].loc.join(' -> ')} - ${detail[0].msg}`;
      }
      else if (typeof detail === 'string') errorMsg = detail;
      setStatus({ type: 'error', message: errorMsg });
    } finally {
      setIsUploading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!tenant_id || !entidadActiva?.id) return;
    setIsTesting(true);
    setHealthStatus('idle');
    try {
      await api.get(`/v1/afip-vault/${tenant_id}/entidad/${entidadActiva.id}/test-connection`);
      setHealthStatus('ok');
      setHealthMsg("Conexión criptográfica establecida con éxito (WSAA OK).");
    } catch (error: unknown) {
      setHealthStatus('fail');
      setHealthMsg(extractApiError(error, "ARCA denegó el acceso o los servidores están caídos."));
    } finally {
      setIsTesting(false);
    }
  };

  const handleForceSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/v1/comprobantes/sync-afip', { punto_venta: 1, tipo_cbte: 1 });
      toast.success("Worker de Celery disparado en segundo plano. Los comprobantes aparecerán en breve.");
    } catch (error: unknown) {
      toast.error("Error al disparar el Worker: " + extractApiError(error, "Fallo de red"));
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRevoke = async () => {
    if (!tenant_id || !entidadActiva?.id) return;

    setIsRevoking(true);
    try {
      await api.delete(`/v1/afip-vault/${tenant_id}/entidad/${entidadActiva.id}/credentials`);
      setEntidadActiva({ ...entidadActiva, has_afip_credentials: false });
      setCertFile(null);
      setKeyFile(null);
      setShowConfirmRevoke(false);
      toast.success("Credenciales revocadas y destruidas de la bóveda.");
    } catch (error: unknown) {
      toast.error("Error al revocar credenciales: " + extractApiError(error, "Fallo de servidor"));
    } finally {
      setIsRevoking(false);
    }
  };

  if (isConfigured) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden animate-in fade-in duration-300">
        <div className="bg-slate-50 border-b border-slate-200 p-4 sm:p-6 flex items-center gap-3">
          <div className="p-2 bg-indigo-100 text-indigo-700 rounded-lg shrink-0">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Dashboard de Salud Fiscal</h2>
            <p className="text-sm text-slate-500">Monitor de conectividad con servidores AFIP/ARCA</p>
          </div>
        </div>

        <div className="p-4 sm:p-6 space-y-6">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5 p-5 rounded-lg border bg-emerald-50/50 border-emerald-100">

            <div className="flex items-start sm:items-center gap-3 w-full lg:w-auto flex-1">
              <CheckCircle className="w-8 h-8 text-emerald-600 shrink-0 mt-1 sm:mt-0" />
              <div className="flex-1 break-words space-y-1">
                <h3 className="font-bold text-emerald-900 leading-tight">Bóveda Criptográfica Activa</h3>
                <p className="text-xs text-emerald-700">CUIT: <span className="font-mono">{entidadActiva.cuit}</span></p>
                {entidadActiva.afip_cert_expiration && (
                  <p className="text-[10px] font-bold text-emerald-600 uppercase">
                    Vence: {new Date(entidadActiva.afip_cert_expiration).toLocaleDateString()}
                  </p>
                )}
                {/* 🌟 FIX TELEMETRÍA FASE E: Visualización de última sincronización */}
                {entidadActiva.afip_last_sync_at ? (
                  <p className="text-[10px] font-bold text-indigo-600 uppercase flex items-center gap-1 mt-1">
                    <Clock className="w-3 h-3 shrink-0" />
                    Sincronizado: {new Date(entidadActiva.afip_last_sync_at).toLocaleString()}
                  </p>
                ) : (
                  <p className="text-[10px] font-bold text-amber-600 uppercase flex items-center gap-1 mt-1">
                    <AlertTriangle className="w-3 h-3 shrink-0" /> Aún no sincronizado
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto shrink-0 mt-2 lg:mt-0">
              <Button onClick={handleTestConnection} disabled={isTesting || isRevoking} variant="outline" className="border-indigo-200 text-indigo-700 hover:bg-indigo-50 w-full sm:w-auto">
                {isTesting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Activity className="w-4 h-4 mr-2" />}
                {isTesting ? "Negociando..." : "Test de Conexión"}
              </Button>
              <Button onClick={handleForceSync} disabled={isSyncing || isRevoking} className="bg-slate-900 hover:bg-slate-800 text-white w-full sm:w-auto">
                {isSyncing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                Sincronizar
              </Button>
            </div>
          </div>

          {healthStatus === 'ok' && (
            <div className="bg-emerald-100 text-emerald-800 p-3 rounded-md text-sm font-medium flex items-center animate-in fade-in slide-in-from-top-2 border border-emerald-200">
              <CheckCircle className="w-5 h-5 mr-2 shrink-0" /> {healthMsg}
            </div>
          )}

          {healthStatus === 'fail' && (
            <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm font-medium flex items-center animate-in fade-in slide-in-from-top-2 border border-red-200">
              <ServerCrash className="w-5 h-5 mr-2 shrink-0" /> {healthMsg}
            </div>
          )}

          <div className="pt-4 mt-6 border-t border-slate-100 flex flex-col justify-end gap-3 sm:flex-row">
            {!showConfirmRevoke ? (
              <Button
                onClick={() => setShowConfirmRevoke(true)}
                disabled={isRevoking || isTesting || isSyncing}
                variant="ghost"
                className="text-red-600 hover:bg-red-50 hover:text-red-700 w-full sm:w-auto"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Revocar Credenciales
              </Button>
            ) : (
              <div className="flex flex-col sm:flex-row items-center gap-3 bg-red-50 p-3 rounded-lg border border-red-100 w-full animate-in slide-in-from-right-2">
                <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
                <span className="text-sm text-red-800 font-medium flex-1 text-center sm:text-left">
                  ¿Seguro? La sincronización con AFIP se detendrá.
                </span>
                <div className="flex gap-2 w-full sm:w-auto">
                  <Button
                    onClick={() => setShowConfirmRevoke(false)}
                    variant="outline"
                    className="flex-1 sm:flex-none border-red-200 text-red-700 hover:bg-red-100"
                  >
                    Cancelar
                  </Button>
                  <Button
                    onClick={handleRevoke}
                    className="flex-1 sm:flex-none bg-red-600 hover:bg-red-700 text-white"
                  >
                    {isRevoking ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : "Confirmar"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4">
        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-800">Bóveda de Credenciales AFIP</h2>
          <p className="text-sm text-slate-500">
            Entidad: <span className="font-semibold text-slate-700">{entidadActiva?.razon_social || 'No seleccionada'}</span>
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Certificado (.crt / .pem)</label>
          <input type="file" accept=".crt,.pem" className="hidden" ref={certInputRef} onChange={(e) => setCertFile(e.target.files?.[0] || null)} />
          <Button type="button" variant="outline" className="w-full justify-start text-slate-600" onClick={() => certInputRef.current?.click()}>
            <UploadCloud className="w-4 h-4 mr-2 text-indigo-500" />
            <span className="truncate">{certFile ? certFile.name : "Seleccionar archivo..."}</span>
          </Button>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Llave Privada (.key)</label>
          <input type="file" accept=".key" className="hidden" ref={keyInputRef} onChange={(e) => setKeyFile(e.target.files?.[0] || null)} />
          <Button type="button" variant="outline" className="w-full justify-start text-slate-600" onClick={() => keyInputRef.current?.click()}>
            <FileKey className="w-4 h-4 mr-2 text-emerald-500" />
            <span className="truncate">{keyFile ? keyFile.name : "Seleccionar archivo..."}</span>
          </Button>
          <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 shrink-0" /> Cifrado AES-128. La llave no viaja en texto plano a la DB.
          </p>
        </div>

        {status.type === 'error' && <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm border border-red-100">{status.message}</div>}

        <div className="pt-4 border-t border-slate-100 flex justify-end">
          <Button onClick={handleUpload} disabled={isUploading || !certFile || !keyFile} className="bg-indigo-600 hover:bg-indigo-700 text-white w-full sm:w-auto">
            {isUploading && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
            {isUploading ? "Cifrando..." : "Guardar en Bóveda"}
          </Button>
        </div>
      </div>
    </div>
  );
}

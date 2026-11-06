import { useEffect, useState } from "react";
import { useEquipo } from "@/hooks/useEquipo";
import { useAuthStore } from "@/store/useAuthStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { UserPlus, Trash2, Loader2, ShieldAlert, Copy, CheckCircle2, AlertCircle } from "lucide-react";
import { extractApiError } from "@/lib/utils";
import type { Miembro } from "@/hooks/useEquipo";

type TeamRole = 'visor' | 'operador' | 'editor' | 'admin';
type MemberUpdate = { rol?: string; is_active?: boolean };

interface InvitationResponse {
  message: string;
  magic_link_token: string;
  expires_in_hours: number;
}

// ==========================================
// 🛡️ COMPONENTE INTERNO: SELECTOR DE ROL REACTIVO
// ==========================================
function SelectorDeRol({
  usuario,
  isAdmin,
  actualizarMiembro,
  showFeedback
}: {
  usuario: Miembro;
  isAdmin: boolean;
  actualizarMiembro: (email: string, payload: MemberUpdate) => Promise<void>;
  showFeedback: (type: 'success' | 'error', msg: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [rolActual, setRolActual] = useState(usuario.rol.toLowerCase());

  const handleRoleChange = async (nuevoRol: TeamRole) => {
    setLoading(true);
    try {
      await actualizarMiembro(usuario.user_id, { rol: nuevoRol });
      setRolActual(nuevoRol);
      showFeedback('success', `Rol de ${usuario.user_id} actualizado a ${nuevoRol.toUpperCase()}`);
    } catch (error: unknown) {
      // 🌟 PRUEBA E2E: Aquí atrapamos el HTTP 400 del "Seguro Anti-Lockout"
      const mensaje = extractApiError(error, "Fallo al cambiar el rol.");
      showFeedback('error', mensaje);
    } finally {
      setLoading(false);
    }
  };

  // Si no es admin, o si el usuario es el Dueño principal (intocable), mostramos el Badge estático.
  if (!isAdmin || rolActual === 'dueño' || rolActual === 'owner') {
    return (
      <Badge
        variant="outline"
        className={`uppercase text-[11px] font-bold tracking-wider border-transparent ${
          rolActual === 'dueño' || rolActual === 'owner'
            ? 'bg-slate-900 text-white'
            : 'bg-indigo-50 text-indigo-700 border-indigo-100'
        }`}
      >
        {rolActual}
      </Badge>
    );
  }

  // Si es admin, mostramos el Selector camuflado como un Badge interactivo
  return (
    <div className="flex items-center gap-2">
      <Select value={rolActual} onValueChange={handleRoleChange} disabled={loading}>
        <SelectTrigger className="h-7 text-[11px] font-bold uppercase tracking-wider w-[140px] bg-indigo-50 text-indigo-700 border-indigo-100 focus:ring-indigo-500">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="visor">Visor</SelectItem>
          <SelectItem value="operador">Operador</SelectItem>
          <SelectItem value="editor">Editor</SelectItem>
          <SelectItem value="admin">Administrador</SelectItem>
        </SelectContent>
      </Select>
      {loading && <Loader2 className="w-3.5 h-3.5 text-indigo-500 animate-spin shrink-0" />}
    </div>
  );
}

export default function EquipoPage() {
  const { miembros, entidades, loading, fetchEquipo, fetchEntidades, invitarMiembro, actualizarMiembro, eliminarMiembro } = useEquipo();

  // 🌟 Estados del Formulario
  const [nuevoEmail, setNuevoEmail] = useState("");
  const [nuevoRol, setNuevoRol] = useState("OPERADOR"); // 🌟 FIX: Rol dinámico
  const [entidadSeleccionada, setEntidadSeleccionada] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 🌟 Estados de Feedback Visual
  const [errorUi, setErrorUi] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{ type: 'success' | 'error', msg: string } | null>(null);
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const user = useAuthStore((state) => state.user);
  const isAdmin = ['admin', 'owner', 'dueño', 'propietario'].includes(String(user?.role || '').toLowerCase());

  useEffect(() => {
    fetchEquipo();
    if (isAdmin && user?.tenant_id) {
      fetchEntidades(user.tenant_id);
    }
  }, [fetchEquipo, fetchEntidades, isAdmin, user?.tenant_id]);

  const showFeedback = (type: 'success' | 'error', msg: string) => {
    setActionFeedback({ type, msg });
    setTimeout(() => setActionFeedback(null), 5000); // 🌟 FIX: 5 segundos para que de tiempo a leer errores E2E
  };

  const handleInvitar = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorUi(null);
    setGeneratedLink(null);

    if (!nuevoEmail || !entidadSeleccionada) {
      setErrorUi("Debes ingresar un email y seleccionar una empresa.");
      return;
    }

    setIsSubmitting(true);
    try {
      // 🌟 FIX: Pasamos el 'nuevoRol' en lugar del string hardcodeado "OPERADOR"
      const response: InvitationResponse = await invitarMiembro(nuevoEmail, nuevoRol, parseInt(entidadSeleccionada));

      const baseUrl = window.location.origin;
      const magicLink = `${baseUrl}/join?token=${response.magic_link_token}`;
      setGeneratedLink(magicLink);

      setNuevoEmail("");
      setNuevoRol("OPERADOR");
      setEntidadSeleccionada("");
    } catch (err: unknown) {
      setErrorUi(extractApiError(err, "Error al invitar al usuario. Intente nuevamente."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyLink = () => {
    if (generatedLink) {
      navigator.clipboard.writeText(generatedLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleToggleEstado = async (email: string, checked: boolean) => {
    try {
      await actualizarMiembro(email, { is_active: checked });
      showFeedback('success', `El acceso de ${email} ha sido ${checked ? 'activado' : 'suspendido'}.`);
    } catch (error: unknown) {
      const msg = extractApiError(error, `Fallo al actualizar el estado de ${email}.`);
      showFeedback('error', msg);
    }
  };

  const handleEliminar = async (email: string) => {
    try {
      await eliminarMiembro(email);
      showFeedback('success', `Usuario ${email} eliminado permanentemente.`);
    } catch (error: unknown) {
      const msg = extractApiError(error, `Fallo al eliminar al usuario ${email}.`);
      showFeedback('error', msg);
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Directorio de Equipo</h1>
          <p className="text-sm sm:text-base text-slate-500 mt-1">
            {isAdmin ? "Administrá quién tiene acceso a esta empresa y sus roles." : "Lista de colaboradores con acceso a esta empresa."}
          </p>
        </div>
      </div>

      {actionFeedback && (
        <div className={`p-4 rounded-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-2 shadow-sm ${actionFeedback.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {actionFeedback.type === 'success' ? <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" /> : <ShieldAlert className="h-5 w-5 text-red-500 shrink-0" />}
          <p className="text-sm font-medium">{actionFeedback.msg}</p>
        </div>
      )}

      {isAdmin && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
            <CardTitle className="text-lg flex items-center gap-2 text-slate-800">
              <UserPlus className="w-5 h-5 text-indigo-600" />
              Delegar Acceso
            </CardTitle>
            <CardDescription>Genera un enlace de invitación seguro para nuevos colaboradores.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 pt-6">

            {errorUi && (
              <div className="p-3 bg-red-50 border border-red-100 rounded-md flex items-center gap-2 text-sm text-red-800 animate-in shake">
                <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
                {errorUi}
              </div>
            )}

            {generatedLink && (
              <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-xl animate-in fade-in zoom-in duration-300 shadow-sm">
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                  <div className="flex items-center gap-3 flex-1">
                    <CheckCircle2 className="h-6 w-6 text-emerald-500 shrink-0" />
                    <div>
                      <h3 className="text-sm font-bold text-emerald-900">¡Invitación generada!</h3>
                      <p className="text-xs text-emerald-700 mt-0.5">Copia el enlace y envíalo al colaborador. Caducará en 48hs.</p>
                    </div>
                  </div>
                  <div className="flex w-full sm:w-auto items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={generatedLink}
                      className="hidden sm:block w-48 text-xs rounded border border-emerald-200 bg-white px-2 py-2 text-emerald-800 outline-none"
                    />
                    <Button
                      type="button"
                      onClick={handleCopyLink}
                      className={`w-full sm:w-auto transition-all ${copied ? 'bg-emerald-600 hover:bg-emerald-700 shadow-md' : 'bg-slate-900 hover:bg-slate-800 shadow-sm'} text-white shrink-0`}
                    >
                      {copied ? <CheckCircle2 className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                      {copied ? 'Copiado' : 'Copiar Magic Link'}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleInvitar} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
              <div className="md:col-span-4 space-y-1.5">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Correo Electrónico</label>
                <Input
                  placeholder="colaborador@empresa.com"
                  type="email"
                  required
                  value={nuevoEmail}
                  onChange={(e) => setNuevoEmail(e.target.value)}
                  disabled={isSubmitting}
                  className="bg-white border-slate-200 h-10"
                />
              </div>

              <div className="md:col-span-3 space-y-1.5">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Nivel de Acceso</label>
                <Select value={nuevoRol} onValueChange={setNuevoRol} disabled={isSubmitting}>
                  <SelectTrigger className="h-10 bg-white border-slate-200 font-medium">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="VISOR">Visor</SelectItem>
                    <SelectItem value="OPERADOR">Operador</SelectItem>
                    <SelectItem value="EDITOR">Editor</SelectItem>
                    <SelectItem value="ADMIN">Administrador</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="md:col-span-3 space-y-1.5">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Empresa Destino</label>
                <Select value={entidadSeleccionada} onValueChange={setEntidadSeleccionada} disabled={isSubmitting || entidades.length === 0}>
                  <SelectTrigger className="h-10 bg-white border-slate-200">
                    <SelectValue placeholder="Seleccionar..." />
                  </SelectTrigger>
                  <SelectContent>
                    {entidades.map(ent => (
                      <SelectItem key={ent.id} value={ent.id.toString()}>{ent.razon_social}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="md:col-span-2">
                <Button type="submit" disabled={isSubmitting} className="bg-indigo-600 hover:bg-indigo-700 w-full h-10 shadow-sm">
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <UserPlus className="w-4 h-4 mr-2" />}
                  {isSubmitting ? "Procesando..." : "Generar"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
            <Table>
            <TableHeader className="bg-slate-50">
                <TableRow>
                <TableHead className="whitespace-nowrap font-semibold text-slate-600">Usuario</TableHead>
                <TableHead className="font-semibold text-slate-600">Rol Asignado</TableHead>
                <TableHead className="font-semibold text-slate-600">Estado Operativo</TableHead>
                {isAdmin && <TableHead className="text-right font-semibold text-slate-600">Acciones</TableHead>}
                </TableRow>
            </TableHeader>
            <TableBody>
                {loading ? (
                <TableRow><TableCell colSpan={isAdmin ? 4 : 3} className="text-center py-12"><Loader2 className="animate-spin mx-auto text-indigo-500 h-8 w-8" /></TableCell></TableRow>
                ) : miembros.length === 0 ? (
                <TableRow><TableCell colSpan={isAdmin ? 4 : 3} className="text-center py-12 text-slate-500">No hay usuarios asignados a esta empresa.</TableCell></TableRow>
                ) : (
                miembros.map((m) => (
                    <TableRow key={m.id} className={`transition-colors ${!m.is_active ? "opacity-60 bg-slate-50/50" : "hover:bg-slate-50/50"}`}>
                    <TableCell className="font-medium whitespace-nowrap text-slate-900">
                        {m.user_id}
                        {m.user_id === user?.email && <span className="ml-2 text-[10px] uppercase tracking-wider bg-indigo-100 text-indigo-800 px-2.5 py-0.5 rounded-full font-bold">Tú</span>}
                    </TableCell>

                    <TableCell>
                        <SelectorDeRol
                          usuario={m}
                          isAdmin={isAdmin}
                          actualizarMiembro={actualizarMiembro}
                          showFeedback={showFeedback}
                        />
                    </TableCell>

                    <TableCell>
                        <div className="flex items-center gap-2">
                        <Switch
                            checked={!!m.is_active}
                            disabled={!isAdmin || m.user_id === user?.email}
                            onCheckedChange={(checked) => handleToggleEstado(m.user_id, checked)}
                            className="data-[state=checked]:bg-emerald-500"
                        />
                        <span className={`text-sm font-medium ${m.is_active ? 'text-slate-900' : 'text-slate-400'}`}>
                          {m.is_active ? "Activo" : "Suspendido"}
                        </span>
                        </div>
                    </TableCell>

                    {isAdmin && (
                        <TableCell className="text-right">
                        {m.rol !== 'DUEÑO' && m.user_id !== user?.email && (
                            <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700 hover:bg-red-50 h-8 px-2 transition-colors">
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent className="rounded-xl">
                                <AlertDialogHeader>
                                <AlertDialogTitle className="flex items-center gap-2 text-red-600 font-bold">
                                    <ShieldAlert className="w-5 h-5" />
                                    ¿Borrado Permanente?
                                </AlertDialogTitle>
                                <AlertDialogDescription className="text-slate-600 leading-relaxed">
                                    Estás a punto de revocar el acceso y eliminar a <strong>{m.user_id}</strong>. Te recomendamos fuertemente utilizar el interruptor de "Suspender" para preservar la trazabilidad forense de sus acciones pasadas. Esta acción no se puede deshacer.
                                </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter className="mt-4">
                                <AlertDialogCancel className="border-slate-200">Cancelar</AlertDialogCancel>
                                <AlertDialogAction
                                    onClick={() => handleEliminar(m.user_id)}
                                    className="bg-red-600 hover:bg-red-700 text-white shadow-sm"
                                >
                                    Sí, eliminar
                                </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                            </AlertDialog>
                        )}
                        </TableCell>
                    )}
                    </TableRow>
                ))
                )}
            </TableBody>
            </Table>
        </div>
      </Card>
    </div>
  );
}

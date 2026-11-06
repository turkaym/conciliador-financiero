import { useCallback, useEffect, useState } from "react"
import { AxiosError } from "axios"
import { Loader2, RefreshCw, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { aiRulesApi, type RuleDraft } from "@/features/ai-rules/api"
import { mergeRuleAfterConflict, type AiRule } from "@/features/ai-rules/model"

const emptyDraft: RuleDraft = { patron_concepto: "", cuit_asociado: "" }

export default function ReglasIAPage() {
  const [rules, setRules] = useState<AiRule[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState("")
  const [active, setActive] = useState("all")
  const [draft, setDraft] = useState<RuleDraft>(emptyDraft)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setMessage("")
    try {
      const result = await aiRulesApi.list(search, active)
      setRules(result.items)
      setTotal(result.total)
    } catch {
      setMessage("No se pudieron cargar las reglas. Podés reintentar.")
    } finally {
      setLoading(false)
    }
  }, [active, search])

  useEffect(() => { void load() }, [load])

  const createRule = async (event: React.FormEvent) => {
    event.preventDefault()
    setMessage("")
    const cuit = draft.cuit_asociado.replace(/[\s-]/g, "")
    if (draft.patron_concepto.trim().length < 2 || !/^\d{11}$/.test(cuit)) {
      setMessage("Revisá el concepto y el CUIT de 11 dígitos.")
      return
    }
    setSaving(true)
    try {
      await aiRulesApi.create({ ...draft, cuit_asociado: cuit })
      setDraft(emptyDraft)
      setMessage("Regla creada correctamente.")
      await load()
    } catch (error) {
      const status = (error as AxiosError).response?.status
      setMessage(status === 400 ? "La regla contiene datos inválidos." : "No se pudo crear la regla. Podés reintentar.")
    } finally {
      setSaving(false)
    }
  }

  const mutate = async (rule: AiRule, operation: "toggle" | "deactivate") => {
    setMessage("")
    try {
      const updated = operation === "toggle" ? await aiRulesApi.toggle(rule) : await aiRulesApi.deactivate(rule)
      setRules((current) => mergeRuleAfterConflict(current, updated))
      setMessage(operation === "deactivate" ? "Regla desactivada con registro de auditoría." : "Estado actualizado.")
    } catch (error) {
      if ((error as AxiosError).response?.status === 409) {
        try {
          const current = await aiRulesApi.get(rule.id)
          setRules((items) => mergeRuleAfterConflict(items, current))
        } catch { await load() }
        setMessage("La regla cambió en otra operación. Actualizamos el estado del servidor; revisalo e intentá nuevamente.")
      } else {
        setMessage("No se pudo completar la operación. Podés reintentar.")
      }
    }
  }

  return (
    <section className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-slate-900">Reglas IA determinísticas</h1>
        <p className="mt-1 text-sm text-slate-500">Administrá coincidencias por concepto y CUIT. No utiliza modelos externos.</p>
      </header>

      <form onSubmit={createRule} className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-4">
        <div className="md:col-span-2">
          <label htmlFor="rule-pattern" className="mb-1 block text-sm font-medium text-slate-700">Concepto a normalizar</label>
          <input id="rule-pattern" value={draft.patron_concepto} onChange={(e) => setDraft({ ...draft, patron_concepto: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="PAGO PROVEEDOR" />
        </div>
        <div>
          <label htmlFor="rule-cuit" className="mb-1 block text-sm font-medium text-slate-700">CUIT asociado</label>
          <input id="rule-cuit" value={draft.cuit_asociado} onChange={(e) => setDraft({ ...draft, cuit_asociado: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="30-71234567-8" />
        </div>
        <div>
          <label htmlFor="rule-voucher" className="mb-1 block text-sm font-medium text-slate-700">Tipo de comprobante (opcional)</label>
          <input id="rule-voucher" type="number" min="1" max="999" value={draft.tipo_cbte_asociado ?? ""} onChange={(e) => setDraft({ ...draft, tipo_cbte_asociado: e.target.value ? Number(e.target.value) : undefined })} className="w-full rounded-md border border-slate-300 px-3 py-2" />
        </div>
        <Button disabled={saving} type="submit" className="md:col-span-4 md:w-fit">{saving ? "Creando regla..." : "Crear regla manual"}</Button>
      </form>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="flex-1"><label htmlFor="rule-search" className="sr-only">Buscar reglas</label><input id="rule-search" value={search} onChange={(e) => setSearch(e.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="Buscar por concepto o CUIT" /></div>
        <div><label htmlFor="rule-state" className="sr-only">Filtrar por estado</label><select id="rule-state" value={active} onChange={(e) => setActive(e.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2"><option value="all">Todos los estados</option><option value="active">Activas</option><option value="inactive">Inactivas</option></select></div>
        <Button type="button" variant="outline" onClick={() => void load()}><RefreshCw className="mr-2 h-4 w-4" />Actualizar reglas</Button>
      </div>

      <p aria-live="polite" className="min-h-5 text-sm font-medium text-slate-700">{message}</p>
      {loading ? <div role="status" className="flex items-center gap-2 text-slate-500"><Loader2 className="h-5 w-5 animate-spin" />Cargando reglas...</div> : rules.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center"><ShieldCheck className="mx-auto mb-3 h-8 w-8 text-slate-400" /><p className="font-medium text-slate-800">No hay reglas para este filtro.</p></div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm"><caption className="sr-only">{total} reglas determinísticas</caption><thead className="border-b bg-slate-50 text-slate-600"><tr><th className="p-3">Concepto normalizado</th><th className="p-3">CUIT</th><th className="p-3">Comprobante</th><th className="p-3">Estado</th><th className="p-3">Acciones</th></tr></thead>
            <tbody>{rules.map((rule) => <tr key={rule.id} className="border-b last:border-0"><td className="p-3 font-medium text-slate-900">{rule.patron_concepto}</td><td className="p-3 font-mono">{rule.cuit_asociado || "Sin CUIT"}</td><td className="p-3">{rule.tipo_cbte_asociado ?? "Cualquiera"}</td><td className="p-3"><span className="font-medium">{rule.activa ? "Activa" : "Inactiva"}</span><span className="ml-2 text-slate-500">({rule.frecuencia_uso} usos)</span></td><td className="p-3"><div className="flex flex-wrap gap-2"><Button type="button" variant="outline" onClick={() => void mutate(rule, "toggle")}>{rule.activa ? "Desactivar regla" : "Activar regla"}</Button>{rule.activa && <Button type="button" variant="outline" onClick={() => void mutate(rule, "deactivate")}>Desactivar con auditoría</Button>}</div></td></tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}

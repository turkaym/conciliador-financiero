export interface AiRule {
  id: number
  patron_concepto: string
  cuit_asociado: string | null
  tipo_cbte_asociado: number | null
  frecuencia_uso: number
  activa: boolean
  created_at: string
  updated_at: string
}

interface CapabilityLike { identifier: string; usable: boolean }

export function aiRulesAccess(
  capabilities: readonly CapabilityLike[],
  features: Record<string, unknown>,
  role?: string,
) {
  if (!capabilities.some((item) => item.identifier === "ai_rules" && item.usable)) return "unavailable"
  if (features.ai_rules !== true || !["admin", "dueño"].includes(role?.toLowerCase() || "")) return "unauthorized"
  return "allowed"
}

export function mergeRuleAfterConflict(rules: AiRule[], current: AiRule) {
  return rules.map((rule) => rule.id === current.id ? current : rule)
}

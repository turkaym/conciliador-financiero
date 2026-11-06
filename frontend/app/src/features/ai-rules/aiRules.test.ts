import { aiRulesAccess, mergeRuleAfterConflict, type AiRule } from "./model.ts"

const usable = [{ identifier: "ai_rules", enabled: true, implemented: true, usable: true }] as const
if (aiRulesAccess(usable, { ai_rules: true }, "admin") !== "allowed") throw new Error("Entitled admin must be allowed")
if (aiRulesAccess(usable, {}, "admin") !== "unauthorized") throw new Error("Unentitled tenant must be denied")
if (aiRulesAccess(usable, { ai_rules: true }, "operador") !== "unauthorized") throw new Error("Operator must be denied")
if (aiRulesAccess([], { ai_rules: true }, "dueño") !== "unavailable") throw new Error("Unusable feature must fail closed")

const stale = { id: 1, patron_concepto: "PAGO", updated_at: "old" } as AiRule
const current = { ...stale, activa: false, updated_at: "new" }
const draft = { patron_concepto: "BORRADOR", cuit_asociado: "30712345678" }
const merged = mergeRuleAfterConflict([stale], current)
if (merged[0].updated_at !== "new" || draft.patron_concepto !== "BORRADOR") {
  throw new Error("Conflict refresh must preserve form input and use server state")
}

console.log("AI Rules route and conflict contract proof passed")

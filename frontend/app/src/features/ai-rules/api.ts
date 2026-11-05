import api from "@/api/axios"
import type { AiRule } from "./model"

export interface RuleList { items: AiRule[]; total: number }
export interface RuleDraft { patron_concepto: string; cuit_asociado: string; tipo_cbte_asociado?: number }

export const aiRulesApi = {
  async list(search = "", active = "all") {
    const { data } = await api.get<RuleList>("/v1/ai-rules", {
      params: { buscar: search || undefined, activa: active === "all" ? undefined : active === "active" },
    })
    return data
  },
  async get(id: number) {
    return (await api.get<AiRule>(`/v1/ai-rules/${id}`)).data
  },
  async create(draft: RuleDraft) {
    return (await api.post<AiRule>("/v1/ai-rules", { tipo_regla: "concepto_cuit", ...draft })).data
  },
  async toggle(rule: AiRule) {
    return (await api.patch<AiRule>(`/v1/ai-rules/${rule.id}`, {
      activa: !rule.activa, expected_updated_at: rule.updated_at,
    })).data
  },
  async deactivate(rule: AiRule) {
    return (await api.delete<AiRule>(`/v1/ai-rules/${rule.id}`, {
      params: { expected_updated_at: rule.updated_at },
    })).data
  },
}

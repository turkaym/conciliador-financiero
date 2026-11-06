export type FeatureIdentifier =
  | "b2b_directory"
  | "expenses_payments"
  | "tax_registries"
  | "team"
  | "ai_rules"
  | "reconciliation"
  | "ai_copilot"
  | "b2b_integrations"

export interface Capability {
  identifier: FeatureIdentifier
  enabled: boolean
  implemented: boolean
  usable: boolean
}

export function isFeatureUsable(capabilities: Capability[], identifier: FeatureIdentifier) {
  return capabilities.some((capability) => capability.identifier === identifier && capability.usable)
}

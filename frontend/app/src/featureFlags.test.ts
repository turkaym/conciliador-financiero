import { isFeatureUsable, type Capability } from "./featureFlags.ts"


const capabilities: Capability[] = [
  { identifier: "b2b_directory", enabled: true, implemented: true, usable: true },
  { identifier: "expenses_payments", enabled: true, implemented: true, usable: true },
  { identifier: "tax_registries", enabled: true, implemented: true, usable: true },
  { identifier: "team", enabled: true, implemented: true, usable: true },
  { identifier: "ai_rules", enabled: true, implemented: false, usable: false },
  { identifier: "reconciliation", enabled: false, implemented: true, usable: false },
  { identifier: "ai_copilot", enabled: false, implemented: true, usable: false },
  { identifier: "b2b_integrations", enabled: false, implemented: true, usable: false },
]


const importedNavigation = ["b2b_directory", "expenses_payments", "tax_registries", "team", "ai_rules", "reconciliation"] as const
const visible = importedNavigation.filter((identifier) => isFeatureUsable(capabilities, identifier))
const expected = ["b2b_directory", "expenses_payments", "tax_registries", "team"]

if (JSON.stringify(visible) !== JSON.stringify(expected)) throw new Error(`Unexpected navigation: ${visible}`)
if (isFeatureUsable(capabilities, "reconciliation")) throw new Error("Reconciliation must be hidden")
if (isFeatureUsable(capabilities, "ai_copilot")) throw new Error("AI Copilot must be hidden")
if (isFeatureUsable(capabilities, "b2b_integrations")) throw new Error("B2B Integrations must be hidden")
if (isFeatureUsable([], "team")) throw new Error("Missing capabilities must fail closed")

console.log("Frontend feature route/navigation proof passed")

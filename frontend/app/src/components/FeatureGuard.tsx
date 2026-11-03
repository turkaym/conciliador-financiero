import type { ReactNode } from "react"
import { useAuthStore } from "@/store/useAuthStore"
import { isFeatureUsable, type FeatureIdentifier } from "@/featureFlags"

interface FeatureGuardProps {
  feature: FeatureIdentifier
  tenantFeature?: string
  fallback?: ReactNode
  children: ReactNode
}

export function FeatureGuard({ feature, tenantFeature, fallback = null, children }: FeatureGuardProps) {
  const features = useAuthStore((state) => state.features);
  const capabilities = useAuthStore((state) => state.capabilities);

  if (!isFeatureUsable(capabilities, feature) || (tenantFeature && features[tenantFeature] !== true)) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

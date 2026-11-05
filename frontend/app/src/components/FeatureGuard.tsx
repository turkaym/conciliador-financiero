import type { ReactNode } from "react"
import { useAuthStore } from "@/store/useAuthStore"

interface FeatureGuardProps {
  feature: string
  fallback?: ReactNode
  children: ReactNode
}

export function FeatureGuard({ feature, fallback = null, children }: FeatureGuardProps) {
  const features = useAuthStore((state) => state.features);

  if (features[feature] !== true) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

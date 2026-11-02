import { ReactNode } from "react"
import { useAuthStore } from "@/store/useAuthStore"

interface FeatureGuardProps {
  feature: string
  fallback?: ReactNode
  children: ReactNode
}

export function FeatureGuard({ feature, fallback = null, children }: FeatureGuardProps) {
  // 1. Extraemos SOLO features del store, y le asignamos un array vacío si no existe
  const features = useAuthStore((state) => state.features);

  // 2. Validación absoluta: Aseguramos que sea un array legítimo de Javascript
  const safeFeatures = Array.isArray(features) ? features : [];

  // 3. Ahora la lectura es 100% segura
  if (!safeFeatures.includes(feature)) {
    return <>{fallback}</>
  }

  return <>{children}</>
}
import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  // Cargamos las variables de entorno de Vite (.env)
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: true, // Fundamental para que Docker exponga el puerto a Windows
      port: 5173,
      allowedHosts: ["app.htsolution.org", "localhost"],
      proxy: {
        // 🌟 MAGIA DEL PROXY: Interceptamos peticiones a /api y las mandamos al backend
        '/api': {
          // Si VITE_API_URL está definida en docker-compose, la usa, sino usa el nombre del contenedor
          target: env.VITE_API_URL || 'http://api-gateway:80',
          changeOrigin: true,
          secure: false, // Por si el backend no tiene HTTPS en local
          rewrite: (path) => path.replace(/^\/api/, ''), // Le saca el '/api' antes de dárselo a FastAPI
        }
      }
    }
  }
})
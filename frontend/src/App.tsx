import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { LoginForm, useAuth } from "./auth";
import "./styles.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();
  return session ? <>{children}</> : <Navigate to="/login" replace state={{ from: location }} />;
}

function AppShell() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Ir al inicio">CONCILIADOR</a>
        <div className="user-menu">
          <span>{session?.user.email}</span>
          <button className="text-button" type="button" onClick={handleLogout}>Cerrar sesión</button>
        </div>
      </header>
      <main className="workspace">
        <p className="eyebrow">Panel de trabajo</p>
        <h1>Bienvenido al conciliador</h1>
        <p className="muted">Tu sesión está activa. Las cargas y conciliaciones estarán disponibles en las próximas etapas del MVP.</p>
        <div className="status-card" role="status">
          <span className="status-dot" aria-hidden="true" />
          Sesión autenticada
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const { session } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to="/" replace /> : <LoginForm />} />
      <Route path="/" element={<ProtectedRoute><AppShell /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to={session ? "/" : "/login"} replace />} />
    </Routes>
  );
}

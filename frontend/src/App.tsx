import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { LoginForm, useAuth } from "./auth";
import { ImportPage } from "./modules/imports/ImportPage";
import { PendingPage } from "./modules/pending/PendingPage";
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
        <nav className="main-nav" aria-label="Navegación principal"><Link to="/">Importar</Link><Link to="/pending">Pendientes</Link></nav>
        <main className="workspace">
         <p className="eyebrow">Panel de trabajo</p>
         <h1>Bienvenido al conciliador</h1>
         <Routes><Route path="/" element={<ImportPage />} /><Route path="/pending" element={<PendingPage />} /></Routes>
      </main>
    </div>
  );
}

export default function App() {
  const { session } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to="/" replace /> : <LoginForm />} />
      <Route path="/*" element={<ProtectedRoute><AppShell /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to={session ? "/" : "/login"} replace />} />
    </Routes>
  );
}

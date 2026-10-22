import {
  createContext,
  type FormEvent,
  type PropsWithChildren,
  useEffect,
  useContext,
  useState,
} from "react";
import { api, type LoginResponse, type User } from "./api";

export interface Session {
  accessToken: string;
  user: User;
  expiresAt: number;
}

const sessionKey = "conciliador.session";

function readSession(): Session | null {
  try {
    const stored = localStorage.getItem(sessionKey);
    if (!stored) return null;
    const session = JSON.parse(stored) as Session;
    if (!session.accessToken || !session.user || session.expiresAt <= Date.now()) {
      localStorage.removeItem(sessionKey);
      return null;
    }
    return session;
  } catch {
    localStorage.removeItem(sessionKey);
    return null;
  }
}

function saveSession(response: LoginResponse): Session {
  const session: Session = {
    accessToken: response.access_token,
    user: response.user,
    expiresAt: Date.now() + response.expires_in * 1000,
  };
  localStorage.setItem(sessionKey, JSON.stringify(session));
  return session;
}

interface AuthContextValue {
  session: Session | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(readSession);

  useEffect(() => {
    if (!session) return;
    const timeout = window.setTimeout(() => {
      localStorage.removeItem(sessionKey);
      setSession(null);
    }, Math.max(0, session.expiresAt - Date.now()));
    return () => window.clearTimeout(timeout);
  }, [session]);

  async function login(email: string, password: string) {
    const response = await api.login(email, password);
    setSession(saveSession(response));
  }

  function logout() {
    localStorage.removeItem(sessionKey);
    setSession(null);
  }

  return <AuthContext.Provider value={{ session, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function LoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo iniciar sesión.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <p className="eyebrow">Acceso seguro</p>
        <h1 id="login-title">Iniciar sesión</h1>
        <p className="muted">Ingresá para continuar con la conciliación financiera.</p>
        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && <p className="error" role="alert">{error}</p>}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </section>
    </main>
  );
}

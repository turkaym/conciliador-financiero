export interface User {
  id: number;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor.", 0);
  }

  const body = (await response.json().catch(() => null)) as
    | { message?: string; code?: string }
    | null;
  if (!response.ok) {
    throw new ApiError(
      body?.message ?? "Ocurrió un error inesperado.",
      response.status,
      body?.code,
    );
  }
  return body as T;
}

export const api = {
  login(email: string, password: string) {
    return request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
};

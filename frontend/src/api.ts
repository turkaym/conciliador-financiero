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

export type ImportType = "MOVIMIENTO" | "COMPROBANTE";

export interface CatalogSource {
  id: number;
  code: string;
  name: string;
  type: ImportType;
}

export interface CatalogTemplate {
  id: number;
  name: string;
  type: ImportType;
  version: number;
  columns: string[];
}

export interface BatchResponse {
  id: number;
  source: CatalogSource;
  template: { id: number; name: string; version: number } | null;
  requested_template_id: number;
  type: ImportType;
  file_name: string;
  status: string;
  totals: { total_rows: number; valid_rows: number; invalid_rows: number };
  received_at: string;
  finished_at: string | null;
  original_batch_id?: number | null;
}

export interface ValidationErrorItem {
  id: number;
  scope: string;
  row_number: number | null;
  field: string | null;
  code: string;
  message: string;
  original_record_id: number | null;
  created_at: string;
}

export interface PendingItem {
  record_id: number;
  type: ImportType;
  batch_id: number;
  external_id: string | null;
  date: string;
  amount: string;
  currency: string;
  reference_original: string | null;
  state: string;
  cause: string;
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

async function request<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init?.headers);
    if (!headers.has("Content-Type") && !(init?.body instanceof FormData)) headers.set("Content-Type", "application/json");
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers,
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
  getSources(accessToken: string, type?: ImportType) {
    return request<{ total: number; items: CatalogSource[] }>(`/api/v1/catalog/sources${type ? `?type=${type}` : ""}`, undefined, accessToken);
  },
  getTemplates(accessToken: string, sourceId: number, type: ImportType) {
    return request<{ total: number; items: CatalogTemplate[] }>(`/api/v1/catalog/templates?source_id=${sourceId}&type=${type}`, undefined, accessToken);
  },
  submitBatch(accessToken: string, values: { sourceId: number; templateId: number; type: ImportType; file: File }) {
    const form = new FormData();
    form.append("source_id", String(values.sourceId));
    form.append("template_id", String(values.templateId));
    form.append("type", values.type);
    form.append("file", values.file);
    return request<BatchResponse>("/api/v1/batches", { method: "POST", body: form }, accessToken);
  },
  getBatchErrors(accessToken: string, batchId: number) {
    return request<{ total: number; items: ValidationErrorItem[] }>(`/api/v1/batches/${batchId}/errors`, undefined, accessToken);
  },
  getPending(accessToken: string) {
    return request<{ page: number; page_size: number; total: number; items: PendingItem[] }>("/api/v1/pending?page_size=100", undefined, accessToken);
  },
};

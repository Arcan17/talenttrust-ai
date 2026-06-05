import type { TokenPair, User, Vacancy, VacancyCreate } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACCESS_KEY = "tt_access";
const REFRESH_KEY = "tt_refresh";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// --- token storage (simple localStorage, client-side only) ---

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function setTokens(tokens: TokenPair): void {
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

// --- core fetch ---

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = opts;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor.");
  }

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- auth ---

export async function login(email: string, password: string): Promise<TokenPair> {
  const tokens = await request<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  setTokens(tokens);
  return tokens;
}

export function getMe(): Promise<User> {
  return request<User>("/api/v1/auth/me");
}

// --- vacancies ---

export function listVacancies(): Promise<Vacancy[]> {
  return request<Vacancy[]>("/api/v1/vacancies");
}

export function getVacancy(id: string): Promise<Vacancy> {
  return request<Vacancy>(`/api/v1/vacancies/${id}`);
}

export function createVacancy(payload: VacancyCreate): Promise<Vacancy> {
  return request<Vacancy>("/api/v1/vacancies", { method: "POST", body: payload });
}

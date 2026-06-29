import { EquityPoint, RunResult, Strategy, StrategyDetail } from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "diel_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
export function isLoggedIn(): boolean {
  return !!getToken();
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...opts, headers, cache: "no-store" });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---- auth ----
export const register = (handle: string, email: string, password: string) =>
  req<{ access_token: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ handle, email, password }),
  });

export const login = (email: string, password: string) =>
  req<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const me = () => req<{ id: string; handle: string; email: string }>("/auth/me");

// ---- strategies ----
export const listStrategies = () => req<Strategy[]>("/strategies");
export const getLeaderboard = () => req<Strategy[]>("/leaderboard");
export const getStrategy = (id: string) => req<StrategyDetail>(`/strategies/${id}`);

export const createStrategy = (payload: {
  name: string;
  symbol: string;
  timeframe: string;
  spec: Record<string, any>;
}) =>
  req<StrategyDetail>("/strategies", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runBacktest = (id: string, body: object) =>
  req<RunResult>(`/strategies/${id}/backtest`, { method: "POST", body: JSON.stringify(body) });

export const runVerify = (id: string, body: object) =>
  req<RunResult>(`/strategies/${id}/verify`, { method: "POST", body: JSON.stringify(body) });

export const getRun = (id: string) => req<RunResult>(`/runs/${id}`);
export const getEquity = (id: string) =>
  req<{ points: EquityPoint[] }>(`/strategies/${id}/equity`);

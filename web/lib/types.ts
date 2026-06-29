export interface Verification {
  badge: string;
  score: number;
}

export interface Strategy {
  id: string;
  name: string;
  symbol: string;
  timeframe: string;
  author_handle: string;
  visibility: string;
  verification?: Verification | null;
}

export interface StrategyDetail extends Strategy {
  spec: Record<string, any>;
}

export interface RunResult {
  id: string;
  strategy_id: string;
  kind: string;
  status: "pending" | "running" | "done" | "error";
  error?: string | null;
  metrics: Record<string, any>;
  report?: Record<string, any> | null;
}

export interface EquityPoint {
  t: string;
  equity: number;
}

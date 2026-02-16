/**
 * API Client
 *
 * Provides typed API access to the backend.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8090/api/v1';

// =============================================================================
// Dashboard Types
// =============================================================================

export interface SummaryResponse {
  total_entries: number;
  total_amount: number;
  debit_total: number;
  credit_total: number;
  unique_accounts: number;
  unique_journals: number;
  date_range: { from: string; to: string };
  high_risk_count: number;
  anomaly_count: number;
}

export interface TimeSeriesPoint {
  date: string;
  amount: number;
  count: number;
  debit: number;
  credit: number;
}

export interface TimeSeriesResponse {
  data: TimeSeriesPoint[];
  aggregation: string;
}

export interface AccountSummary {
  account_code: string;
  account_name: string;
  debit_total: number;
  credit_total: number;
  net_amount: number;
  entry_count: number;
}

export interface AccountsResponse {
  accounts: AccountSummary[];
  total_accounts: number;
}

export interface RiskItem {
  journal_id: string;
  gl_detail_id: string;
  risk_score: number;
  risk_factors: string[];
  amount: number;
  date: string;
  description: string;
}

export interface RiskResponse {
  high_risk: RiskItem[];
  medium_risk: RiskItem[];
  low_risk: RiskItem[];
  risk_distribution: { high: number; medium: number; low: number; minimal: number };
}

export interface KPIResponse {
  fiscal_year: number;
  total_entries: number;
  total_journals: number;
  total_amount: number;
  unique_users: number;
  unique_accounts: number;
  high_risk_count: number;
  high_risk_pct: number;
  avg_risk_score: number;
  self_approval_count: number;
}

export interface BenfordDistribution {
  digit: number;
  count: number;
  actual_pct: number;
  expected_pct: number;
  deviation: number;
}

export interface BenfordResponse {
  distribution: BenfordDistribution[];
  total_count: number;
  mad: number;
  conformity: 'close' | 'acceptable' | 'marginally_acceptable' | 'nonconforming';
}

// =============================================================================
// Analysis Types
// =============================================================================

export interface ViolationItem {
  gl_detail_id: string;
  journal_id: string;
  rule_id: string;
  rule_name: string;
  severity: string;
  category: string;
  description: string;
  amount: number;
  date: string;
}

export interface ViolationsResponse {
  violations: ViolationItem[];
  total_count: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
}

export interface MLAnomalyItem {
  gl_detail_id: string;
  journal_id: string;
  anomaly_score: number;
  detection_method: string;
  is_anomaly: boolean;
  amount: number;
  date: string;
  features: Record<string, unknown>;
}

export interface MLAnomaliesResponse {
  anomalies: MLAnomalyItem[];
  total_count: number;
  by_method: Record<string, number>;
}

export interface RulesSummaryResponse {
  rules: Array<{
    rule_id: string;
    rule_name: string;
    category: string;
    severity: string;
    violation_count: number;
    total_amount: number;
  }>;
  total_rules_triggered: number;
  total_violations: number;
  by_category: Record<string, { count: number; rules: number }>;
  by_severity: Record<string, number>;
}

// =============================================================================
// Batch Types
// =============================================================================

export interface BatchJobRequest {
  mode: 'full' | 'quick' | 'ml_only' | 'rules_only';
  fiscal_year: number;
  business_unit_code?: string;
  accounting_period?: number;
  update_aggregations?: boolean;
}

export interface BatchJobResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface BatchStatusResponse {
  job_id: string;
  status: string;
  mode: string;
  started_at: string;
  completed_at?: string;
  total_entries: number;
  rules_executed: number;
  total_violations: number;
  execution_time_ms: number;
  success: boolean;
  errors: string[];
}

// =============================================================================
// Agent Types
// =============================================================================

export interface AgentRequest {
  query?: string;
  fiscal_year?: number;
  context?: Record<string, unknown>;
}

export interface AgentResponse {
  session_id: string;
  agent_type: string;
  status: string;
  result: {
    response: string;
    context?: Record<string, unknown>;
    step_count?: number;
  };
}

// =============================================================================
// Report Types
// =============================================================================

export interface ReportRequest {
  report_type:
    | 'summary'
    | 'detailed'
    | 'executive'
    | 'violations'
    | 'risk'
    | 'benford'
    | 'working_paper';
  fiscal_year: number;
  period_from?: number;
  period_to?: number;
  accounts?: string[];
  include_details?: boolean;
  format?: 'json' | 'csv' | 'excel' | 'pdf';
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
}

// =============================================================================
// Rule Management Types
// =============================================================================

export interface AuditRule {
  rule_id: string;
  rule_name: string;
  rule_name_en: string | null;
  category: string;
  description: string | null;
  severity: string;
  is_enabled: boolean;
  parameters: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface RuleCategoryInfo {
  category: string;
  total: number;
  enabled: number;
}

// =============================================================================
// Period Comparison Types
// =============================================================================

export interface PeriodComparisonItem {
  account_code: string;
  account_name: string;
  current_amount: number;
  previous_amount: number;
  change_amount: number;
  change_percent: number | null;
}

export interface PeriodComparisonResponse {
  items: PeriodComparisonItem[];
  comparison_type: string;
  current_period: string;
  previous_period: string;
  total_current: number;
  total_previous: number;
}

// =============================================================================
// LLM Usage Types
// =============================================================================

export interface LLMUsageSummary {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
  by_provider: Record<
    string,
    { requests: number; input_tokens: number; output_tokens: number; cost_usd: number }
  >;
  by_request_type: Record<string, { requests: number; cost_usd: number }>;
}

export interface LLMDailyUsage {
  date: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface LLMDailyResponse {
  daily: LLMDailyUsage[];
  total_cost_usd: number;
  days: number;
}

// =============================================================================
// Fetch Wrapper
// =============================================================================

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// =============================================================================
// SSE Types & Helper
// =============================================================================

export interface SSEEvent {
  type: 'start' | 'thinking' | 'chunk' | 'complete' | 'error';
  agent?: string;
  content?: string;
  data?: Record<string, unknown>;
  message?: string;
}

export async function streamSSE(
  endpoint: string,
  body: Record<string, unknown>,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: SSEEvent = JSON.parse(line.slice(6));
          onEvent(event);
        } catch {
          // 不正なJSONは無視
        }
      }
    }
  }
}

// =============================================================================
// API Methods
// =============================================================================

export const api = {
  // ---------------------------------------------------------------------------
  // Health
  // ---------------------------------------------------------------------------
  healthCheck: (): Promise<{ status: string; app: string; version: string }> => {
    const base = API_BASE.replace(/\/api\/v1$/, '');
    return fetch(`${base}/health`).then((r) => r.json());
  },

  // ---------------------------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------------------------
  getDashboardSummary: (
    fiscalYear: number,
    periodFrom?: number,
    periodTo?: number
  ): Promise<SummaryResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
    });
    if (periodFrom) params.append('period_from', periodFrom.toString());
    if (periodTo) params.append('period_to', periodTo.toString());

    return fetchApi(`/dashboard/summary?${params}`);
  },

  getTimeSeries: (
    fiscalYear: number,
    aggregation: 'daily' | 'weekly' | 'monthly' = 'monthly',
    periodFrom?: number,
    periodTo?: number
  ): Promise<TimeSeriesResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
      aggregation,
    });
    if (periodFrom) params.append('period_from', periodFrom.toString());
    if (periodTo) params.append('period_to', periodTo.toString());

    return fetchApi(`/dashboard/timeseries?${params}`);
  },

  getAccounts: (
    fiscalYear: number,
    limit?: number,
    periodFrom?: number,
    periodTo?: number
  ): Promise<AccountsResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
    });
    if (limit) params.append('limit', limit.toString());
    if (periodFrom) params.append('period_from', periodFrom.toString());
    if (periodTo) params.append('period_to', periodTo.toString());

    return fetchApi(`/dashboard/accounts?${params}`);
  },

  getRiskAnalysis: (
    fiscalYear: number,
    periodFrom?: number,
    periodTo?: number,
    limit?: number
  ): Promise<RiskResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
    });
    if (periodFrom) params.append('period_from', periodFrom.toString());
    if (periodTo) params.append('period_to', periodTo.toString());
    if (limit) params.append('limit', limit.toString());

    return fetchApi(`/dashboard/risk?${params}`);
  },

  getKPI: (fiscalYear: number): Promise<KPIResponse> => {
    return fetchApi(`/dashboard/kpi?fiscal_year=${fiscalYear}`);
  },

  getBenford: (fiscalYear: number): Promise<BenfordResponse> => {
    return fetchApi(`/dashboard/benford?fiscal_year=${fiscalYear}`);
  },

  // ---------------------------------------------------------------------------
  // Analysis
  // ---------------------------------------------------------------------------
  getViolations: (
    fiscalYear: number,
    options?: {
      ruleId?: string;
      severity?: string;
      category?: string;
      periodFrom?: number;
      periodTo?: number;
      limit?: number;
      offset?: number;
    }
  ): Promise<ViolationsResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
    });
    if (options?.ruleId) params.append('rule_id', options.ruleId);
    if (options?.severity) params.append('severity', options.severity);
    if (options?.category) params.append('category', options.category);
    if (options?.periodFrom) params.append('period_from', options.periodFrom.toString());
    if (options?.periodTo) params.append('period_to', options.periodTo.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());

    return fetchApi(`/analysis/violations?${params}`);
  },

  getMLAnomalies: (
    fiscalYear: number,
    options?: {
      method?: string;
      minScore?: number;
      periodFrom?: number;
      periodTo?: number;
      limit?: number;
    }
  ): Promise<MLAnomaliesResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
    });
    if (options?.method) params.append('method', options.method);
    if (options?.minScore) params.append('min_score', options.minScore.toString());
    if (options?.periodFrom) params.append('period_from', options.periodFrom.toString());
    if (options?.periodTo) params.append('period_to', options.periodTo.toString());
    if (options?.limit) params.append('limit', options.limit.toString());

    return fetchApi(`/analysis/ml-anomalies?${params}`);
  },

  getRulesSummary: (fiscalYear: number): Promise<RulesSummaryResponse> => {
    return fetchApi(`/analysis/rules-summary?fiscal_year=${fiscalYear}`);
  },

  getBenfordDetail: (
    fiscalYear: number,
    account?: string
  ): Promise<{
    first_digit: BenfordDistribution[];
    second_digit: BenfordDistribution[];
    total_count: number;
    mad_first: number;
    mad_second: number;
    conformity: string;
    suspicious_accounts: Array<{
      account: string;
      total_count: number;
      digit_1_pct: number;
      expected_pct: number;
      deviation: number;
    }>;
  }> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
    });
    if (account) params.append('account', account);

    return fetchApi(`/analysis/benford-detail?${params}`);
  },

  // ---------------------------------------------------------------------------
  // Batch
  // ---------------------------------------------------------------------------
  startBatchJob: (request: BatchJobRequest): Promise<BatchJobResponse> => {
    return fetchApi('/batch/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  getBatchStatus: (jobId: string): Promise<BatchStatusResponse> => {
    return fetchApi(`/batch/status/${jobId}`);
  },

  getRecentJobs: (limit?: number): Promise<Array<Record<string, unknown>>> => {
    const params = limit ? `?limit=${limit}` : '';
    return fetchApi(`/batch/jobs${params}`);
  },

  runBatchSync: (request: BatchJobRequest): Promise<Record<string, unknown>> => {
    return fetchApi('/batch/run-sync', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // ---------------------------------------------------------------------------
  // Agents
  // ---------------------------------------------------------------------------
  askAgent: (query: string, context?: Record<string, unknown>): Promise<AgentResponse> => {
    return fetchApi('/agents/ask', {
      method: 'POST',
      body: JSON.stringify({ query, context }),
    });
  },

  runAnalysis: (fiscalYear: number, analysisType?: string): Promise<AgentResponse> => {
    return fetchApi('/agents/analyze', {
      method: 'POST',
      body: JSON.stringify({ fiscal_year: fiscalYear, analysis_type: analysisType }),
    });
  },

  runInvestigation: (target: string, fiscalYear: number): Promise<AgentResponse> => {
    return fetchApi('/agents/investigate', {
      method: 'POST',
      body: JSON.stringify({ target, fiscal_year: fiscalYear }),
    });
  },

  generateDocument: (
    docType: string,
    fiscalYear: number,
    findingType?: string
  ): Promise<AgentResponse> => {
    return fetchApi('/agents/document', {
      method: 'POST',
      body: JSON.stringify({
        document_type: docType,
        fiscal_year: fiscalYear,
        finding_type: findingType,
      }),
    });
  },

  routeRequest: (request: string): Promise<AgentResponse> => {
    return fetchApi('/agents/route', {
      method: 'POST',
      body: JSON.stringify({ request }),
    });
  },

  // ---------------------------------------------------------------------------
  // Reports
  // ---------------------------------------------------------------------------
  generateReport: (request: ReportRequest): Promise<Record<string, unknown>> => {
    return fetchApi('/reports/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  getReportTemplates: (): Promise<{ templates: ReportTemplate[] }> => {
    return fetchApi('/reports/templates');
  },

  getReportHistory: (
    fiscalYear?: number,
    limit?: number
  ): Promise<{ reports: Array<Record<string, unknown>>; total_count: number }> => {
    const params = new URLSearchParams();
    if (fiscalYear) params.append('fiscal_year', fiscalYear.toString());
    if (limit) params.append('limit', limit.toString());

    return fetchApi(`/reports/history?${params}`);
  },

  // ---------------------------------------------------------------------------
  // Rules
  // ---------------------------------------------------------------------------
  getRules: (category?: string): Promise<{ rules: AuditRule[]; total: number }> => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    return fetchApi(`/rules?${params}`);
  },

  getRuleCategories: (): Promise<{ categories: RuleCategoryInfo[] }> => {
    return fetchApi('/rules/categories');
  },

  updateRule: (
    ruleId: string,
    data: { is_enabled?: boolean; severity?: string; parameters?: Record<string, unknown> }
  ): Promise<AuditRule> => {
    return fetchApi(`/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  resetRule: (ruleId: string): Promise<AuditRule> => {
    return fetchApi(`/rules/${ruleId}/reset`, { method: 'POST' });
  },

  // ---------------------------------------------------------------------------
  // Period Comparison
  // ---------------------------------------------------------------------------
  getPeriodComparison: (
    fiscalYear: number,
    period: number,
    comparisonType: 'mom' | 'yoy' = 'mom',
    limit?: number
  ): Promise<PeriodComparisonResponse> => {
    const params = new URLSearchParams({
      fiscal_year: fiscalYear.toString(),
      period: period.toString(),
      comparison_type: comparisonType,
    });
    if (limit) params.append('limit', limit.toString());

    return fetchApi(`/dashboard/period-comparison?${params}`);
  },

  // ---------------------------------------------------------------------------
  // LLM Usage
  // ---------------------------------------------------------------------------
  getLLMUsageSummary: (days?: number): Promise<LLMUsageSummary> => {
    const params = days ? `?days=${days}` : '';
    return fetchApi(`/llm-usage/summary${params}`);
  },

  getLLMDailyUsage: (days?: number): Promise<LLMDailyResponse> => {
    const params = days ? `?days=${days}` : '';
    return fetchApi(`/llm-usage/daily${params}`);
  },
};

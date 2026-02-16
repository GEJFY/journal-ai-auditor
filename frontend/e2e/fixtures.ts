/**
 * E2E テスト共通フィクスチャ
 *
 * APIモックとページオブジェクトを提供する。
 * バックエンド不要でフロントエンドのみテスト可能。
 */

import { test as base, type Page } from '@playwright/test';

// ============================================================
// モックデータ定義
// ============================================================

export const MOCK_HEALTH = { status: 'healthy', app: 'JAIA', version: '0.2.0' };

export const MOCK_SUMMARY = {
  total_entries: 784824,
  total_amount: 15_200_000_000,
  total_journals: 98000,
  unique_accounts: 156,
  high_risk_count: 1200,
  medium_risk_count: 5400,
  low_risk_count: 778224,
  fiscal_year: 2024,
};

export const MOCK_KPI = {
  total_entries: 784824,
  total_amount: 15_200_000_000,
  total_journals: 98000,
  unique_accounts: 156,
  high_risk_count: 1200,
  avg_risk_score: 18.5,
  period_count: 12,
};

export const MOCK_TREND = Array.from({ length: 12 }, (_, i) => ({
  period: i + 1,
  fiscal_year: 2024,
  entry_count: 60000 + Math.floor(Math.random() * 10000),
  total_amount: 1_200_000_000 + Math.floor(Math.random() * 200_000_000),
  journal_count: 7500 + Math.floor(Math.random() * 1000),
}));

export const MOCK_RISK = {
  risk_distribution: { high: 1200, medium: 5400, low: 778224 },
  high_risk_items: [],
  medium_risk_items: [],
  low_risk_items: [],
  total_count: 784824,
};

export const MOCK_BENFORD = {
  distribution: Array.from({ length: 9 }, (_, i) => ({
    digit: i + 1,
    count: Math.floor(784824 * Math.log10(1 + 1 / (i + 1))),
    actual_pct: 0,
    expected_pct: Math.log10(1 + 1 / (i + 1)) * 100,
  })),
  mad: 0.004,
  conformity: 'close',
  total_count: 784824,
};

export const MOCK_PERIOD_COMPARISON = {
  comparison_type: 'mom',
  current_period: 6,
  previous_period: 5,
  fiscal_year: 2024,
  total_current: 1_300_000_000,
  total_previous: 1_200_000_000,
  items: [],
};

export const MOCK_SETTINGS = {
  settings: {
    fiscal_year_start: '04',
    llm_provider: 'anthropic',
    llm_model: 'claude-3-opus',
    theme: 'system',
  },
};

export const MOCK_RULES = [
  {
    rule_id: 'AMOUNT_001',
    rule_name: '高額取引検出',
    rule_name_en: 'Large Transaction Detection',
    category: 'AMOUNT',
    description: '閾値以上の取引を検出',
    severity: 'HIGH',
    is_enabled: true,
    parameters: '{"threshold": 10000000}',
  },
  {
    rule_id: 'TIME_001',
    rule_name: '営業時間外入力',
    rule_name_en: 'After-hours Entry',
    category: 'TIME',
    description: '営業時間外の仕訳入力を検出',
    severity: 'MEDIUM',
    is_enabled: true,
    parameters: '{"start_hour": 8, "end_hour": 20}',
  },
];

export const MOCK_LLM_USAGE = {
  total_requests: 42,
  total_input_tokens: 150000,
  total_output_tokens: 80000,
  total_cost_usd: 3.5,
  providers: { anthropic: { requests: 42, cost: 3.5 } },
};

// ============================================================
// APIモック設定
// ============================================================

async function setupApiMocks(page: Page) {
  const API = '**/api/v1/**';

  // Health check（/health は /api/v1 の外にある）
  await page.route('**/health', (route) => route.fulfill({ json: MOCK_HEALTH }));

  // Dashboard endpoints
  await page.route('**/api/v1/dashboard/summary*', (route) =>
    route.fulfill({ json: MOCK_SUMMARY })
  );
  await page.route('**/api/v1/dashboard/kpi*', (route) => route.fulfill({ json: MOCK_KPI }));
  await page.route('**/api/v1/dashboard/trend*', (route) => route.fulfill({ json: MOCK_TREND }));
  await page.route('**/api/v1/dashboard/risk*', (route) => route.fulfill({ json: MOCK_RISK }));
  await page.route('**/api/v1/dashboard/benford*', (route) =>
    route.fulfill({ json: MOCK_BENFORD })
  );
  await page.route('**/api/v1/dashboard/period-comparison*', (route) =>
    route.fulfill({ json: MOCK_PERIOD_COMPARISON })
  );

  // Settings
  await page.route('**/api/v1/settings*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: MOCK_SETTINGS });
    }
    return route.fulfill({ json: { status: 'ok' } });
  });

  // Rules
  await page.route('**/api/v1/rules*', (route) => route.fulfill({ json: MOCK_RULES }));

  // LLM usage
  await page.route('**/api/v1/llm-usage/**', (route) => route.fulfill({ json: MOCK_LLM_USAGE }));

  // Search (empty default)
  await page.route('**/api/v1/search*', (route) =>
    route.fulfill({ json: { items: [], total: 0, page: 1, per_page: 50 } })
  );

  // Catch-all for unhandled API calls
  await page.route(API, (route) => {
    const url = route.request().url();
    console.warn(`[E2E] Unhandled API call: ${url}`);
    return route.fulfill({ json: {}, status: 200 });
  });
}

// ============================================================
// カスタムテスト fixture
// ============================================================

export const test = base.extend<{ mockApi: void }>({
  mockApi: [
    async ({ page }, use) => {
      await setupApiMocks(page);
      await use();
    },
    { auto: true },
  ],
});

export { expect } from '@playwright/test';

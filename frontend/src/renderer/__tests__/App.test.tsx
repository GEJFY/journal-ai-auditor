/**
 * App Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock scrollIntoView (not implemented in jsdom)
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Mock recharts to avoid canvas rendering issues
vi.mock('recharts', () => ({
  AreaChart: ({ children }: any) => <div>{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  PieChart: ({ children }: any) => <div>{children}</div>,
  Pie: () => null,
  Cell: () => null,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: () => null,
}));

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    healthCheck: vi.fn().mockResolvedValue({ status: 'healthy' }),
    getDashboardSummary: vi.fn().mockResolvedValue({
      total_entries: 50000,
      total_amount: 1000000000,
      high_risk_count: 150,
      unique_users: 25,
      debit_total: 500000000,
      credit_total: 500000000,
      unique_accounts: 100,
      unique_journals: 5000,
      date_range: { from: '2024-04-01', to: '2025-03-31' },
      anomaly_count: 30,
    }),
    getTimeSeries: vi.fn().mockResolvedValue({ data: [], aggregation: 'monthly' }),
    getKPI: vi.fn().mockResolvedValue({
      fiscal_year: 2024,
      total_entries: 50000,
      total_journals: 5000,
      total_amount: 1000000000,
      unique_users: 25,
      unique_accounts: 100,
      high_risk_count: 150,
      high_risk_pct: 3.0,
      avg_risk_score: 25.5,
      self_approval_count: 10,
    }),
    getRiskAnalysis: vi.fn().mockResolvedValue({
      high_risk: [],
      medium_risk: [],
      low_risk: [],
      risk_distribution: { high: 5, medium: 15, low: 80, minimal: 100 },
    }),
    getBenford: vi.fn().mockResolvedValue({
      distribution: [],
      total_count: 0,
      mad: 0,
      conformity: 'close',
    }),
  },
}));

// Mock onboarding to skip it in tests
vi.mock('../components/onboarding/Onboarding', () => ({
  default: () => null,
  useOnboarding: () => ({ showOnboarding: false, completeOnboarding: vi.fn() }),
}));

import App from '../App';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(document.body).toBeTruthy();
  });

  it('renders navigation sidebar', () => {
    render(<App />);
    expect(screen.getByText('JAIA')).toBeTruthy();
  });

  it('renders dashboard by default', () => {
    render(<App />);
    expect(screen.getAllByText(/ダッシュボード/).length).toBeGreaterThanOrEqual(1);
  });
});

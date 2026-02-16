/**
 * DashboardPage Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock useFiscalYear hook
vi.mock('../lib/useFiscalYear', () => ({
  useFiscalYear: () => [2024, vi.fn()],
}));

// Mock the api module
vi.mock('../lib/api', () => ({
  api: {
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

// Mock HelpTooltip
vi.mock('../components/ui/HelpTooltip', () => ({
  default: ({ id }: { id: string }) => <span data-testid={`help-${id}`} />,
}));

// Mock recharts to avoid rendering issues in tests
vi.mock('recharts', () => ({
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
}));

import DashboardPage from '../pages/DashboardPage';

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('DashboardPage', () => {
  it('renders page header', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText(/ダッシュボード/)).toBeInTheDocument();
    });
  });

  it('renders stat cards section', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(document.querySelector('[class*="grid"]')).toBeTruthy();
    });
  });

  it('renders chart sections', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(document.querySelector('[class*="card"]')).toBeTruthy();
    });
  });
});

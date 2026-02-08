/**
 * DashboardPage Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the api module
vi.mock('../lib/api', () => ({
  api: {
    getDashboardSummary: vi.fn().mockResolvedValue({
      total_entries: 50000,
      total_amount: 1000000000,
      high_risk_count: 150,
      unique_users: 25,
    }),
    getDashboardTimeseries: vi.fn().mockResolvedValue([]),
    getDashboardRisk: vi.fn().mockResolvedValue([]),
    getDashboardBenford: vi.fn().mockResolvedValue({ actual: [], expected: [] }),
  },
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

function renderDashboard() {
  // Lazy import to ensure mocks are in place
  const DashboardPage = require('../pages/DashboardPage').default;
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
  it('renders page header', () => {
    renderDashboard();
    expect(screen.getByText(/ダッシュボード/)).toBeInTheDocument();
  });

  it('renders stat cards section', () => {
    renderDashboard();
    // The page should have a refresh or data-related element
    expect(document.querySelector('[class*="grid"]')).toBeTruthy();
  });

  it('renders chart sections', () => {
    renderDashboard();
    // Charts are mocked, but containers should exist
    expect(document.querySelector('[class*="card"]')).toBeTruthy();
  });
});

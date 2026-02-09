/**
 * RiskPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  AlertTriangle: (props: Record<string, unknown>) => (
    <span data-testid="icon-alert-triangle" {...props} />
  ),
  AlertCircle: (props: Record<string, unknown>) => (
    <span data-testid="icon-alert-circle" {...props} />
  ),
  Info: (props: Record<string, unknown>) => <span data-testid="icon-info" {...props} />,
  ChevronRight: (props: Record<string, unknown>) => <span data-testid="icon-chevron" {...props} />,
  Filter: (props: Record<string, unknown>) => <span data-testid="icon-filter" {...props} />,
}));

// Mock recharts
vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Cell: () => <div />,
}));

// Mock API - matches RiskResponse / ViolationsResponse schemas
vi.mock('../lib/api', () => ({
  api: {
    getRiskAnalysis: vi.fn().mockResolvedValue({
      risk_distribution: { high: 5, medium: 15, low: 80, minimal: 100 },
      high_risk: [],
      medium_risk: [],
      low_risk: [],
    }),
    getViolations: vi.fn().mockResolvedValue({
      violations: [],
      total_count: 20,
      by_severity: { high: 5, medium: 10, low: 5 },
      by_category: { amount: 8, time: 7, approval: 5 },
    }),
  },
}));

import RiskPage from '../pages/RiskPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('RiskPage', () => {
  it('renders page title', async () => {
    renderWithQuery(<RiskPage />);
    await waitFor(() => {
      expect(screen.getByText('リスク分析')).toBeTruthy();
    });
  });

  it('renders risk level filter buttons', async () => {
    renderWithQuery(<RiskPage />);
    await waitFor(() => {
      expect(screen.getByText('すべて')).toBeTruthy();
    });
    expect(screen.getByText('高')).toBeTruthy();
    expect(screen.getByText('中')).toBeTruthy();
    expect(screen.getByText('低')).toBeTruthy();
  });

  it('renders risk distribution section', async () => {
    renderWithQuery(<RiskPage />);
    await waitFor(() => {
      expect(screen.getByText('リスク分布')).toBeTruthy();
    });
  });

  it('renders violation summary section', async () => {
    renderWithQuery(<RiskPage />);
    await waitFor(() => {
      expect(screen.getByText('違反サマリー')).toBeTruthy();
    });
  });

  it('changes filter on button click', async () => {
    renderWithQuery(<RiskPage />);
    await waitFor(() => {
      expect(screen.getByText('高')).toBeTruthy();
    });
    const highButton = screen.getByText('高');
    fireEvent.click(highButton);
    expect(screen.getByText('リスク分析')).toBeTruthy();
  });

  it('shows loading state initially', () => {
    renderWithQuery(<RiskPage />);
    // Initially shows loading spinner before data resolves
    expect(document.querySelector('[class*="animate-spin"]')).toBeTruthy();
  });
});

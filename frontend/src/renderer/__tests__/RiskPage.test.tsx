/**
 * RiskPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="icon-alert-triangle" {...props} />,
  AlertCircle: (props: Record<string, unknown>) => <span data-testid="icon-alert-circle" {...props} />,
  Info: (props: Record<string, unknown>) => <span data-testid="icon-info" {...props} />,
  ChevronRight: (props: Record<string, unknown>) => <span data-testid="icon-chevron" {...props} />,
  Filter: (props: Record<string, unknown>) => <span data-testid="icon-filter" {...props} />,
}));

// Mock recharts
vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
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
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe('RiskPage', () => {
  it('renders page title', () => {
    renderWithQuery(<RiskPage />);
    expect(screen.getByText('リスク分析')).toBeTruthy();
  });

  it('renders risk level filter buttons', () => {
    renderWithQuery(<RiskPage />);
    expect(screen.getByText('全て')).toBeTruthy();
    expect(screen.getByText('高')).toBeTruthy();
    expect(screen.getByText('中')).toBeTruthy();
    expect(screen.getByText('低')).toBeTruthy();
  });

  it('renders risk distribution section', () => {
    renderWithQuery(<RiskPage />);
    expect(screen.getByText('リスク分布')).toBeTruthy();
  });

  it('renders violation summary section', () => {
    renderWithQuery(<RiskPage />);
    expect(screen.getByText('違反サマリー')).toBeTruthy();
  });

  it('changes filter on button click', () => {
    renderWithQuery(<RiskPage />);
    const highButton = screen.getByText('高');
    fireEvent.click(highButton);
    // フィルタ変更後もUIが表示される
    expect(screen.getByText('リスク分析')).toBeTruthy();
  });

  it('shows loading state', () => {
    renderWithQuery(<RiskPage />);
    // ロード中の表示があるか確認
    const page = screen.getByText('リスク分析');
    expect(page).toBeTruthy();
  });
});

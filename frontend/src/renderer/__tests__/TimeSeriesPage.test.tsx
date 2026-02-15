/**
 * TimeSeriesPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  TrendingUp: (props: Record<string, unknown>) => <span data-testid="icon-trending-up" {...props} />,
  Calendar: (props: Record<string, unknown>) => <span data-testid="icon-calendar" {...props} />,
  BarChart3: (props: Record<string, unknown>) => <span data-testid="icon-bar-chart" {...props} />,
  RefreshCw: (props: Record<string, unknown>) => <span data-testid="icon-refresh" {...props} />,
  ArrowUpRight: (props: Record<string, unknown>) => (
    <span data-testid="icon-arrow-up" {...props} />
  ),
  ArrowDownRight: (props: Record<string, unknown>) => (
    <span data-testid="icon-arrow-down" {...props} />
  ),
}));

// Mock recharts
vi.mock('recharts', () => ({
  AreaChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => <div />,
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div />,
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Legend: () => <div />,
}));

// Mock clsx
vi.mock('clsx', () => ({
  default: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    getTimeSeries: vi.fn().mockResolvedValue({
      data: [
        { date: '2024-01-01', amount: 1000000, count: 50, debit: 600000, credit: 400000 },
        { date: '2024-02-01', amount: 1200000, count: 60, debit: 700000, credit: 500000 },
        { date: '2024-03-01', amount: 900000, count: 45, debit: 500000, credit: 400000 },
      ],
    }),
  },
}));

import TimeSeriesPage from '../pages/TimeSeriesPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('TimeSeriesPage', () => {
  it('renders page title', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('2024年度 時系列分析')).toBeTruthy();
    });
  });

  it('renders aggregation toggles', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('月次')).toBeTruthy();
    });
    expect(screen.getByText('週次')).toBeTruthy();
    expect(screen.getByText('日次')).toBeTruthy();
  });

  it('renders chart type toggles', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('エリア')).toBeTruthy();
    });
    expect(screen.getByText('棒')).toBeTruthy();
    expect(screen.getByText('折線')).toBeTruthy();
  });

  it('renders trend chart section', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('トレンドチャート')).toBeTruthy();
    });
  });

  it('renders period stats when data is available', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('最新期間の金額')).toBeTruthy();
    });
    expect(screen.getByText('最新期間の件数')).toBeTruthy();
    expect(screen.getByText('期間合計金額')).toBeTruthy();
    expect(screen.getByText('期間合計件数')).toBeTruthy();
  });

  it('renders debit/credit breakdown section', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('借方・貸方の推移')).toBeTruthy();
    });
  });

  it('switches chart type on toggle click', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('棒')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('棒'));
    // Both the main chart and debit/credit breakdown chart render as BarChart
    const barCharts = screen.getAllByTestId('bar-chart');
    expect(barCharts.length).toBeGreaterThanOrEqual(2);
  });

  it('switches to line chart', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('折線')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('折線'));
    expect(screen.getByTestId('line-chart')).toBeTruthy();
  });

  it('renders refresh button', async () => {
    renderWithQuery(<TimeSeriesPage />);
    await waitFor(() => {
      expect(screen.getByText('更新')).toBeTruthy();
    });
  });
});

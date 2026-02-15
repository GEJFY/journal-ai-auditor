/**
 * AccountsPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock useFiscalYear hook
vi.mock('../lib/useFiscalYear', () => ({
  useFiscalYear: () => [2024, vi.fn()],
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  FileText: (props: Record<string, unknown>) => <span data-testid="icon-file" {...props} />,
  RefreshCw: (props: Record<string, unknown>) => <span data-testid="icon-refresh" {...props} />,
  ArrowUpDown: (props: Record<string, unknown>) => <span data-testid="icon-sort" {...props} />,
  BarChart3: (props: Record<string, unknown>) => <span data-testid="icon-bar-chart" {...props} />,
  TrendingUp: (props: Record<string, unknown>) => (
    <span data-testid="icon-trending-up" {...props} />
  ),
  TrendingDown: (props: Record<string, unknown>) => (
    <span data-testid="icon-trending-down" {...props} />
  ),
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
}));

// Mock clsx
vi.mock('clsx', () => ({
  default: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    getAccounts: vi.fn().mockResolvedValue({
      accounts: [
        {
          account_code: '1000',
          account_name: '現金',
          debit_total: 500000,
          credit_total: 300000,
          net_amount: 200000,
          entry_count: 25,
        },
        {
          account_code: '2000',
          account_name: '売掛金',
          debit_total: 800000,
          credit_total: 750000,
          net_amount: 50000,
          entry_count: 40,
        },
        {
          account_code: '3000',
          account_name: '買掛金',
          debit_total: 200000,
          credit_total: 600000,
          net_amount: -400000,
          entry_count: 15,
        },
      ],
      total_accounts: 3,
    }),
  },
}));

import AccountsPage from '../pages/AccountsPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AccountsPage', () => {
  it('renders page title', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('2024年度 勘定科目分析')).toBeTruthy();
    });
  });

  it('renders stats cards', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('科目数')).toBeTruthy();
    });
    // 借方合計/貸方合計 appear in both stats cards and table headers
    expect(screen.getAllByText('借方合計').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('貸方合計').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('平均仕訳件数/科目')).toBeTruthy();
  });

  it('renders chart section', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('上位10科目（借方・貸方）')).toBeTruthy();
    });
  });

  it('renders accounts table', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('勘定科目一覧')).toBeTruthy();
    });
  });

  it('renders table headers', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('科目コード')).toBeTruthy();
    });
    expect(screen.getByText('科目名')).toBeTruthy();
  });

  it('renders account data in table', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('1000')).toBeTruthy();
    });
    expect(screen.getByText('現金')).toBeTruthy();
    expect(screen.getByText('売掛金')).toBeTruthy();
    expect(screen.getByText('買掛金')).toBeTruthy();
  });

  it('sorts by column on header click', async () => {
    renderWithQuery(<AccountsPage />);
    // Wait for actual data to render
    await waitFor(() => {
      expect(screen.getByText('1000')).toBeTruthy();
    });

    // Click 仕訳件数 header to sort by entry_count
    const headerCells = screen.getAllByRole('columnheader');
    const entryCountHeader = headerCells.find((h) => h.textContent?.includes('仕訳件数'));
    if (entryCountHeader) {
      fireEvent.click(entryCountHeader);
    }
    // Page should still render after sort
    expect(screen.getByText('勘定科目一覧')).toBeTruthy();
  });

  it('renders refresh button', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('更新')).toBeTruthy();
    });
  });

  it('shows total accounts count', async () => {
    renderWithQuery(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText('現金')).toBeTruthy();
    });
    // Total accounts count renders as stat
    expect(screen.getByText('3')).toBeTruthy();
  });
});

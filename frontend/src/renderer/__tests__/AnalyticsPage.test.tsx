/**
 * AnalyticsPage Component Tests
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
  Building2: (props: Record<string, unknown>) => <span data-testid="icon-building2" {...props} />,
  Users: (props: Record<string, unknown>) => <span data-testid="icon-users" {...props} />,
  ArrowRightLeft: (props: Record<string, unknown>) => (
    <span data-testid="icon-arrow-right-left" {...props} />
  ),
  AlertTriangle: (props: Record<string, unknown>) => (
    <span data-testid="icon-alert-triangle" {...props} />
  ),
  Loader2: (props: Record<string, unknown>) => <span data-testid="icon-loader2" {...props} />,
  TrendingUp: (props: Record<string, unknown>) => (
    <span data-testid="icon-trending-up" {...props} />
  ),
  TrendingDown: (props: Record<string, unknown>) => (
    <span data-testid="icon-trending-down" {...props} />
  ),
}));

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    getDepartments: vi.fn().mockResolvedValue({
      departments: [
        {
          dept_code: 'D001',
          entry_count: 150,
          total_debit: 5000000,
          total_credit: 4800000,
          avg_risk_score: 35.2,
          high_risk_count: 3,
          self_approval_rate: 5.0,
        },
      ],
      total: 1,
    }),
    getVendors: vi.fn().mockResolvedValue({
      vendors: [
        {
          vendor_code: 'V001',
          entry_count: 80,
          total_amount: 3000000,
          avg_amount: 37500,
          max_amount: 500000,
          avg_risk_score: 42.1,
          concentration_pct: 15.3,
          high_risk_count: 2,
        },
      ],
      total: 1,
    }),
    getAccountFlow: vi.fn().mockResolvedValue({
      flows: [
        {
          source_account: '1100',
          target_account: '5100',
          transaction_count: 45,
          flow_amount: 2000000,
          avg_amount: 44444,
        },
      ],
      total: 1,
    }),
  },
}));

import AnalyticsPage from '../pages/AnalyticsPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AnalyticsPage', () => {
  it('renders page title and description', async () => {
    renderWithQuery(<AnalyticsPage />);
    expect(screen.getByText('詳細分析')).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText(/2024年度の部門・取引先・勘定科目フロー分析/)).toBeTruthy();
    });
  });

  it('renders three tab buttons', () => {
    renderWithQuery(<AnalyticsPage />);
    expect(screen.getByText('部門分析')).toBeTruthy();
    expect(screen.getByText('取引先分析')).toBeTruthy();
    expect(screen.getByText('勘定科目フロー')).toBeTruthy();
  });

  it('shows departments tab content by default', async () => {
    renderWithQuery(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('部門コード')).toBeTruthy();
    });
    expect(screen.getByText('D001')).toBeTruthy();
    expect(screen.getByText('150')).toBeTruthy();
  });

  it('switches to vendors tab on click', async () => {
    renderWithQuery(<AnalyticsPage />);
    fireEvent.click(screen.getByText('取引先分析'));
    await waitFor(() => {
      expect(screen.getByText('取引先コード')).toBeTruthy();
    });
    expect(screen.getByText('V001')).toBeTruthy();
  });

  it('switches to account flow tab on click', async () => {
    renderWithQuery(<AnalyticsPage />);
    fireEvent.click(screen.getByText('勘定科目フロー'));
    await waitFor(() => {
      expect(screen.getByText('借方勘定')).toBeTruthy();
    });
    expect(screen.getByText('1100')).toBeTruthy();
    expect(screen.getByText('5100')).toBeTruthy();
  });

  it('shows department table headers', async () => {
    renderWithQuery(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('仕訳件数')).toBeTruthy();
    });
    expect(screen.getByText('借方合計')).toBeTruthy();
    expect(screen.getByText('貸方合計')).toBeTruthy();
    expect(screen.getByText('平均リスク')).toBeTruthy();
    expect(screen.getByText('高リスク件数')).toBeTruthy();
    expect(screen.getByText('自己承認率')).toBeTruthy();
  });

  it('shows department total count footer', async () => {
    renderWithQuery(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('1 部門')).toBeTruthy();
    });
  });

  it('renders risk badge with correct score', async () => {
    renderWithQuery(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('35.2')).toBeTruthy();
    });
  });
});

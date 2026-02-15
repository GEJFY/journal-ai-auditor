/**
 * SearchPage Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock useFiscalYear hook
vi.mock('../lib/useFiscalYear', () => ({
  useFiscalYear: () => [2024, vi.fn()],
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Search: (props: Record<string, unknown>) => <span data-testid="icon-search" {...props} />,
  Filter: (props: Record<string, unknown>) => <span data-testid="icon-filter" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => (
    <span data-testid="icon-chevron-down" {...props} />
  ),
  ChevronUp: (props: Record<string, unknown>) => <span data-testid="icon-chevron-up" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="icon-alert" {...props} />,
  FileText: (props: Record<string, unknown>) => <span data-testid="icon-file" {...props} />,
  Download: (props: Record<string, unknown>) => <span data-testid="icon-download" {...props} />,
}));

// Mock API
vi.mock('../lib/api', () => ({
  API_BASE: 'http://localhost:8090/api/v1',
}));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

import SearchPage from '../pages/SearchPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe('SearchPage', () => {
  it('renders search form', () => {
    renderWithQuery(<SearchPage />);
    expect(screen.getByText('仕訳検索')).toBeTruthy();
    expect(screen.getByPlaceholderText('仕訳ID、摘要、勘定科目コードで検索...')).toBeTruthy();
  });

  it('renders search and reset buttons', () => {
    renderWithQuery(<SearchPage />);
    const buttons = screen.getAllByRole('button');
    const searchButton = buttons.find((b) => b.textContent?.trim() === '検索');
    expect(searchButton).toBeTruthy();
    expect(screen.getByText('リセット')).toBeTruthy();
  });

  it('shows initial state before search', () => {
    renderWithQuery(<SearchPage />);
    expect(screen.getByText('検索条件を入力して仕訳データを検索してください')).toBeTruthy();
  });

  it('toggles advanced filters', () => {
    renderWithQuery(<SearchPage />);
    const toggleButton = screen.getByText('詳細フィルター');
    fireEvent.click(toggleButton);
    expect(screen.getByText('勘定科目')).toBeTruthy();
    expect(screen.getByText('日付（開始）')).toBeTruthy();
    expect(screen.getByText('日付（終了）')).toBeTruthy();
    expect(screen.getByText('起票者')).toBeTruthy();
    expect(screen.getByText('金額（下限）')).toBeTruthy();
    expect(screen.getByText('金額（上限）')).toBeTruthy();
    expect(screen.getByText('リスクスコア（最小）')).toBeTruthy();
  });

  it('submits search and shows results', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          entries: [
            {
              gl_detail_id: '1',
              journal_id: 'JE001',
              effective_date: '2024-01-15',
              gl_account_number: '1000',
              account_name: '現金',
              amount: 50000,
              debit_credit_indicator: 'D',
              description: 'テスト仕訳',
              prepared_by: 'user1',
              approved_by: 'admin',
              risk_score: 75,
            },
          ],
          total_count: 1,
          page: 0,
          page_size: 50,
        }),
    });

    renderWithQuery(<SearchPage />);
    const input = screen.getByPlaceholderText('仕訳ID、摘要、勘定科目コードで検索...');
    fireEvent.change(input, { target: { value: 'JE001' } });
    const form = input.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText('JE001')).toBeTruthy();
    });
    expect(screen.getByText('検索結果')).toBeTruthy();
    expect(screen.getByText('テスト仕訳')).toBeTruthy();
  });

  it('shows empty results message', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          entries: [],
          total_count: 0,
          page: 0,
          page_size: 50,
        }),
    });

    renderWithQuery(<SearchPage />);
    const input = screen.getByPlaceholderText('仕訳ID、摘要、勘定科目コードで検索...');
    const form = input.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText('該当する仕訳がありません')).toBeTruthy();
    });
  });

  it('resets filters on reset button click', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ entries: [], total_count: 0, page: 0, page_size: 50 }),
    });

    renderWithQuery(<SearchPage />);
    const input = screen.getByPlaceholderText('仕訳ID、摘要、勘定科目コードで検索...');
    fireEvent.change(input, { target: { value: 'test' } });
    const form = input.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText('該当する仕訳がありません')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('リセット'));
    expect(screen.getByText('検索条件を入力して仕訳データを検索してください')).toBeTruthy();
  });
});

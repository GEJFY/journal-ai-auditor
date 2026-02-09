/**
 * ReportsPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  FileText: (props: Record<string, unknown>) => <span data-testid="icon-file-text" {...props} />,
  Download: (props: Record<string, unknown>) => <span data-testid="icon-download" {...props} />,
  Eye: (props: Record<string, unknown>) => <span data-testid="icon-eye" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="icon-loader" {...props} />,
  CheckCircle: (props: Record<string, unknown>) => <span data-testid="icon-check" {...props} />,
  AlertCircle: (props: Record<string, unknown>) => <span data-testid="icon-alert" {...props} />,
  FileSpreadsheet: (props: Record<string, unknown>) => (
    <span data-testid="icon-spreadsheet" {...props} />
  ),
  FileBarChart: (props: Record<string, unknown>) => <span data-testid="icon-bar" {...props} />,
  ClipboardList: (props: Record<string, unknown>) => (
    <span data-testid="icon-clipboard" {...props} />
  ),
  Shield: (props: Record<string, unknown>) => <span data-testid="icon-shield" {...props} />,
  BarChart3: (props: Record<string, unknown>) => <span data-testid="icon-barchart3" {...props} />,
}));

// Mock API - getReportTemplates returns { templates: [...] } wrapper
vi.mock('../lib/api', () => ({
  api: {
    getReportTemplates: vi.fn().mockResolvedValue({
      templates: [
        { id: 'summary', name: 'サマリーレポート', description: '概要レポート' },
        { id: 'detailed', name: '詳細レポート', description: '詳細分析レポート' },
        { id: 'executive', name: 'エグゼクティブレポート', description: '経営向け報告' },
        { id: 'violations', name: '違反レポート', description: 'ルール違反一覧' },
        { id: 'risk', name: 'リスクレポート', description: 'リスク分析' },
        { id: 'benford', name: 'ベンフォードレポート', description: 'ベンフォード分析' },
        { id: 'working_paper', name: '調書', description: '監査調書' },
      ],
    }),
    generateReport: vi.fn().mockResolvedValue({
      id: 'test-report',
      type: 'summary',
      data: { total: 100 },
    }),
  },
}));

import ReportsPage from '../pages/ReportsPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('ReportsPage', () => {
  it('renders page title', async () => {
    renderWithQuery(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText('レポート生成')).toBeTruthy();
    });
  });

  it('renders report template section', async () => {
    renderWithQuery(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getAllByText(/テンプレート|レポート種類/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders generated reports section', async () => {
    renderWithQuery(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText(/生成されたレポート/)).toBeTruthy();
    });
  });

  it('shows empty state when no reports generated', async () => {
    renderWithQuery(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText(/テンプレートをクリック/)).toBeTruthy();
    });
  });

  it('renders page content', async () => {
    renderWithQuery(<ReportsPage />);
    await waitFor(() => {
      const page = document.body;
      expect(page.textContent).toContain('レポート');
    });
  });
});

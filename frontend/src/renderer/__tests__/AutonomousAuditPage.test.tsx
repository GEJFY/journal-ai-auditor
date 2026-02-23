/**
 * AutonomousAuditPage Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock useFiscalYear hook
vi.mock('../lib/useFiscalYear', () => ({
  useFiscalYear: () => [2024, vi.fn()],
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Brain: (props: Record<string, unknown>) => <span data-testid="icon-brain" {...props} />,
  Play: (props: Record<string, unknown>) => <span data-testid="icon-play" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="icon-loader" {...props} />,
  CheckCircle2: (props: Record<string, unknown>) => <span data-testid="icon-check" {...props} />,
  XCircle: (props: Record<string, unknown>) => <span data-testid="icon-xcircle" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="icon-alert" {...props} />,
  ChevronRight: (props: Record<string, unknown>) => <span data-testid="icon-chevron" {...props} />,
  Eye: (props: Record<string, unknown>) => <span data-testid="icon-eye" {...props} />,
  Lightbulb: (props: Record<string, unknown>) => <span data-testid="icon-lightbulb" {...props} />,
  Search: (props: Record<string, unknown>) => <span data-testid="icon-search" {...props} />,
  ShieldCheck: (props: Record<string, unknown>) => <span data-testid="icon-shield" {...props} />,
  FileText: (props: Record<string, unknown>) => <span data-testid="icon-file" {...props} />,
  Clock: (props: Record<string, unknown>) => <span data-testid="icon-clock" {...props} />,
}));

// Mock API
vi.mock('../lib/api', () => ({
  streamSSE: vi.fn(),
  api: {
    listAuditSessions: vi.fn().mockResolvedValue([]),
    getAuditReport: vi.fn().mockResolvedValue({
      session_id: 'test-session',
      fiscal_year: 2024,
      executive_summary: '',
      insights: [],
      hypotheses: [],
      total_tool_calls: 0,
    }),
  },
}));

import AutonomousAuditPage from '../pages/AutonomousAuditPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AutonomousAuditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(screen.getByText('AI自律監査')).toBeTruthy();
  });

  it('renders page description', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(
      screen.getByText('AIエージェントが自律的に仕訳データを分析し、監査インサイトを生成します')
    ).toBeTruthy();
  });

  it('renders start button', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(screen.getByText('分析開始')).toBeTruthy();
  });

  it('renders auto-approve checkbox', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(screen.getByText('自動承認')).toBeTruthy();
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeTruthy();
    expect((checkbox as HTMLInputElement).checked).toBe(true);
  });

  it('renders 5 phase labels', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(screen.getByText('観察')).toBeTruthy();
    expect(screen.getByText('仮説生成')).toBeTruthy();
    expect(screen.getByText('探索')).toBeTruthy();
    expect(screen.getByText('検証')).toBeTruthy();
    expect(screen.getByText('統合')).toBeTruthy();
  });

  it('renders tab buttons', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(screen.getByText('ログ')).toBeTruthy();
    expect(screen.getByText('仮説')).toBeTruthy();
    expect(screen.getByText('インサイト')).toBeTruthy();
    expect(screen.getByText('サマリー')).toBeTruthy();
  });

  it('shows empty log message initially', () => {
    renderWithQuery(<AutonomousAuditPage />);
    expect(screen.getByText('分析を開始するとログが表示されます')).toBeTruthy();
  });

  it('switches to hypotheses tab and shows empty message', () => {
    renderWithQuery(<AutonomousAuditPage />);
    fireEvent.click(screen.getByText('仮説'));
    expect(screen.getByText('仮説はまだ生成されていません')).toBeTruthy();
  });

  it('switches to insights tab and shows empty message', () => {
    renderWithQuery(<AutonomousAuditPage />);
    fireEvent.click(screen.getByText('インサイト'));
    expect(screen.getByText('インサイトはまだ生成されていません')).toBeTruthy();
  });

  it('switches to summary tab and shows empty message', () => {
    renderWithQuery(<AutonomousAuditPage />);
    fireEvent.click(screen.getByText('サマリー'));
    expect(screen.getByText('分析完了後にエグゼクティブサマリーが表示されます')).toBeTruthy();
  });

  it('toggles auto-approve checkbox', () => {
    renderWithQuery(<AutonomousAuditPage />);
    const checkbox = screen.getByRole('checkbox');
    expect((checkbox as HTMLInputElement).checked).toBe(true);
    fireEvent.click(checkbox);
    expect((checkbox as HTMLInputElement).checked).toBe(false);
  });
});

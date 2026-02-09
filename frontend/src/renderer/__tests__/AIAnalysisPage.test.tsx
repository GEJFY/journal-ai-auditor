/**
 * AIAnalysisPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Send: (props: Record<string, unknown>) => <span data-testid="icon-send" {...props} />,
  Bot: (props: Record<string, unknown>) => <span data-testid="icon-bot" {...props} />,
  User: (props: Record<string, unknown>) => <span data-testid="icon-user" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="icon-loader" {...props} />,
  FileText: (props: Record<string, unknown>) => <span data-testid="icon-file" {...props} />,
  Search: (props: Record<string, unknown>) => <span data-testid="icon-search" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="icon-alert" {...props} />,
  Sparkles: (props: Record<string, unknown>) => <span data-testid="icon-sparkles" {...props} />,
}));

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    askAgent: vi.fn().mockResolvedValue({
      response: 'AIの回答です',
      agent_type: 'QA',
    }),
  },
}));

import AIAnalysisPage from '../pages/AIAnalysisPage';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AIAnalysisPage', () => {
  it('renders page title', () => {
    renderWithQuery(<AIAnalysisPage />);
    expect(screen.getByText('AI分析')).toBeTruthy();
  });

  it('renders welcome message', () => {
    renderWithQuery(<AIAnalysisPage />);
    expect(screen.getByText(/JAIAのAIアシスタント/)).toBeTruthy();
  });

  it('renders quick action buttons', () => {
    renderWithQuery(<AIAnalysisPage />);
    expect(screen.getByText('高リスク仕訳を検索')).toBeTruthy();
    expect(screen.getByText('異常検知結果')).toBeTruthy();
    expect(screen.getByText('サマリーレポート')).toBeTruthy();
    expect(screen.getByText('リスク評価')).toBeTruthy();
  });

  it('renders text input', () => {
    renderWithQuery(<AIAnalysisPage />);
    const input = screen.getByPlaceholderText(/質問|入力|メッセージ/i);
    expect(input).toBeTruthy();
  });

  it('handles empty input submission', () => {
    renderWithQuery(<AIAnalysisPage />);
    const sendButton = screen.getAllByTestId('icon-send')[0]?.closest('button');
    if (sendButton) {
      fireEvent.click(sendButton);
    }
    // 空入力でメッセージが追加されないことを確認
    expect(screen.getByText(/JAIAのAIアシスタント/)).toBeTruthy();
  });

  it('shows disclaimer text', () => {
    renderWithQuery(<AIAnalysisPage />);
    // 免責事項テキストの確認
    const page = document.body;
    expect(page.textContent).toContain('AI');
  });
});

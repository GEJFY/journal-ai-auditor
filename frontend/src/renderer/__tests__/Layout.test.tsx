/**
 * Layout Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  LayoutDashboard: () => <span data-testid="icon-dashboard" />,
  Upload: () => <span data-testid="icon-upload" />,
  Settings: () => <span data-testid="icon-settings" />,
  Activity: () => <span data-testid="icon-activity" />,
  FileText: () => <span data-testid="icon-filetext" />,
  Search: () => <span data-testid="icon-search" />,
  TrendingUp: () => <span data-testid="icon-trending" />,
  Shield: () => <span data-testid="icon-shield" />,
  Bot: () => <span data-testid="icon-bot" />,
  ClipboardList: () => <span data-testid="icon-clipboard" />,
  HelpCircle: () => <span data-testid="icon-help" />,
  ChevronDown: () => <span data-testid="icon-chevron" />,
  Bell: () => <span data-testid="icon-bell" />,
  User: () => <span data-testid="icon-user" />,
}));

// Mock clsx
vi.mock('clsx', () => ({
  default: (...args: any[]) => args.filter(Boolean).join(' '),
}));

function renderLayout(path = '/') {
  const Layout = require('../components/Layout').default;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Layout isConnected={true}>
        <div data-testid="child-content">テストコンテンツ</div>
      </Layout>
    </MemoryRouter>
  );
}

describe('Layout', () => {
  it('renders JAIA logo and title', () => {
    renderLayout();
    expect(screen.getByText('JAIA')).toBeInTheDocument();
    expect(screen.getByText('Journal Entry Analyzer')).toBeInTheDocument();
  });

  it('renders navigation groups', () => {
    renderLayout();
    expect(screen.getByText('概要')).toBeInTheDocument();
    expect(screen.getByText('データ管理')).toBeInTheDocument();
    expect(screen.getByText('分析')).toBeInTheDocument();
    expect(screen.getByText('レポート')).toBeInTheDocument();
  });

  it('renders navigation items', () => {
    renderLayout();
    expect(screen.getByText('ダッシュボード')).toBeInTheDocument();
    expect(screen.getByText('データ取込')).toBeInTheDocument();
    expect(screen.getByText('仕訳検索')).toBeInTheDocument();
    expect(screen.getByText('リスク分析')).toBeInTheDocument();
    expect(screen.getByText('時系列分析')).toBeInTheDocument();
    expect(screen.getByText('勘定科目分析')).toBeInTheDocument();
    expect(screen.getByText('AI分析')).toBeInTheDocument();
    expect(screen.getByText('レポート生成')).toBeInTheDocument();
  });

  it('renders settings nav item', () => {
    renderLayout();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('renders child content', () => {
    renderLayout();
    expect(screen.getByTestId('child-content')).toBeInTheDocument();
    expect(screen.getByText('テストコンテンツ')).toBeInTheDocument();
  });

  it('shows connected status', () => {
    renderLayout();
    expect(screen.getByText('接続中')).toBeInTheDocument();
  });

  it('shows disconnected status', () => {
    const Layout = require('../components/Layout').default;
    render(
      <MemoryRouter>
        <Layout isConnected={false}>
          <div>test</div>
        </Layout>
      </MemoryRouter>
    );
    expect(screen.getByText('未接続')).toBeInTheDocument();
  });

  it('shows version number', () => {
    renderLayout();
    expect(screen.getByText('v0.1.0')).toBeInTheDocument();
  });

  it('renders header with current page title', () => {
    renderLayout('/');
    // Dashboard is the active page at '/'
    const headers = screen.getAllByText('ダッシュボード');
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it('toggles help panel', () => {
    renderLayout();
    // Help panel should not be visible initially
    expect(screen.queryByText('ヘルプ')).not.toBeInTheDocument();

    // Click help button
    const helpButton = screen.getByTitle('ヘルプ');
    fireEvent.click(helpButton);

    // Help panel should be visible
    expect(screen.getByText('クイックスタート')).toBeInTheDocument();
    expect(screen.getByText('サポート')).toBeInTheDocument();
  });

  it('renders notification bell', () => {
    renderLayout();
    expect(screen.getByTitle('通知')).toBeInTheDocument();
  });
});

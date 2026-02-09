/**
 * Main Layout Component
 *
 * Professional consulting-style application shell with categorized navigation.
 */

import { Link, useLocation } from 'react-router-dom';
import { ReactNode, useState } from 'react';
import {
  LayoutDashboard,
  Upload,
  Settings,
  Activity,
  FileText,
  Search,
  TrendingUp,
  Shield,
  Bot,
  ClipboardList,
  HelpCircle,
  ChevronDown,
  Bell,
  User,
} from 'lucide-react';
import clsx from 'clsx';

interface LayoutProps {
  children: ReactNode;
  isConnected: boolean;
}

interface NavItem {
  path: string;
  label: string;
  icon: ReactNode;
  description?: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: '概要',
    items: [
      {
        path: '/',
        label: 'ダッシュボード',
        icon: <LayoutDashboard size={20} />,
        description: '全体の分析状況を確認',
      },
    ],
  },
  {
    label: 'データ管理',
    items: [
      {
        path: '/import',
        label: 'データ取込',
        icon: <Upload size={20} />,
        description: '仕訳データをインポート',
      },
      {
        path: '/search',
        label: '仕訳検索',
        icon: <Search size={20} />,
        description: '仕訳データを検索',
      },
    ],
  },
  {
    label: '分析',
    items: [
      {
        path: '/risk',
        label: 'リスク分析',
        icon: <Shield size={20} />,
        description: 'リスクスコアと違反一覧',
      },
      {
        path: '/timeseries',
        label: '時系列分析',
        icon: <TrendingUp size={20} />,
        description: '月次・期間トレンド分析',
      },
      {
        path: '/accounts',
        label: '勘定科目分析',
        icon: <FileText size={20} />,
        description: '勘定科目別の分析',
      },
      {
        path: '/ai-analysis',
        label: 'AI分析',
        icon: <Bot size={20} />,
        description: 'AIによる自動分析',
      },
    ],
  },
  {
    label: 'レポート',
    items: [
      {
        path: '/reports',
        label: 'レポート生成',
        icon: <ClipboardList size={20} />,
        description: '監査レポートを作成',
      },
    ],
  },
];

const bottomNavItems: NavItem[] = [
  { path: '/settings', label: '設定', icon: <Settings size={20} /> },
];

export default function Layout({ children, isConnected }: LayoutProps) {
  const location = useLocation();
  const [showHelp, setShowHelp] = useState(false);

  // Find current page info
  const currentPage =
    navGroups.flatMap((g) => g.items).find((item) => item.path === location.pathname) ||
    bottomNavItems.find((item) => item.path === location.pathname);

  return (
    <div className="flex h-screen bg-neutral-50">
      {/* Sidebar */}
      <aside className="w-[280px] bg-white border-r border-neutral-200 flex flex-col shadow-nav">
        {/* Logo */}
        <div className="h-header flex items-center px-6 border-b border-neutral-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-brand rounded-xl flex items-center justify-center shadow-sm">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-primary-900 tracking-tight">JAIA</span>
              <p className="text-[10px] text-neutral-400 font-medium tracking-wide">
                Journal Entry Analyzer
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-5 space-y-6 overflow-y-auto scrollbar-thin">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="nav-group-label mb-2">{group.label}</div>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={clsx(
                      'nav-item group',
                      location.pathname === item.path && 'nav-item-active'
                    )}
                    title={item.description}
                  >
                    <span
                      className={clsx(
                        'transition-colors',
                        location.pathname === item.path
                          ? 'text-primary-700'
                          : 'text-neutral-400 group-hover:text-neutral-600'
                      )}
                    >
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom Navigation */}
        <div className="px-4 py-3 border-t border-neutral-100">
          {bottomNavItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={clsx('nav-item', location.pathname === item.path && 'nav-item-active')}
            >
              <span
                className={clsx(
                  'transition-colors',
                  location.pathname === item.path ? 'text-primary-700' : 'text-neutral-400'
                )}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
            </Link>
          ))}
        </div>

        {/* Status */}
        <div className="px-5 py-4 border-t border-neutral-100 bg-neutral-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className={clsx(
                  'w-2.5 h-2.5 rounded-full ring-2 ring-offset-1',
                  isConnected ? 'bg-green-500 ring-green-200' : 'bg-red-500 ring-red-200'
                )}
              />
              <span className="text-xs font-medium text-neutral-500">
                {isConnected ? '接続中' : '未接続'}
              </span>
            </div>
            <span className="text-[10px] text-neutral-400">v0.1.0</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-header bg-white border-b border-neutral-200 flex items-center justify-between px-8 shadow-nav">
          <div>
            <h1 className="text-xl font-semibold text-neutral-900">
              {currentPage?.label || 'JAIA'}
            </h1>
            {currentPage?.description && (
              <p className="text-sm text-neutral-500 mt-0.5">{currentPage.description}</p>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Help Button */}
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="btn-ghost btn-sm rounded-full p-2"
              title="ヘルプ"
            >
              <HelpCircle size={20} className="text-neutral-500" />
            </button>

            {/* Notifications */}
            <button className="btn-ghost btn-sm rounded-full p-2 relative" title="通知">
              <Bell size={20} className="text-neutral-500" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-accent-500 rounded-full" />
            </button>

            {/* User Menu */}
            <button className="flex items-center gap-2 btn-ghost btn-sm rounded-full pl-2 pr-3">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <User size={16} className="text-primary-700" />
              </div>
              <ChevronDown size={16} className="text-neutral-400" />
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <div className="page-container animate-fade-in">{children}</div>
        </div>
      </main>

      {/* Help Panel (placeholder for future implementation) */}
      {showHelp && (
        <div className="fixed inset-0 bg-black/20 z-50" onClick={() => setShowHelp(false)}>
          <div
            className="absolute right-0 top-0 h-full w-96 bg-white shadow-dropdown p-6 animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-neutral-900">ヘルプ</h2>
              <button
                onClick={() => setShowHelp(false)}
                className="btn-ghost btn-sm rounded-full p-1"
              >
                <span className="text-xl">&times;</span>
              </button>
            </div>
            <div className="space-y-4">
              <div className="card p-4">
                <h3 className="font-medium text-neutral-800 mb-2">クイックスタート</h3>
                <p className="text-sm text-neutral-600">
                  1. データ取込からCSVファイルをアップロード
                  <br />
                  2. ダッシュボードで結果を確認
                  <br />
                  3. リスク分析で詳細を調査
                </p>
              </div>
              <div className="card p-4">
                <h3 className="font-medium text-neutral-800 mb-2">サポート</h3>
                <p className="text-sm text-neutral-600">
                  問題がある場合は、設定画面からログを確認してください。
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

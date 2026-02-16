/**
 * Main Layout Component
 *
 * Professional consulting-style application shell with categorized navigation.
 */

import { Link, useLocation } from 'react-router-dom';
import { ReactNode, useState, useEffect, useRef } from 'react';
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
  BookOpen,
  Keyboard,
  CheckCircle,
  Info,
  AlertTriangle,
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

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning';
  title: string;
  message: string;
  time: string;
  read: boolean;
}

export default function Layout({ children, isConnected }: LayoutProps) {
  const location = useLocation();
  const [showHelp, setShowHelp] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: '1',
      type: 'info',
      title: 'JAIAへようこそ',
      message: 'データ取込からCSVファイルをアップロードして分析を開始できます。',
      time: '起動時',
      read: false,
    },
  ]);

  // Close notifications dropdown when clicking outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const notifIcon = (type: Notification['type']) => {
    if (type === 'success') return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (type === 'warning') return <AlertTriangle className="w-4 h-4 text-amber-500" />;
    return <Info className="w-4 h-4 text-blue-500" />;
  };

  // Find current page info
  const currentPage =
    navGroups.flatMap((g) => g.items).find((item) => item.path === location.pathname) ||
    bottomNavItems.find((item) => item.path === location.pathname);

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-900">
      {/* Sidebar */}
      <aside className="w-[280px] bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 flex flex-col shadow-nav">
        {/* Logo */}
        <div className="h-header flex items-center px-6 border-b border-neutral-100 dark:border-neutral-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-brand rounded-xl flex items-center justify-center shadow-sm">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-primary-900 dark:text-primary-100 tracking-tight">JAIA</span>
              <p className="text-[10px] text-neutral-400 dark:text-neutral-500 font-medium tracking-wide">
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
        <div className="px-4 py-3 border-t border-neutral-100 dark:border-neutral-700">
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
        <div className="px-5 py-4 border-t border-neutral-100 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900">
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
        <header className="h-header bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between px-8 shadow-nav">
          <div>
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
              {currentPage?.label || 'JAIA'}
            </h1>
            {currentPage?.description && (
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">{currentPage.description}</p>
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
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="btn-ghost btn-sm rounded-full p-2 relative"
                title="通知"
              >
                <Bell size={20} className="text-neutral-500" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-accent-500 rounded-full" />
                )}
              </button>
              {showNotifications && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-neutral-800 rounded-lg shadow-dropdown border border-neutral-200 dark:border-neutral-700 z-50">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100">
                    <span className="font-semibold text-neutral-800 text-sm">通知</span>
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllRead}
                        className="text-xs text-primary-600 hover:text-primary-700"
                      >
                        すべて既読にする
                      </button>
                    )}
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {notifications.length > 0 ? (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={clsx(
                            'px-4 py-3 border-b border-neutral-50 last:border-0',
                            !n.read && 'bg-blue-50/50'
                          )}
                        >
                          <div className="flex items-start gap-2">
                            {notifIcon(n.type)}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-neutral-800">{n.title}</p>
                              <p className="text-xs text-neutral-500 mt-0.5">{n.message}</p>
                              <p className="text-xs text-neutral-400 mt-1">{n.time}</p>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="px-4 py-6 text-center text-sm text-neutral-400">
                        通知はありません
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

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

      {/* Help Panel */}
      {showHelp && (
        <div className="fixed inset-0 bg-black/20 z-50" onClick={() => setShowHelp(false)}>
          <div
            className="absolute right-0 top-0 h-full w-96 bg-white shadow-dropdown p-6 animate-slide-up overflow-y-auto"
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
              {/* Quick Start */}
              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen className="w-4 h-4 text-primary-600" />
                  <h3 className="font-medium text-neutral-800">クイックスタート</h3>
                </div>
                <ol className="text-sm text-neutral-600 space-y-2 list-decimal list-inside">
                  <li>
                    <strong>データ取込</strong>
                    でマスタデータ（勘定科目表、部門等）をアップロード
                  </li>
                  <li>
                    <strong>仕訳データ</strong>をCSV/Excel形式でインポート
                  </li>
                  <li>
                    <strong>ダッシュボード</strong>で全体のKPIとリスク分布を確認
                  </li>
                  <li>
                    <strong>リスク分析</strong>で高リスク仕訳の詳細を調査
                  </li>
                  <li>
                    <strong>AI分析</strong>で自然言語による深掘り分析
                  </li>
                  <li>
                    <strong>レポート生成</strong>で監査報告書を出力
                  </li>
                </ol>
              </div>

              {/* Page Guide */}
              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="w-4 h-4 text-primary-600" />
                  <h3 className="font-medium text-neutral-800">各画面の説明</h3>
                </div>
                <div className="text-sm text-neutral-600 space-y-2">
                  <div>
                    <strong>仕訳検索</strong> -
                    仕訳ID、勘定科目、金額、日付、リスクスコアで仕訳を絞り込み検索
                  </div>
                  <div>
                    <strong>時系列分析</strong> -
                    月次/週次/日次のトレンドチャートで金額・件数の推移を可視化
                  </div>
                  <div>
                    <strong>勘定科目分析</strong> - 科目別の借方・貸方残高と取引件数の分析
                  </div>
                  <div>
                    <strong>AI分析</strong> -
                    チャット形式でAIに分析を依頼（高リスク仕訳検索、異常検知等）
                  </div>
                </div>
              </div>

              {/* Data Formats */}
              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Upload className="w-4 h-4 text-primary-600" />
                  <h3 className="font-medium text-neutral-800">対応データ形式</h3>
                </div>
                <div className="text-sm text-neutral-600 space-y-1">
                  <div>
                    <strong>AICPA GL_Detail</strong> - 監査データ標準準拠の仕訳明細
                  </div>
                  <div>
                    <strong>汎用CSV/Excel</strong> - .csv, .xlsx, .xls
                  </div>
                  <div className="text-xs text-neutral-400 mt-2">
                    sample_data/ フォルダにサンプルデータがあります
                  </div>
                </div>
              </div>

              {/* Keyboard Shortcuts */}
              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Keyboard className="w-4 h-4 text-primary-600" />
                  <h3 className="font-medium text-neutral-800">キーボードショートカット</h3>
                </div>
                <div className="text-sm text-neutral-600 space-y-1">
                  <div className="flex justify-between">
                    <span>ヘルプを表示</span>
                    <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded text-xs font-mono">?</kbd>
                  </div>
                </div>
              </div>

              {/* Support */}
              <div className="card p-4">
                <h3 className="font-medium text-neutral-800 mb-2">サポート</h3>
                <p className="text-sm text-neutral-600">
                  問題がある場合は、設定画面からログを確認するか、管理者にお問い合わせください。
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

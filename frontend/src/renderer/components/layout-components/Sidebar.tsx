/**
 * Sidebar Navigation Component
 *
 * Categorized navigation with connection status indicator.
 */

import { Link } from 'react-router-dom';
import { ReactNode } from 'react';
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
  Building2,
  X,
} from 'lucide-react';
import clsx from 'clsx';

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

export const navGroups: NavGroup[] = [
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
      {
        path: '/analytics',
        label: '詳細分析',
        icon: <Building2 size={20} />,
        description: '部門・取引先・フロー分析',
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

export const bottomNavItems: NavItem[] = [
  { path: '/settings', label: '設定', icon: <Settings size={20} /> },
];

interface SidebarProps {
  currentPath: string;
  isConnected: boolean;
  sidebarOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ currentPath, isConnected, sidebarOpen, onClose }: SidebarProps) {
  return (
    <aside
      className={clsx(
        'fixed inset-y-0 left-0 z-50 w-[280px] bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 flex flex-col shadow-nav transition-transform duration-200',
        'lg:relative lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}
      aria-label="メインナビゲーション"
    >
      {/* Logo */}
      <div className="h-header flex items-center justify-between px-6 border-b border-neutral-100 dark:border-neutral-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-brand rounded-xl flex items-center justify-center shadow-sm">
            <Activity className="w-6 h-6 text-white" aria-hidden="true" />
          </div>
          <div>
            <span className="text-xl font-bold text-primary-900 dark:text-primary-100 tracking-tight">
              JAIA
            </span>
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 font-medium tracking-wide">
              Journal Entry Analyzer
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="btn-ghost btn-sm rounded-full p-1.5 lg:hidden"
          aria-label="サイドバーを閉じる"
        >
          <X size={20} className="text-neutral-500" />
        </button>
      </div>

      {/* Navigation */}
      <nav
        className="flex-1 px-4 py-5 space-y-6 overflow-y-auto scrollbar-thin"
        aria-label="メインメニュー"
      >
        {navGroups.map((group) => (
          <div key={group.label} role="group" aria-label={group.label}>
            <div className="nav-group-label mb-2" id={`nav-group-${group.label}`}>
              {group.label}
            </div>
            <div className="space-y-1" role="list" aria-labelledby={`nav-group-${group.label}`}>
              {group.items.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={clsx('nav-item group', currentPath === item.path && 'nav-item-active')}
                  title={item.description}
                  aria-current={currentPath === item.path ? 'page' : undefined}
                  role="listitem"
                >
                  <span
                    className={clsx(
                      'transition-colors',
                      currentPath === item.path
                        ? 'text-primary-700'
                        : 'text-neutral-400 group-hover:text-neutral-600'
                    )}
                    aria-hidden="true"
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
            className={clsx('nav-item', currentPath === item.path && 'nav-item-active')}
            aria-current={currentPath === item.path ? 'page' : undefined}
          >
            <span
              className={clsx(
                'transition-colors',
                currentPath === item.path ? 'text-primary-700' : 'text-neutral-400'
              )}
              aria-hidden="true"
            >
              {item.icon}
            </span>
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Status */}
      <div
        className="px-5 py-4 border-t border-neutral-100 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900"
        role="status"
        aria-label="接続状態"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={clsx(
                'w-2.5 h-2.5 rounded-full ring-2 ring-offset-1',
                isConnected ? 'bg-green-500 ring-green-200' : 'bg-red-500 ring-red-200'
              )}
              aria-hidden="true"
            />
            <span className="text-xs font-medium text-neutral-500">
              {isConnected ? '接続中' : '未接続'}
            </span>
          </div>
          <span className="text-[10px] text-neutral-400">v0.1.0</span>
        </div>
      </div>
    </aside>
  );
}

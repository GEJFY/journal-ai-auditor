/**
 * Header Component
 *
 * Top navigation bar with page title, help, notifications, and user menu.
 */

import { ReactNode, type Ref } from 'react';
import { HelpCircle, Bell, User, ChevronDown, Menu } from 'lucide-react';
import NotificationPanel, { type Notification } from './NotificationPanel';

interface HeaderProps {
  currentPageLabel?: string;
  currentPageDescription?: string;
  sidebarOpen: boolean;
  onOpenSidebar: () => void;
  showHelp: boolean;
  onToggleHelp: () => void;
  showNotifications: boolean;
  onToggleNotifications: () => void;
  notifications: Notification[];
  unreadCount: number;
  onMarkAllRead: () => void;
  notifRef: Ref<HTMLDivElement>;
  children?: ReactNode;
}

export default function Header({
  currentPageLabel,
  currentPageDescription,
  sidebarOpen,
  onOpenSidebar,
  showHelp,
  onToggleHelp,
  showNotifications,
  onToggleNotifications,
  notifications,
  unreadCount,
  onMarkAllRead,
  notifRef,
}: HeaderProps) {
  return (
    <header className="h-header bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between px-4 lg:px-8 shadow-nav">
      <div className="flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          onClick={onOpenSidebar}
          className="btn-ghost btn-sm rounded-full p-2 lg:hidden"
          aria-label="メニューを開く"
          aria-expanded={sidebarOpen}
          aria-controls="main-sidebar"
        >
          <Menu size={20} className="text-neutral-500" />
        </button>
        <div>
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            {currentPageLabel || 'JAIA'}
          </h1>
          {currentPageDescription && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5 hidden sm:block">
              {currentPageDescription}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Help Button */}
        <button
          onClick={onToggleHelp}
          className="btn-ghost btn-sm rounded-full p-2"
          aria-label="ヘルプを表示"
          aria-expanded={showHelp}
        >
          <HelpCircle size={20} className="text-neutral-500" aria-hidden="true" />
        </button>

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={onToggleNotifications}
            className="btn-ghost btn-sm rounded-full p-2 relative"
            aria-label={`通知${unreadCount > 0 ? `（${unreadCount}件の未読）` : ''}`}
            aria-expanded={showNotifications}
            aria-haspopup="true"
          >
            <Bell size={20} className="text-neutral-500" aria-hidden="true" />
            {unreadCount > 0 && (
              <span
                className="absolute top-1 right-1 w-2 h-2 bg-accent-500 rounded-full"
                aria-hidden="true"
              />
            )}
          </button>
          {showNotifications && (
            <NotificationPanel
              notifications={notifications}
              unreadCount={unreadCount}
              onMarkAllRead={onMarkAllRead}
            />
          )}
        </div>

        {/* User Menu */}
        <button
          className="flex items-center gap-2 btn-ghost btn-sm rounded-full pl-2 pr-3"
          aria-label="ユーザーメニュー"
          aria-haspopup="true"
        >
          <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
            <User size={16} className="text-primary-700" aria-hidden="true" />
          </div>
          <ChevronDown size={16} className="text-neutral-400" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}

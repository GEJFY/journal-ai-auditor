/**
 * Main Layout Component
 *
 * Professional consulting-style application shell with categorized navigation.
 * Sub-components: Sidebar, Header, NotificationPanel, HelpPanel.
 */

import { useLocation } from 'react-router-dom';
import { ReactNode, useState, useEffect, useRef, useCallback } from 'react';

import Sidebar, { navGroups, bottomNavItems } from './layout-components/Sidebar';
import Header from './layout-components/Header';
import HelpPanel from './layout-components/HelpPanel';
import type { Notification } from './layout-components/NotificationPanel';

interface LayoutProps {
  children: ReactNode;
  isConnected: boolean;
}

export default function Layout({ children, isConnected }: LayoutProps) {
  const location = useLocation();
  const [showHelp, setShowHelp] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
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

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

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

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  // Find current page info
  const currentPage =
    navGroups.flatMap((g) => g.items).find((item) => item.path === location.pathname) ||
    bottomNavItems.find((item) => item.path === location.pathname);

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-900">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 lg:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      <Sidebar
        currentPath={location.pathname}
        isConnected={isConnected}
        sidebarOpen={sidebarOpen}
        onClose={closeSidebar}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden" role="main">
        <Header
          currentPageLabel={currentPage?.label}
          currentPageDescription={currentPage?.description}
          sidebarOpen={sidebarOpen}
          onOpenSidebar={() => setSidebarOpen(true)}
          showHelp={showHelp}
          onToggleHelp={() => setShowHelp(!showHelp)}
          showNotifications={showNotifications}
          onToggleNotifications={() => setShowNotifications(!showNotifications)}
          notifications={notifications}
          unreadCount={unreadCount}
          onMarkAllRead={markAllRead}
          notifRef={notifRef}
        />

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <div className="page-container animate-fade-in">{children}</div>
        </div>
      </main>

      {/* Help Panel */}
      {showHelp && <HelpPanel onClose={() => setShowHelp(false)} />}
    </div>
  );
}

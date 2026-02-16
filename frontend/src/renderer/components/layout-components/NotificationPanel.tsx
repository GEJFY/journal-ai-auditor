/**
 * Notification Panel Component
 *
 * Dropdown notification list with read/unread state.
 */

import { CheckCircle, Info, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning';
  title: string;
  message: string;
  time: string;
  read: boolean;
}

interface NotificationPanelProps {
  notifications: Notification[];
  unreadCount: number;
  onMarkAllRead: () => void;
}

function notifIcon(type: Notification['type']) {
  if (type === 'success') return <CheckCircle className="w-4 h-4 text-green-500" />;
  if (type === 'warning') return <AlertTriangle className="w-4 h-4 text-amber-500" />;
  return <Info className="w-4 h-4 text-blue-500" />;
}

export default function NotificationPanel({
  notifications,
  unreadCount,
  onMarkAllRead,
}: NotificationPanelProps) {
  return (
    <div
      className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-neutral-800 rounded-lg shadow-dropdown border border-neutral-200 dark:border-neutral-700 z-50"
      role="menu"
      aria-label="通知一覧"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100">
        <span className="font-semibold text-neutral-800 text-sm">通知</span>
        {unreadCount > 0 && (
          <button
            onClick={onMarkAllRead}
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
          <div className="px-4 py-6 text-center text-sm text-neutral-400">通知はありません</div>
        )}
      </div>
    </div>
  );
}

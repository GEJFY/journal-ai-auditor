/**
 * PageHeader Component
 *
 * Consistent page header with title, subtitle, and action buttons.
 */

import { ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  helpId?: string;
  actions?: ReactNode;
  children?: ReactNode;
}

export default function PageHeader({
  title,
  subtitle,
  helpId,
  actions,
  children,
}: PageHeaderProps) {
  return (
    <div className="page-header mb-6">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h1 className="page-title">{title}</h1>
          {helpId && (
            <button
              className="text-neutral-400 hover:text-neutral-600 transition-colors"
              title="このページについて"
            >
              <HelpCircle size={18} />
            </button>
          )}
        </div>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
        {children}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}

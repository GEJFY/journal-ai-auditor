/**
 * StatCard Component
 *
 * Professional KPI card with value, label, change indicator, and optional icon.
 */

import { ReactNode } from 'react';
import { TrendingUp, TrendingDown, HelpCircle } from 'lucide-react';
import clsx from 'clsx';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  iconBgColor?: string;
  helpId?: string;
  variant?: 'default' | 'accent' | 'warning' | 'danger';
}

export default function StatCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon,
  iconBgColor = 'bg-primary-100',
  helpId,
  variant = 'default',
}: StatCardProps) {
  const isPositive = change && change > 0;
  const isNegative = change && change < 0;

  const variantStyles = {
    default: 'border-neutral-100',
    accent: 'border-l-4 border-l-accent-500',
    warning: 'border-l-4 border-l-risk-high',
    danger: 'border-l-4 border-l-risk-critical',
  };

  return (
    <div className={clsx('stat-card', variantStyles[variant])}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          {icon && (
            <div
              className={clsx('w-12 h-12 rounded-xl flex items-center justify-center', iconBgColor)}
            >
              {icon}
            </div>
          )}
          <div>
            <div className="flex items-center gap-1.5">
              <span className="stat-label">{title}</span>
              {helpId && (
                <button className="text-neutral-300 hover:text-neutral-500 transition-colors">
                  <HelpCircle size={14} />
                </button>
              )}
            </div>
            <div className="stat-value">{value}</div>
            {subtitle && <p className="text-sm text-neutral-500 mt-1">{subtitle}</p>}
          </div>
        </div>
      </div>

      {change !== undefined && (
        <div className="mt-4 pt-4 border-t border-neutral-100">
          <div
            className={clsx(
              'stat-change flex items-center gap-1',
              isPositive && 'stat-change-positive',
              isNegative && 'stat-change-negative',
              !isPositive && !isNegative && 'text-neutral-500'
            )}
          >
            {isPositive && <TrendingUp size={16} />}
            {isNegative && <TrendingDown size={16} />}
            <span>
              {isPositive && '+'}
              {change}%
            </span>
            {changeLabel && <span className="text-neutral-400 ml-1">{changeLabel}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

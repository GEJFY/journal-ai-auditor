/**
 * HelpTooltip Component
 *
 * Contextual help tooltip that appears on hover.
 */

import { useState, useRef, useEffect, ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';
import { helpContent } from '../../lib/helpContent';
import clsx from 'clsx';

interface HelpTooltipProps {
  id: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
  children?: ReactNode;
  iconSize?: number;
}

export default function HelpTooltip({
  id,
  position = 'top',
  children,
  iconSize = 16,
}: HelpTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const content = helpContent[id];

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const trigger = triggerRef.current.getBoundingClientRect();
      const tooltip = tooltipRef.current.getBoundingClientRect();

      let top = 0;
      let left = 0;

      switch (position) {
        case 'top':
          top = trigger.top - tooltip.height - 8;
          left = trigger.left + trigger.width / 2 - tooltip.width / 2;
          break;
        case 'bottom':
          top = trigger.bottom + 8;
          left = trigger.left + trigger.width / 2 - tooltip.width / 2;
          break;
        case 'left':
          top = trigger.top + trigger.height / 2 - tooltip.height / 2;
          left = trigger.left - tooltip.width - 8;
          break;
        case 'right':
          top = trigger.top + trigger.height / 2 - tooltip.height / 2;
          left = trigger.right + 8;
          break;
      }

      // Keep tooltip within viewport
      left = Math.max(8, Math.min(left, window.innerWidth - tooltip.width - 8));
      top = Math.max(8, Math.min(top, window.innerHeight - tooltip.height - 8));

      setCoords({ top, left });
    }
  }, [isVisible, position]);

  if (!content) {
    return null;
  }

  return (
    <>
      <button
        ref={triggerRef}
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        className="inline-flex items-center justify-center text-neutral-400 hover:text-neutral-600 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded"
        aria-label={content.title}
      >
        {children || <HelpCircle size={iconSize} />}
      </button>

      {isVisible && (
        <div
          ref={tooltipRef}
          className={clsx(
            'fixed z-[100] bg-neutral-800 text-white rounded-lg shadow-dropdown p-4 max-w-xs',
            'animate-fade-in'
          )}
          style={{ top: coords.top, left: coords.left }}
          role="tooltip"
        >
          <h4 className="font-semibold text-sm mb-1">{content.title}</h4>
          <p className="text-neutral-300 text-sm leading-relaxed">
            {content.description}
          </p>
          {content.learnMoreUrl && (
            <a
              href={content.learnMoreUrl}
              className="inline-block mt-2 text-xs text-accent-400 hover:text-accent-300"
            >
              詳細を見る →
            </a>
          )}
          {/* Arrow */}
          <div
            className={clsx(
              'absolute w-2 h-2 bg-neutral-800 transform rotate-45',
              position === 'top' && 'bottom-[-4px] left-1/2 -translate-x-1/2',
              position === 'bottom' && 'top-[-4px] left-1/2 -translate-x-1/2',
              position === 'left' && 'right-[-4px] top-1/2 -translate-y-1/2',
              position === 'right' && 'left-[-4px] top-1/2 -translate-y-1/2'
            )}
          />
        </div>
      )}
    </>
  );
}

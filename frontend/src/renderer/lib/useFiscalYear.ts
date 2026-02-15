/**
 * Shared fiscal year hook.
 *
 * Determines the current fiscal year based on settings or current date.
 * The fiscal year start month is read from localStorage settings.
 */

import { useState, useEffect } from 'react';

function detectFiscalYear(startMonth: number): number {
  const now = new Date();
  const currentMonth = now.getMonth() + 1; // 1-based
  const currentYear = now.getFullYear();
  // If the current month is before the fiscal year start, the fiscal year
  // started in the previous calendar year.
  return currentMonth >= startMonth ? currentYear : currentYear - 1;
}

export function useFiscalYear(): [number, (year: number) => void] {
  const [fiscalYear, setFiscalYear] = useState<number>(() => {
    // Try to read fiscal year start month from saved settings
    try {
      const stored = localStorage.getItem('jaia-settings');
      if (stored) {
        const settings = JSON.parse(stored);
        const startMonth = parseInt(settings.fiscalYearStart || '4', 10);
        return detectFiscalYear(startMonth);
      }
    } catch {
      // ignore parse errors
    }
    // Default: April start → detect based on current date
    return detectFiscalYear(4);
  });

  useEffect(() => {
    // Re-check if settings change (e.g. after saving settings page)
    const handler = () => {
      try {
        const stored = localStorage.getItem('jaia-settings');
        if (stored) {
          const settings = JSON.parse(stored);
          const startMonth = parseInt(settings.fiscalYearStart || '4', 10);
          setFiscalYear(detectFiscalYear(startMonth));
        }
      } catch {
        // ignore
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  return [fiscalYear, setFiscalYear];
}

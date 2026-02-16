/**
 * LoadingSpinner - 共通ローディング表示コンポーネント
 */

import clsx from 'clsx';

interface LoadingSpinnerProps {
  /** 表示サイズ */
  size?: 'sm' | 'md' | 'lg';
  /** ラベルテキスト */
  label?: string;
  /** コンテナの高さクラス (e.g., "h-32", "h-64") */
  height?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-8 w-8 border-2',
};

export default function LoadingSpinner({
  size = 'md',
  label,
  height = 'h-32',
}: LoadingSpinnerProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center', height)}>
      <div
        className={clsx(
          'animate-spin rounded-full border-b-2 border-primary-600 dark:border-primary-400',
          sizeClasses[size]
        )}
      />
      {label && (
        <p className="mt-3 text-sm text-neutral-500 dark:text-neutral-400">{label}</p>
      )}
    </div>
  );
}

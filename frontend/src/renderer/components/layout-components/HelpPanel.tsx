/**
 * Help Panel Component
 *
 * Right-side drawer with quick start guide, page descriptions, and shortcuts.
 */

import { X, BookOpen, FileText, Upload, Keyboard } from 'lucide-react';

interface HelpPanelProps {
  onClose: () => void;
}

export default function HelpPanel({ onClose }: HelpPanelProps) {
  return (
    <div className="fixed inset-0 bg-black/20 z-50" onClick={onClose} aria-hidden="true">
      <div
        className="absolute right-0 top-0 h-full w-96 max-w-full bg-white shadow-dropdown p-6 animate-slide-up overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="ヘルプパネル"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-neutral-900">ヘルプ</h2>
          <button
            onClick={onClose}
            className="btn-ghost btn-sm rounded-full p-1"
            aria-label="ヘルプを閉じる"
          >
            <X size={20} className="text-neutral-500" aria-hidden="true" />
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
  );
}

/**
 * Import Page
 *
 * Data import interface for CSV/Excel files.
 */

import { useState, useCallback } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react';
import { API_BASE } from '@/lib/api';

interface ImportStatus {
  step: 'idle' | 'validating' | 'mapping' | 'importing' | 'complete' | 'error';
  message: string;
}

export default function ImportPage() {
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState<ImportStatus>({
    step: 'idle',
    message: '',
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  }, []);

  const handleFile = async (file: File) => {
    const allowedExtensions = ['.csv', '.xlsx', '.xls'];
    const maxFileSize = 500 * 1024 * 1024; // 500MB
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!allowedExtensions.includes(ext)) {
      setStatus({
        step: 'error',
        message: `対応していないファイル形式です: ${ext}（CSV, XLSX, XLS のみ対応）`,
      });
      return;
    }

    if (file.size > maxFileSize) {
      setStatus({
        step: 'error',
        message: `ファイルサイズが大きすぎます: ${(file.size / 1024 / 1024).toFixed(1)}MB（上限: 500MB）`,
      });
      return;
    }

    if (file.size === 0) {
      setStatus({ step: 'error', message: 'ファイルが空です' });
      return;
    }

    setStatus({ step: 'validating', message: 'ファイルを検証中...' });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/import/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `インポートエラー: ${response.status}`);
      }

      const result = await response.json();
      setStatus({
        step: 'complete',
        message: `${file.name} の読み込みが完了しました（${result.imported_count ?? 0} 件）`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'インポート中にエラーが発生しました';
      setStatus({ step: 'error', message });
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">データ取込</h2>

        <div
          className={`
            relative border-2 border-dashed rounded-xl p-12 text-center
            transition-colors cursor-pointer
            ${
              dragActive
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/10'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
            }
          `}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileInput}
            className="hidden"
          />

          <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <p className="text-lg text-gray-700 dark:text-gray-300 mb-2">
            ファイルをドラッグ＆ドロップ
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            または
            <span className="text-primary-600 hover:text-primary-700 font-medium">
              {' '}
              クリックして選択
            </span>
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
            対応形式: CSV, Excel (.xlsx, .xls)
          </p>
        </div>

        {/* Status */}
        {status.step !== 'idle' && (
          <div
            className={`
            mt-4 p-4 rounded-lg flex items-center gap-3
            ${
              status.step === 'error'
                ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                : status.step === 'complete'
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                  : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
            }
          `}
          >
            {status.step === 'error' ? (
              <AlertCircle className="w-5 h-5" />
            ) : status.step === 'complete' ? (
              <CheckCircle className="w-5 h-5" />
            ) : (
              <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            )}
            <span>{status.message}</span>
          </div>
        )}
      </div>

      {/* Supported Formats */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          対応フォーマット
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <FileText className="w-5 h-5 text-green-600" />
              <span className="font-medium text-gray-900 dark:text-white">AICPA GL_Detail</span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              AICPA監査データ標準に準拠した仕訳明細形式
            </p>
          </div>

          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-gray-900 dark:text-white">汎用CSV/Excel</span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              カスタム列マッピングで柔軟に対応
            </p>
          </div>
        </div>
      </div>

      {/* Import History */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">取込履歴</h3>

        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          まだ取込履歴がありません
        </div>
      </div>
    </div>
  );
}

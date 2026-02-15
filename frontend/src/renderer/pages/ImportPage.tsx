/**
 * Import Page
 *
 * Guided data import interface with clear distinction between
 * master data (CoA, departments, vendors, users) and journal entries.
 */

import { useState, useCallback, useRef } from 'react';
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle,
  BookOpen,
  Building2,
  Users,
  Truck,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

type UploadStatus = 'idle' | 'uploading' | 'complete' | 'error';

interface MasterDataType {
  key: 'accounts' | 'departments' | 'vendors' | 'users';
  label: string;
  shortLabel: string;
  description: string;
  sampleFile: string;
  icon: React.ReactNode;
}

interface MasterCardState {
  status: UploadStatus;
  message: string;
  importedCount: number;
}

// =============================================================================
// Constants
// =============================================================================

const MASTER_DATA_TYPES: MasterDataType[] = [
  {
    key: 'accounts',
    label: '勘定科目表',
    shortLabel: 'CoA',
    description: '勘定科目コード・名称・分類を定義するマスタデータ',
    sampleFile: '01_chart_of_accounts.csv',
    icon: <BookOpen size={24} />,
  },
  {
    key: 'departments',
    label: '部門マスタ',
    shortLabel: 'Dept',
    description: '部門コード・名称・コストセンター情報',
    sampleFile: '02_department_master.csv',
    icon: <Building2 size={24} />,
  },
  {
    key: 'vendors',
    label: '取引先マスタ',
    shortLabel: 'Vendor',
    description: '仕入先・得意先の基本情報',
    sampleFile: '03_vendor_master.csv',
    icon: <Truck size={24} />,
  },
  {
    key: 'users',
    label: 'ユーザーマスタ',
    shortLabel: 'User',
    description: '担当者・承認者の情報と権限設定',
    sampleFile: '04_user_master.csv',
    icon: <Users size={24} />,
  },
];

const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

// =============================================================================
// Helper: File validation
// =============================================================================

function validateFile(file: File): string | null {
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `対応していないファイル形式です: ${ext}（CSV, XLSX, XLS のみ対応）`;
  }
  if (file.size > MAX_FILE_SIZE) {
    return `ファイルサイズが大きすぎます: ${(file.size / 1024 / 1024).toFixed(1)}MB（上限: 500MB）`;
  }
  if (file.size === 0) {
    return 'ファイルが空です';
  }
  return null;
}

// =============================================================================
// Helper: Upload + import
// =============================================================================

async function uploadAndImportMaster(
  file: File,
  masterType: string
): Promise<{ success: boolean; count: number; message: string }> {
  // Step 1: Upload
  const formData = new FormData();
  formData.append('file', file);

  const uploadRes = await fetch(`${API_BASE}/import/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!uploadRes.ok) {
    const err = await uploadRes.json().catch(() => ({}));
    throw new Error(err.detail || `アップロードエラー: ${uploadRes.status}`);
  }

  const { temp_file_id } = await uploadRes.json();

  // Step 2: Import master
  const importRes = await fetch(`${API_BASE}/import/master`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temp_file_id, master_type: masterType }),
  });

  if (!importRes.ok) {
    const err = await importRes.json().catch(() => ({}));
    throw new Error(err.detail || `インポートエラー: ${importRes.status}`);
  }

  const result = await importRes.json();
  return {
    success: result.success,
    count: result.imported_rows ?? 0,
    message: result.success ? `${result.imported_rows} 件を取り込みました` : `取込に失敗しました`,
  };
}

async function uploadAndImportJournal(
  file: File
): Promise<{ success: boolean; count: number; message: string }> {
  // Step 1: Upload
  const formData = new FormData();
  formData.append('file', file);

  const uploadRes = await fetch(`${API_BASE}/import/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!uploadRes.ok) {
    const err = await uploadRes.json().catch(() => ({}));
    throw new Error(err.detail || `アップロードエラー: ${uploadRes.status}`);
  }

  const { temp_file_id } = await uploadRes.json();

  // Step 2: Execute import (auto column mapping)
  const importRes = await fetch(`${API_BASE}/import/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      temp_file_id,
      column_mapping: {},
      skip_errors: false,
    }),
  });

  if (!importRes.ok) {
    const err = await importRes.json().catch(() => ({}));
    throw new Error(err.detail || `インポートエラー: ${importRes.status}`);
  }

  const result = await importRes.json();
  return {
    success: result.success,
    count: result.imported_rows ?? 0,
    message: result.success
      ? `${result.imported_rows} 件の仕訳を取り込みました`
      : `取込に失敗しました`,
  };
}

// =============================================================================
// Component: MasterDataCard
// =============================================================================

function MasterDataCard({
  masterType,
  state,
  onFileSelected,
}: {
  masterType: MasterDataType;
  state: MasterCardState;
  onFileSelected: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="card p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center text-primary-600 dark:text-primary-400 flex-shrink-0">
          {masterType.icon}
        </div>
        <div className="min-w-0">
          <h4 className="font-semibold text-gray-900 dark:text-white text-sm leading-tight">
            {masterType.label}
            <span className="ml-1.5 text-xs font-normal text-gray-400">
              ({masterType.shortLabel})
            </span>
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
            {masterType.description}
          </p>
        </div>
      </div>

      {/* Sample file hint */}
      <div className="text-xs text-gray-400 dark:text-gray-500 mb-3 flex items-center gap-1">
        <FileText size={12} />
        <span>サンプル: {masterType.sampleFile}</span>
      </div>

      {/* Status / Action */}
      <div className="mt-auto">
        {state.status === 'complete' ? (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2">
            <CheckCircle size={16} />
            <span>{state.message}</span>
          </div>
        ) : state.status === 'error' ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
              <AlertCircle size={16} />
              <span className="truncate">{state.message}</span>
            </div>
            <button
              onClick={() => inputRef.current?.click()}
              className="btn btn-secondary w-full text-sm py-1.5"
            >
              再選択
            </button>
          </div>
        ) : state.status === 'uploading' ? (
          <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg px-3 py-2">
            <Loader2 size={16} className="animate-spin" />
            <span>取込中...</span>
          </div>
        ) : (
          <button
            onClick={() => inputRef.current?.click()}
            className="btn btn-secondary w-full text-sm py-1.5"
          >
            <Upload size={14} />
            ファイルを選択
          </button>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelected(file);
          e.target.value = '';
        }}
      />
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export default function ImportPage() {
  // Master data states
  const [masterStates, setMasterStates] = useState<Record<string, MasterCardState>>({
    accounts: { status: 'idle', message: '', importedCount: 0 },
    departments: { status: 'idle', message: '', importedCount: 0 },
    vendors: { status: 'idle', message: '', importedCount: 0 },
    users: { status: 'idle', message: '', importedCount: 0 },
  });

  // Journal entry state
  const [jeStatus, setJeStatus] = useState<UploadStatus>('idle');
  const [jeMessage, setJeMessage] = useState('');
  const [dragActive, setDragActive] = useState(false);

  // Master data upload handler
  const handleMasterFile = useCallback(async (file: File, masterType: string) => {
    const error = validateFile(file);
    if (error) {
      setMasterStates((prev) => ({
        ...prev,
        [masterType]: { status: 'error' as const, message: error, importedCount: 0 },
      }));
      return;
    }

    setMasterStates((prev) => ({
      ...prev,
      [masterType]: { status: 'uploading' as const, message: '取込中...', importedCount: 0 },
    }));

    try {
      const result = await uploadAndImportMaster(file, masterType);
      setMasterStates((prev) => ({
        ...prev,
        [masterType]: {
          status: result.success ? ('complete' as const) : ('error' as const),
          message: result.message,
          importedCount: result.count,
        },
      }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : '取込中にエラーが発生しました';
      setMasterStates((prev) => ({
        ...prev,
        [masterType]: { status: 'error' as const, message: msg, importedCount: 0 },
      }));
    }
  }, []);

  // Journal entry upload handler
  const handleJournalFile = useCallback(async (file: File) => {
    const error = validateFile(file);
    if (error) {
      setJeStatus('error');
      setJeMessage(error);
      return;
    }

    setJeStatus('uploading');
    setJeMessage(`${file.name} を取り込み中...`);

    try {
      const result = await uploadAndImportJournal(file);
      setJeStatus(result.success ? 'complete' : 'error');
      setJeMessage(result.message);
    } catch (err) {
      setJeStatus('error');
      setJeMessage(err instanceof Error ? err.message : '取込中にエラーが発生しました');
    }
  }, []);

  // Drag and drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.[0]) {
        handleJournalFile(e.dataTransfer.files[0]);
      }
    },
    [handleJournalFile]
  );

  // Count completed masters
  const completedMasters = Object.values(masterStates).filter(
    (s) => s.status === 'complete'
  ).length;

  return (
    <div className="space-y-8">
      {/* Step Indicator */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              completedMasters > 0
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
            }`}
          >
            {completedMasters > 0 ? <CheckCircle size={16} /> : '1'}
          </div>
          <div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">マスタデータ</span>
            <span className="text-xs text-gray-400 ml-1.5">（推奨）</span>
          </div>
        </div>

        <ArrowRight size={16} className="text-gray-300 dark:text-gray-600" />

        <div className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              jeStatus === 'complete'
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
            }`}
          >
            {jeStatus === 'complete' ? <CheckCircle size={16} /> : '2'}
          </div>
          <div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">仕訳データ</span>
            <span className="text-xs text-red-500 ml-1.5">（必須）</span>
          </div>
        </div>
      </div>

      {/* ================================================================== */}
      {/* Step 1: Master Data */}
      {/* ================================================================== */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Step 1: マスタデータの取込
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            分析の精度を高めるため、先にマスタデータを取り込むことを推奨します。
            <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded ml-1">
              sample_data/
            </code>{' '}
            フォルダにサンプルがあります。
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MASTER_DATA_TYPES.map((mt) => (
            <MasterDataCard
              key={mt.key}
              masterType={mt}
              state={masterStates[mt.key]}
              onFileSelected={(file) => handleMasterFile(file, mt.key)}
            />
          ))}
        </div>
      </div>

      {/* ================================================================== */}
      {/* Step 2: Journal Entries */}
      {/* ================================================================== */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Step 2: 仕訳データ (Journal Entries) の取込
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            AICPA GL_Detail形式またはCSV/Excelの仕訳明細データをアップロードしてください。
            <span className="text-xs text-gray-400 ml-1">
              サンプル:{' '}
              <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                10_journal_entries.csv
              </code>
            </span>
          </p>
        </div>

        <div className="card p-6">
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
            onClick={() => document.getElementById('je-file-input')?.click()}
          >
            <input
              id="je-file-input"
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleJournalFile(file);
                e.target.value = '';
              }}
              className="hidden"
            />

            <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-lg text-gray-700 dark:text-gray-300 mb-2">
              仕訳データファイルをドラッグ＆ドロップ
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              または
              <span className="text-primary-600 hover:text-primary-700 font-medium">
                {' '}
                クリックして選択
              </span>
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
              対応形式: CSV, Excel (.xlsx, .xls) / 上限: 500MB
            </p>
          </div>

          {/* JE Status */}
          {jeStatus !== 'idle' && (
            <div
              className={`
                mt-4 p-4 rounded-lg flex items-center gap-3
                ${
                  jeStatus === 'error'
                    ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                    : jeStatus === 'complete'
                      ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                      : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
                }
              `}
            >
              {jeStatus === 'error' ? (
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
              ) : jeStatus === 'complete' ? (
                <CheckCircle className="w-5 h-5 flex-shrink-0" />
              ) : (
                <Loader2 className="w-5 h-5 flex-shrink-0 animate-spin" />
              )}
              <span>{jeMessage}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

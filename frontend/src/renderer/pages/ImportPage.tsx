/**
 * Import Page
 *
 * Guided data import interface with clear distinction between
 * master data (CoA, departments, vendors, users) and journal entries.
 * Journal entries go through a column mapping step before import.
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
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { API_BASE, api, type FilePreviewResponse, type ImportValidationResponse } from '@/lib/api';

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

type JournalPhase =
  | 'idle'
  | 'uploading'
  | 'mapping'
  | 'validating'
  | 'validated'
  | 'importing'
  | 'complete'
  | 'error';

interface JournalImportState {
  phase: JournalPhase;
  tempFileId: string | null;
  filename: string | null;
  preview: FilePreviewResponse | null;
  columnMapping: Record<string, string>;
  validationResult: ImportValidationResponse | null;
  errorMessage: string;
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

interface TargetField {
  key: string;
  label: string;
  required: boolean;
}

const TARGET_FIELDS: TargetField[] = [
  { key: 'journal_id', label: '伝票番号', required: true },
  { key: 'effective_date', label: '計上日', required: true },
  { key: 'gl_account_number', label: '勘定科目コード', required: true },
  { key: 'amount', label: '金額', required: true },
  { key: 'debit_credit_indicator', label: '借貸区分', required: true },
  { key: 'journal_id_line_number', label: '行番号', required: false },
  { key: 'gl_detail_id', label: '明細ID', required: false },
  { key: 'business_unit_code', label: '事業部コード', required: false },
  { key: 'fiscal_year', label: '会計年度', required: false },
  { key: 'accounting_period', label: '会計期間', required: false },
  { key: 'entry_date', label: '入力日', required: false },
  { key: 'entry_time', label: '入力時刻', required: false },
  { key: 'amount_currency', label: '通貨', required: false },
  { key: 'functional_amount', label: '円貨金額', required: false },
  { key: 'je_line_description', label: '摘要', required: false },
  { key: 'source', label: '発生源', required: false },
  { key: 'vendor_code', label: '取引先コード', required: false },
  { key: 'dept_code', label: '部門コード', required: false },
  { key: 'prepared_by', label: '起票者', required: false },
  { key: 'approved_by', label: '承認者', required: false },
  { key: 'approved_date', label: '承認日', required: false },
];

const INITIAL_JE_STATE: JournalImportState = {
  phase: 'idle',
  tempFileId: null,
  filename: null,
  preview: null,
  columnMapping: {},
  validationResult: null,
  errorMessage: '',
  importedCount: 0,
};

// =============================================================================
// Helper: File validation
// =============================================================================

function validateFileInput(file: File): string | null {
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
// Helper: Upload + import master
// =============================================================================

async function uploadAndImportMaster(
  file: File,
  masterType: string
): Promise<{ success: boolean; count: number; message: string }> {
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
    message: result.success ? `${result.imported_rows} 件を取り込みました` : '取込に失敗しました',
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

      <div className="text-xs text-gray-400 dark:text-gray-500 mb-3 flex items-center gap-1">
        <FileText size={12} />
        <span>サンプル: {masterType.sampleFile}</span>
      </div>

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
// Component: ColumnMappingPanel
// =============================================================================

function ColumnMappingPanel({
  preview,
  columnMapping,
  onMappingChange,
  onValidate,
  onCancel,
  isValidating,
  errorMessage,
}: {
  preview: FilePreviewResponse;
  columnMapping: Record<string, string>;
  onMappingChange: (targetField: string, sourceColumn: string | null) => void;
  onValidate: () => void;
  onCancel: () => void;
  isValidating: boolean;
  errorMessage: string;
}) {
  const [showSample, setShowSample] = useState(false);

  const missingRequired = TARGET_FIELDS.filter((f) => f.required && !columnMapping[f.key]).map(
    (f) => f.key
  );

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-primary-600" />
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white">{preview.filename}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {preview.total_rows.toLocaleString()} 行 / {preview.column_count} 列
              </p>
            </div>
          </div>
          {missingRequired.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              <AlertCircle size={12} />
              必須項目 {missingRequired.length} 件未設定
            </span>
          )}
        </div>
      </div>

      {/* Mapping Table */}
      <div className="p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-neutral-700">
                <th className="text-left py-2 pr-3 font-medium text-gray-500 dark:text-gray-400 w-48">
                  取込先フィールド
                </th>
                <th className="text-left py-2 pr-3 font-medium text-gray-500 dark:text-gray-400 w-16">
                  区分
                </th>
                <th className="text-left py-2 pr-3 font-medium text-gray-500 dark:text-gray-400">
                  ファイル列（マッピング）
                </th>
                <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400 w-48">
                  サンプル値
                </th>
              </tr>
            </thead>
            <tbody>
              {TARGET_FIELDS.map((field) => {
                const sourceCol = columnMapping[field.key] || '';
                const sampleVal =
                  sourceCol && preview.sample_data[0] ? preview.sample_data[0][sourceCol] : null;

                return (
                  <tr
                    key={field.key}
                    className="border-b border-gray-100 dark:border-neutral-700/50"
                  >
                    <td className="py-2.5 pr-3">
                      <span className="font-medium text-gray-800 dark:text-gray-200">
                        {field.label}
                      </span>
                      <span className="ml-1.5 text-xs text-gray-400 font-mono">{field.key}</span>
                    </td>
                    <td className="py-2.5 pr-3">
                      {field.required ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                          必須
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 dark:bg-neutral-700 dark:text-gray-400">
                          任意
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-3">
                      <select
                        value={sourceCol}
                        onChange={(e) => onMappingChange(field.key, e.target.value || null)}
                        className={`w-full px-3 py-1.5 text-sm border rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white ${
                          field.required && !sourceCol
                            ? 'border-red-300 dark:border-red-600'
                            : 'border-gray-300 dark:border-neutral-600'
                        }`}
                      >
                        <option value="">-- 未設定 --</option>
                        {preview.columns.map((col) => (
                          <option key={col} value={col}>
                            {col}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2.5 text-xs text-gray-500 dark:text-gray-400 font-mono truncate max-w-[200px]">
                      {sampleVal !== null && sampleVal !== undefined ? String(sampleVal) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sample Data Preview (collapsible) */}
      {preview.sample_data.length > 0 && (
        <div className="border-t border-gray-200 dark:border-neutral-700">
          <button
            onClick={() => setShowSample(!showSample)}
            className="w-full px-6 py-3 flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-neutral-800/50"
          >
            {showSample ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            サンプルデータ（先頭 {Math.min(preview.sample_data.length, 5)} 行）
          </button>
          {showSample && (
            <div className="px-6 pb-4 overflow-x-auto">
              <table className="text-xs border-collapse">
                <thead>
                  <tr>
                    {preview.columns.map((col) => (
                      <th
                        key={col}
                        className="px-3 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-neutral-700 whitespace-nowrap"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.sample_data.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                      {preview.columns.map((col) => (
                        <td
                          key={col}
                          className="px-3 py-1 text-gray-700 dark:text-gray-300 border-b border-gray-100 dark:border-neutral-700/50 whitespace-nowrap max-w-[200px] truncate"
                        >
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Error message */}
      {errorMessage && (
        <div className="px-6 pb-3">
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-4 border-t border-gray-200 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 flex items-center justify-between">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
        >
          キャンセル
        </button>
        <button
          onClick={onValidate}
          disabled={missingRequired.length > 0 || isValidating}
          className="px-5 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2"
        >
          {isValidating ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              検証中...
            </>
          ) : (
            '検証する'
          )}
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Component: ValidationResultPanel
// =============================================================================

function ValidationResultPanel({
  result,
  onProceed,
  onBackToMapping,
  isImporting,
}: {
  result: ImportValidationResponse;
  onProceed: () => void;
  onBackToMapping: () => void;
  isImporting: boolean;
}) {
  const hasErrors = result.error_count > 0;

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div
        className={`px-6 py-4 flex items-center gap-3 ${
          hasErrors
            ? 'bg-red-50 dark:bg-red-900/20'
            : result.warning_count > 0
              ? 'bg-amber-50 dark:bg-amber-900/20'
              : 'bg-green-50 dark:bg-green-900/20'
        }`}
      >
        {hasErrors ? (
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
        ) : result.warning_count > 0 ? (
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
        ) : (
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
        )}
        <div>
          <h3
            className={`font-medium ${
              hasErrors
                ? 'text-red-800 dark:text-red-300'
                : result.warning_count > 0
                  ? 'text-amber-800 dark:text-amber-300'
                  : 'text-green-800 dark:text-green-300'
            }`}
          >
            {hasErrors
              ? '検証エラーがあります'
              : result.warning_count > 0
                ? '警告があります（インポート可能）'
                : '検証OK'}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            全 {result.total_rows.toLocaleString()} 行 / エラー {result.error_count} 件 / 警告{' '}
            {result.warning_count} 件
          </p>
        </div>
      </div>

      {/* Error / Warning list */}
      {(result.errors.length > 0 || result.warnings.length > 0) && (
        <div className="px-6 py-4 max-h-64 overflow-y-auto space-y-2">
          {result.errors.slice(0, 20).map((err, i) => (
            <div
              key={`err-${i}`}
              className="text-sm text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/10 rounded px-3 py-2"
            >
              {err.message ? String(err.message) : JSON.stringify(err)}
            </div>
          ))}
          {result.warnings.slice(0, 10).map((warn, i) => (
            <div
              key={`warn-${i}`}
              className="text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/10 rounded px-3 py-2"
            >
              {warn.message ? String(warn.message) : JSON.stringify(warn)}
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-4 border-t border-gray-200 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 flex items-center justify-between">
        <button
          onClick={onBackToMapping}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
        >
          マッピングに戻る
        </button>
        <button
          onClick={onProceed}
          disabled={hasErrors || isImporting}
          className="px-5 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2"
        >
          {isImporting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              インポート中...
            </>
          ) : result.warning_count > 0 ? (
            '警告を無視してインポート'
          ) : (
            'インポート実行'
          )}
        </button>
      </div>
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

  // Journal entry state machine
  const [jeState, setJeState] = useState<JournalImportState>(INITIAL_JE_STATE);
  const [dragActive, setDragActive] = useState(false);

  // Master data upload handler
  const handleMasterFile = useCallback(async (file: File, masterType: string) => {
    const error = validateFileInput(file);
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

  // Journal entry: upload + preview
  const handleJournalFile = useCallback(async (file: File) => {
    const error = validateFileInput(file);
    if (error) {
      setJeState({ ...INITIAL_JE_STATE, phase: 'error', errorMessage: error });
      return;
    }

    setJeState({ ...INITIAL_JE_STATE, phase: 'uploading', filename: file.name });

    try {
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

      const preview = await api.getFilePreview(temp_file_id);

      setJeState({
        phase: 'mapping',
        tempFileId: temp_file_id,
        filename: file.name,
        preview,
        columnMapping: { ...preview.suggested_mapping },
        validationResult: null,
        errorMessage: '',
        importedCount: 0,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : '取込中にエラーが発生しました';
      setJeState({ ...INITIAL_JE_STATE, phase: 'error', errorMessage: msg });
    }
  }, []);

  // Mapping change handler
  const handleMappingChange = useCallback((targetField: string, sourceColumn: string | null) => {
    setJeState((prev) => {
      const newMapping = { ...prev.columnMapping };
      if (sourceColumn) {
        newMapping[targetField] = sourceColumn;
      } else {
        delete newMapping[targetField];
      }
      return { ...prev, columnMapping: newMapping, validationResult: null, errorMessage: '' };
    });
  }, []);

  // Validate handler
  const handleValidate = useCallback(async () => {
    if (!jeState.tempFileId) return;

    setJeState((prev) => ({ ...prev, phase: 'validating', errorMessage: '' }));

    try {
      const result = await api.validateImportFile(jeState.tempFileId, jeState.columnMapping);
      setJeState((prev) => ({ ...prev, phase: 'validated', validationResult: result }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : '検証中にエラーが発生しました';
      setJeState((prev) => ({ ...prev, phase: 'mapping', errorMessage: msg }));
    }
  }, [jeState.tempFileId, jeState.columnMapping]);

  // Execute import handler
  const handleExecuteImport = useCallback(async () => {
    if (!jeState.tempFileId) return;

    setJeState((prev) => ({ ...prev, phase: 'importing' }));

    try {
      const importRes = await fetch(`${API_BASE}/import/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temp_file_id: jeState.tempFileId,
          column_mapping: jeState.columnMapping,
          skip_errors: false,
        }),
      });
      if (!importRes.ok) {
        const err = await importRes.json().catch(() => ({}));
        throw new Error(err.detail || `インポートエラー: ${importRes.status}`);
      }
      const result = await importRes.json();
      setJeState((prev) => ({
        ...prev,
        phase: result.success ? 'complete' : 'error',
        importedCount: result.imported_rows ?? 0,
        errorMessage: result.success ? '' : 'インポートに失敗しました',
      }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'インポート中にエラーが発生しました';
      setJeState((prev) => ({ ...prev, phase: 'error', errorMessage: msg }));
    }
  }, [jeState.tempFileId, jeState.columnMapping]);

  // Cancel / back handlers
  const handleCancel = useCallback(() => {
    setJeState(INITIAL_JE_STATE);
  }, []);

  const handleBackToMapping = useCallback(() => {
    setJeState((prev) => ({ ...prev, phase: 'mapping', validationResult: null }));
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

  const completedMasters = Object.values(masterStates).filter(
    (s) => s.status === 'complete'
  ).length;

  const isJeComplete = jeState.phase === 'complete';

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
              isJeComplete
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
            }`}
          >
            {isJeComplete ? <CheckCircle size={16} /> : '2'}
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
            {jeState.phase === 'mapping' || jeState.phase === 'validating'
              ? 'ファイルの列と取込先フィールドのマッピングを確認・調整してください。'
              : jeState.phase === 'validated'
                ? '検証結果を確認してください。'
                : jeState.phase === 'complete'
                  ? 'インポートが完了しました。'
                  : 'AICPA GL_Detail形式またはCSV/Excelの仕訳明細データをアップロードしてください。'}
          </p>
        </div>

        {/* Phase: idle / uploading / error → show drag-and-drop zone */}
        {(jeState.phase === 'idle' ||
          jeState.phase === 'uploading' ||
          jeState.phase === 'error') && (
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

            {jeState.phase === 'uploading' && (
              <div className="mt-4 p-4 rounded-lg flex items-center gap-3 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400">
                <Loader2 className="w-5 h-5 flex-shrink-0 animate-spin" />
                <span>{jeState.filename} をアップロード中...</span>
              </div>
            )}
            {jeState.phase === 'error' && (
              <div className="mt-4 p-4 rounded-lg flex items-center gap-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{jeState.errorMessage}</span>
              </div>
            )}
          </div>
        )}

        {/* Phase: mapping / validating → show ColumnMappingPanel */}
        {(jeState.phase === 'mapping' || jeState.phase === 'validating') && jeState.preview && (
          <ColumnMappingPanel
            preview={jeState.preview}
            columnMapping={jeState.columnMapping}
            onMappingChange={handleMappingChange}
            onValidate={handleValidate}
            onCancel={handleCancel}
            isValidating={jeState.phase === 'validating'}
            errorMessage={jeState.errorMessage}
          />
        )}

        {/* Phase: validated → show ValidationResultPanel */}
        {jeState.phase === 'validated' && jeState.validationResult && (
          <ValidationResultPanel
            result={jeState.validationResult}
            onProceed={handleExecuteImport}
            onBackToMapping={handleBackToMapping}
            isImporting={false}
          />
        )}

        {/* Phase: importing */}
        {jeState.phase === 'importing' && (
          <div className="card p-6">
            <div className="flex items-center gap-3 text-blue-600 dark:text-blue-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>仕訳データをインポート中...</span>
            </div>
          </div>
        )}

        {/* Phase: complete */}
        {jeState.phase === 'complete' && (
          <div className="card p-6">
            <div className="flex items-center gap-3 text-green-600 dark:text-green-400">
              <CheckCircle className="w-5 h-5" />
              <span>{jeState.importedCount.toLocaleString()} 件の仕訳を取り込みました</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

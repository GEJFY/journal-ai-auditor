/**
 * Search Page
 *
 * Journal entry search with filters for account, date, amount, user, and risk.
 */

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  FileText,
  Download,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

interface SearchFilters {
  fiscal_year: number;
  keyword: string;
  account: string;
  date_from: string;
  date_to: string;
  min_amount: string;
  max_amount: string;
  prepared_by: string;
  risk_score_min: string;
}

interface JournalEntry {
  gl_detail_id: string;
  journal_id: string;
  effective_date: string;
  gl_account_number: string;
  account_name: string;
  amount: number;
  debit_credit_indicator: string;
  description: string;
  prepared_by: string;
  approved_by: string;
  risk_score: number;
}

interface SearchResult {
  entries: JournalEntry[];
  total_count: number;
  page: number;
  page_size: number;
}

function makeDefaultFilters(fiscalYear: number): SearchFilters {
  return {
    fiscal_year: fiscalYear,
    keyword: '',
    account: '',
    date_from: '',
    date_to: '',
    min_amount: '',
    max_amount: '',
    prepared_by: '',
    risk_score_min: '',
  };
}

// =============================================================================
// Component
// =============================================================================

export default function SearchPage() {
  const [fiscalYear] = useFiscalYear();
  const [filters, setFilters] = useState<SearchFilters>(() => makeDefaultFilters(fiscalYear));
  const [submittedFilters, setSubmittedFilters] = useState<SearchFilters | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data, isLoading, isFetching } = useQuery<SearchResult>({
    queryKey: ['journal-search', submittedFilters, page],
    queryFn: async () => {
      if (!submittedFilters) return { entries: [], total_count: 0, page: 0, page_size: pageSize };
      const params = new URLSearchParams();
      params.append('fiscal_year', submittedFilters.fiscal_year.toString());
      params.append('limit', pageSize.toString());
      params.append('offset', (page * pageSize).toString());
      if (submittedFilters.keyword) params.append('keyword', submittedFilters.keyword);
      if (submittedFilters.account) params.append('account', submittedFilters.account);
      if (submittedFilters.date_from) params.append('date_from', submittedFilters.date_from);
      if (submittedFilters.date_to) params.append('date_to', submittedFilters.date_to);
      if (submittedFilters.min_amount) params.append('min_amount', submittedFilters.min_amount);
      if (submittedFilters.max_amount) params.append('max_amount', submittedFilters.max_amount);
      if (submittedFilters.prepared_by) params.append('prepared_by', submittedFilters.prepared_by);
      if (submittedFilters.risk_score_min)
        params.append('risk_score_min', submittedFilters.risk_score_min);

      const res = await fetch(`${API_BASE}/journals/search?${params}`);
      if (!res.ok) throw new Error(`Search failed: ${res.status}`);
      return res.json();
    },
    enabled: !!submittedFilters,
  });

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setPage(0);
      setSubmittedFilters({ ...filters });
    },
    [filters]
  );

  const handleReset = useCallback(() => {
    setFilters(makeDefaultFilters(fiscalYear));
    setSubmittedFilters(null);
    setPage(0);
  }, [fiscalYear]);

  const handleExportCsv = useCallback(() => {
    if (!submittedFilters) return;
    const params = new URLSearchParams();
    params.append('fiscal_year', submittedFilters.fiscal_year.toString());
    if (submittedFilters.keyword) params.append('keyword', submittedFilters.keyword);
    if (submittedFilters.account) params.append('account', submittedFilters.account);
    if (submittedFilters.date_from) params.append('date_from', submittedFilters.date_from);
    if (submittedFilters.date_to) params.append('date_to', submittedFilters.date_to);
    if (submittedFilters.min_amount) params.append('min_amount', submittedFilters.min_amount);
    if (submittedFilters.max_amount) params.append('max_amount', submittedFilters.max_amount);
    if (submittedFilters.prepared_by) params.append('prepared_by', submittedFilters.prepared_by);
    if (submittedFilters.risk_score_min)
      params.append('risk_score_min', submittedFilters.risk_score_min);
    window.open(`${API_BASE}/journals/export?${params}`, '_blank');
  }, [submittedFilters]);

  const riskBadge = (score: number) => {
    if (score >= 80) return 'badge badge-danger';
    if (score >= 50) return 'badge badge-warning';
    if (score >= 20) return 'badge badge-info';
    return 'badge badge-success';
  };

  const totalPages = data ? Math.ceil(data.total_count / pageSize) : 0;

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Search className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-neutral-900">仕訳検索</h2>
        </div>

        {/* Basic search */}
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            value={filters.keyword}
            onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
            placeholder="仕訳ID、摘要、勘定科目コードで検索..."
            className="input flex-1"
          />
          <button type="submit" className="btn btn-primary" disabled={isLoading}>
            <Search className="w-4 h-4" />
            検索
          </button>
          <button type="button" onClick={handleReset} className="btn btn-secondary">
            リセット
          </button>
        </div>

        {/* Advanced filters toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <Filter className="w-4 h-4" />
          詳細フィルター
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* Advanced filters */}
        {showAdvanced && (
          <div className="mt-4 pt-4 border-t border-neutral-200 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">勘定科目</label>
              <input
                type="text"
                value={filters.account}
                onChange={(e) => setFilters({ ...filters, account: e.target.value })}
                placeholder="科目コード"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">
                日付（開始）
              </label>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">
                日付（終了）
              </label>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">起票者</label>
              <input
                type="text"
                value={filters.prepared_by}
                onChange={(e) => setFilters({ ...filters, prepared_by: e.target.value })}
                placeholder="ユーザーID"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">
                金額（下限）
              </label>
              <input
                type="number"
                value={filters.min_amount}
                onChange={(e) => setFilters({ ...filters, min_amount: e.target.value })}
                placeholder="0"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">
                金額（上限）
              </label>
              <input
                type="number"
                value={filters.max_amount}
                onChange={(e) => setFilters({ ...filters, max_amount: e.target.value })}
                placeholder="上限なし"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-600 mb-1">
                リスクスコア（最小）
              </label>
              <input
                type="number"
                value={filters.risk_score_min}
                onChange={(e) => setFilters({ ...filters, risk_score_min: e.target.value })}
                placeholder="0"
                min="0"
                max="100"
                className="input"
              />
            </div>
          </div>
        )}
      </form>

      {/* Results */}
      {submittedFilters && (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-neutral-400" />
              <h3 className="font-semibold text-neutral-800">
                検索結果
                {data && (
                  <span className="ml-2 text-sm font-normal text-neutral-500">
                    ({data.total_count.toLocaleString()} 件)
                  </span>
                )}
              </h3>
            </div>
            {data && data.total_count > 0 && (
              <button className="btn btn-secondary btn-sm" onClick={handleExportCsv}>
                <Download className="w-4 h-4" />
                CSV出力
              </button>
            )}
          </div>
          <div className="card-body p-0">
            {isLoading || isFetching ? (
              <div className="flex items-center justify-center h-32">
                <div className="spinner" />
              </div>
            ) : data && data.entries.length > 0 ? (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-neutral-50 border-b border-neutral-200">
                        <th className="text-left px-4 py-3 font-medium text-neutral-600">仕訳ID</th>
                        <th className="text-left px-4 py-3 font-medium text-neutral-600">日付</th>
                        <th className="text-left px-4 py-3 font-medium text-neutral-600">
                          勘定科目
                        </th>
                        <th className="text-right px-4 py-3 font-medium text-neutral-600">借方</th>
                        <th className="text-right px-4 py-3 font-medium text-neutral-600">貸方</th>
                        <th className="text-left px-4 py-3 font-medium text-neutral-600">摘要</th>
                        <th className="text-left px-4 py-3 font-medium text-neutral-600">起票者</th>
                        <th className="text-center px-4 py-3 font-medium text-neutral-600">
                          リスク
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {data.entries.map((entry) => (
                        <tr
                          key={entry.gl_detail_id}
                          className="hover:bg-neutral-50 transition-colors"
                        >
                          <td className="px-4 py-3 font-mono text-xs">{entry.journal_id}</td>
                          <td className="px-4 py-3 whitespace-nowrap">{entry.effective_date}</td>
                          <td className="px-4 py-3">
                            <span className="font-mono text-xs">{entry.gl_account_number}</span>
                            {entry.account_name &&
                              entry.account_name !== entry.gl_account_number && (
                                <span className="ml-1 text-neutral-500">{entry.account_name}</span>
                              )}
                          </td>
                          <td className="px-4 py-3 text-right font-mono">
                            {entry.debit_credit_indicator === 'D'
                              ? `¥${entry.amount.toLocaleString()}`
                              : ''}
                          </td>
                          <td className="px-4 py-3 text-right font-mono">
                            {entry.debit_credit_indicator === 'C'
                              ? `¥${entry.amount.toLocaleString()}`
                              : ''}
                          </td>
                          <td className="px-4 py-3 max-w-[200px] truncate">
                            {entry.description || '-'}
                          </td>
                          <td className="px-4 py-3">{entry.prepared_by || '-'}</td>
                          <td className="px-4 py-3 text-center">
                            {entry.risk_score > 0 ? (
                              <span className={riskBadge(entry.risk_score)}>
                                {entry.risk_score >= 50 && (
                                  <AlertTriangle className="w-3 h-3 inline mr-1" />
                                )}
                                {entry.risk_score.toFixed(0)}
                              </span>
                            ) : (
                              <span className="text-neutral-300">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-200">
                    <span className="text-sm text-neutral-500">
                      {page * pageSize + 1} - {Math.min((page + 1) * pageSize, data.total_count)} /{' '}
                      {data.total_count.toLocaleString()} 件
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="btn btn-secondary btn-sm"
                      >
                        前へ
                      </button>
                      <button
                        onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                        className="btn btn-secondary btn-sm"
                      >
                        次へ
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state py-12">
                <Search className="empty-state-icon" />
                <p className="empty-state-title">該当する仕訳がありません</p>
                <p className="empty-state-description">検索条件を変更して再度お試しください</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Initial state */}
      {!submittedFilters && (
        <div className="card p-12 text-center">
          <Search className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
          <p className="text-neutral-500">検索条件を入力して仕訳データを検索してください</p>
          <p className="text-sm text-neutral-400 mt-2">
            仕訳ID、摘要、勘定科目コード、日付、金額、リスクスコアで絞り込みが可能です
          </p>
        </div>
      )}
    </div>
  );
}

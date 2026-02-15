/**
 * Accounts Analysis Page
 *
 * Account-level analysis with debit/credit breakdown and drill-down.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  RefreshCw,
  ArrowUpDown,
  BarChart3,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import clsx from 'clsx';

type SortKey = 'net_amount' | 'entry_count' | 'debit_total' | 'credit_total';
type SortDir = 'asc' | 'desc';

export default function AccountsPage() {
  const [fiscalYear] = useState(2024);
  const [sortKey, setSortKey] = useState<SortKey>('net_amount');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const {
    data: accountsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['accounts', fiscalYear],
    queryFn: () => api.getAccounts(fiscalYear, 100),
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sortedAccounts = (() => {
    if (!accountsData?.accounts) return [];
    return [...accountsData.accounts].sort((a, b) => {
      const aVal = Math.abs(a[sortKey]);
      const bVal = Math.abs(b[sortKey]);
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });
  })();

  // Top 10 for chart
  const chartData = sortedAccounts.slice(0, 10).map((a) => ({
    code: a.account_code,
    name: a.account_name || a.account_code,
    label:
      a.account_name && a.account_name !== a.account_code
        ? `${a.account_code} ${a.account_name}`
        : a.account_code,
    debit: a.debit_total,
    credit: a.credit_total,
    net: a.net_amount,
    count: a.entry_count,
  }));

  // Summary stats
  const stats = accountsData?.accounts
    ? {
        totalAccounts: accountsData.total_accounts,
        totalDebit: accountsData.accounts.reduce((s, a) => s + a.debit_total, 0),
        totalCredit: accountsData.accounts.reduce((s, a) => s + a.credit_total, 0),
        avgEntries: Math.round(
          accountsData.accounts.reduce((s, a) => s + a.entry_count, 0) /
            (accountsData.accounts.length || 1)
        ),
      }
    : null;

  const formatAmount = (v: number) => {
    const abs = Math.abs(v);
    if (abs >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
    if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(0)}M`;
    return `${(v / 1_000).toFixed(0)}K`;
  };

  const SortIcon = ({ col }: { col: SortKey }) => (
    <ArrowUpDown
      className={clsx(
        'w-3 h-3 ml-1 inline',
        sortKey === col ? 'text-primary-600' : 'text-neutral-300'
      )}
    />
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${fiscalYear}年度 勘定科目分析`}
        subtitle={`${accountsData?.total_accounts ?? 0} 科目の残高・取引分析`}
        actions={
          <button onClick={handleRefresh} disabled={isRefreshing} className="btn btn-secondary">
            <RefreshCw className={clsx('w-4 h-4', isRefreshing && 'animate-spin')} />
            更新
          </button>
        }
      />

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-sm text-neutral-500">科目数</p>
            <p className="text-2xl font-bold text-neutral-900">{stats.totalAccounts}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-neutral-500">借方合計</p>
            <p className="text-2xl font-bold text-blue-700">¥{formatAmount(stats.totalDebit)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-neutral-500">貸方合計</p>
            <p className="text-2xl font-bold text-red-700">¥{formatAmount(stats.totalCredit)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-neutral-500">平均仕訳件数/科目</p>
            <p className="text-2xl font-bold text-neutral-900">{stats.avgEntries}</p>
          </div>
        </div>
      )}

      {/* Top 10 Chart */}
      <div className="card">
        <div className="card-header flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-neutral-400" />
          <h3 className="font-semibold text-neutral-800">上位10科目（借方・貸方）</h3>
        </div>
        <div className="card-body">
          {isLoading ? (
            <div className="flex items-center justify-center h-80">
              <div className="spinner" />
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                <XAxis type="number" tickFormatter={(v) => `¥${formatAmount(v)}`} />
                <YAxis
                  dataKey="label"
                  type="category"
                  width={180}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => (v.length > 24 ? v.slice(0, 24) + '...' : v)}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [`¥${value.toLocaleString()}`, name]}
                />
                <Bar dataKey="debit" fill="#2563eb" name="借方" radius={[0, 4, 4, 0]} />
                <Bar dataKey="credit" fill="#dc2626" name="貸方" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state h-80">
              <BarChart3 className="empty-state-icon" />
              <p className="empty-state-title">データがありません</p>
            </div>
          )}
        </div>
      </div>

      {/* Accounts Table */}
      <div className="card">
        <div className="card-header flex items-center gap-2">
          <FileText className="w-5 h-5 text-neutral-400" />
          <h3 className="font-semibold text-neutral-800">勘定科目一覧</h3>
        </div>
        <div className="card-body p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="spinner" />
            </div>
          ) : sortedAccounts.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-neutral-50 border-b border-neutral-200">
                    <th className="text-left px-4 py-3 font-medium text-neutral-600">科目コード</th>
                    <th className="text-left px-4 py-3 font-medium text-neutral-600">科目名</th>
                    <th
                      className="text-right px-4 py-3 font-medium text-neutral-600 cursor-pointer hover:text-primary-600"
                      onClick={() => handleSort('debit_total')}
                    >
                      借方合計
                      <SortIcon col="debit_total" />
                    </th>
                    <th
                      className="text-right px-4 py-3 font-medium text-neutral-600 cursor-pointer hover:text-primary-600"
                      onClick={() => handleSort('credit_total')}
                    >
                      貸方合計
                      <SortIcon col="credit_total" />
                    </th>
                    <th
                      className="text-right px-4 py-3 font-medium text-neutral-600 cursor-pointer hover:text-primary-600"
                      onClick={() => handleSort('net_amount')}
                    >
                      差引残高
                      <SortIcon col="net_amount" />
                    </th>
                    <th
                      className="text-right px-4 py-3 font-medium text-neutral-600 cursor-pointer hover:text-primary-600"
                      onClick={() => handleSort('entry_count')}
                    >
                      仕訳件数
                      <SortIcon col="entry_count" />
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {sortedAccounts.map((account) => (
                    <tr
                      key={account.account_code}
                      className="hover:bg-neutral-50 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs">{account.account_code}</td>
                      <td className="px-4 py-3">
                        {account.account_name && account.account_name !== account.account_code
                          ? account.account_name
                          : '-'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-blue-700">
                        ¥{account.debit_total.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-red-700">
                        ¥{account.credit_total.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-medium">
                        <span className="flex items-center justify-end gap-1">
                          {account.net_amount > 0 ? (
                            <TrendingUp className="w-3 h-3 text-blue-500" />
                          ) : account.net_amount < 0 ? (
                            <TrendingDown className="w-3 h-3 text-red-500" />
                          ) : null}
                          ¥{account.net_amount.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {account.entry_count.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state py-12">
              <FileText className="empty-state-icon" />
              <p className="empty-state-title">勘定科目データがありません</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

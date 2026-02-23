/**
 * Accounts Analysis Page
 *
 * Account-level analysis with debit/credit breakdown and drill-down.
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import { FileText, RefreshCw, BarChart3, TrendingUp, TrendingDown } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { type ColumnDef } from '@tanstack/react-table';
import { api } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import { DataTable } from '@/components/ui/DataTable';
import clsx from 'clsx';

interface AccountItem {
  account_code: string;
  account_name: string;
  debit_total: number;
  credit_total: number;
  net_amount: number;
  entry_count: number;
}

export default function AccountsPage() {
  const [fiscalYear] = useFiscalYear();
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

  const accounts: AccountItem[] = accountsData?.accounts ?? [];

  const columns = useMemo<ColumnDef<AccountItem, any>[]>(
    () => [
      {
        accessorKey: 'account_code',
        header: '科目コード',
        cell: ({ getValue }) => <span className="font-mono text-xs">{getValue<string>()}</span>,
        enableSorting: false,
      },
      {
        accessorKey: 'account_name',
        header: '科目名',
        cell: ({ row }) => {
          const name = row.original.account_name;
          return name && name !== row.original.account_code ? name : '-';
        },
        enableSorting: false,
      },
      {
        accessorKey: 'debit_total',
        header: () => <span className="flex justify-end">借方合計</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end font-mono text-blue-700">
            ¥{getValue<number>().toLocaleString()}
          </span>
        ),
        sortingFn: (a, b) =>
          Math.abs(a.original.debit_total) - Math.abs(b.original.debit_total),
      },
      {
        accessorKey: 'credit_total',
        header: () => <span className="flex justify-end">貸方合計</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end font-mono text-red-700">
            ¥{getValue<number>().toLocaleString()}
          </span>
        ),
        sortingFn: (a, b) =>
          Math.abs(a.original.credit_total) - Math.abs(b.original.credit_total),
      },
      {
        accessorKey: 'net_amount',
        header: () => <span className="flex justify-end">差引残高</span>,
        cell: ({ row }) => (
          <span className="flex items-center justify-end gap-1 font-mono font-medium">
            {row.original.net_amount > 0 ? (
              <TrendingUp className="w-3 h-3 text-blue-500" />
            ) : row.original.net_amount < 0 ? (
              <TrendingDown className="w-3 h-3 text-red-500" />
            ) : null}
            ¥{row.original.net_amount.toLocaleString()}
          </span>
        ),
        sortingFn: (a, b) =>
          Math.abs(a.original.net_amount) - Math.abs(b.original.net_amount),
      },
      {
        accessorKey: 'entry_count',
        header: () => <span className="flex justify-end">仕訳件数</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end">{getValue<number>().toLocaleString()}</span>
        ),
      },
    ],
    []
  );

  // Top 10 for chart (sort by net_amount desc)
  const chartData = useMemo(() => {
    return [...accounts]
      .sort((a, b) => Math.abs(b.net_amount) - Math.abs(a.net_amount))
      .slice(0, 10)
      .map((a) => ({
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
  }, [accounts]);

  // Summary stats
  const stats = accounts.length > 0
    ? {
        totalAccounts: accountsData?.total_accounts ?? accounts.length,
        totalDebit: accounts.reduce((s, a) => s + a.debit_total, 0),
        totalCredit: accounts.reduce((s, a) => s + a.credit_total, 0),
        avgEntries: Math.round(
          accounts.reduce((s, a) => s + a.entry_count, 0) / accounts.length
        ),
      }
    : null;

  const formatAmount = (v: number) => {
    const abs = Math.abs(v);
    if (abs >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
    if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(0)}M`;
    return `${(v / 1_000).toFixed(0)}K`;
  };

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
          <DataTable
            columns={columns}
            data={accounts}
            isLoading={isLoading}
            emptyIcon={<FileText className="w-12 h-12 text-neutral-300" />}
            emptyTitle="勘定科目データがありません"
          />
        </div>
      </div>
    </div>
  );
}

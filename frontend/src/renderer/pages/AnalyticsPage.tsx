/**
 * Analytics Page
 *
 * Department, vendor, and account flow analysis.
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import {
  Building2,
  Users,
  ArrowRightLeft,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import { api, type DepartmentItem, type VendorItem, type AccountFlowItem } from '../lib/api';
import { DataTable } from '@/components/ui/DataTable';

type Tab = 'departments' | 'vendors' | 'account-flow';

function formatAmount(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) {
    return `¥${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `¥${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `¥${(value / 1_000).toFixed(0)}K`;
  }
  return `¥${value.toLocaleString()}`;
}

function riskBadge(score: number): string {
  if (score >= 60) return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
  if (score >= 40) return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
  if (score >= 20)
    return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300';
  return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
}

// =============================================================================
// Department Tab
// =============================================================================

function DepartmentsTab({ fiscalYear }: { fiscalYear: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['departments', fiscalYear],
    queryFn: () => api.getDepartments(fiscalYear, 50),
  });

  const columns = useMemo<ColumnDef<DepartmentItem, any>[]>(
    () => [
      {
        accessorKey: 'dept_code',
        header: '部門コード',
        cell: ({ getValue }) => (
          <span className="font-medium text-gray-900 dark:text-white">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: 'entry_count',
        header: () => <span className="flex justify-end">仕訳件数</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {getValue<number>().toLocaleString()}
          </span>
        ),
      },
      {
        accessorKey: 'total_debit',
        header: () => <span className="flex justify-end">借方合計</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'total_credit',
        header: () => <span className="flex justify-end">貸方合計</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'avg_risk_score',
        header: () => <span className="flex justify-end">平均リスク</span>,
        cell: ({ getValue }) => {
          const score = getValue<number>();
          return (
            <span className="flex justify-end">
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${riskBadge(score)}`}
              >
                {score.toFixed(1)}
              </span>
            </span>
          );
        },
      },
      {
        accessorKey: 'high_risk_count',
        header: () => <span className="flex justify-end">高リスク件数</span>,
        cell: ({ getValue }) => {
          const count = getValue<number>();
          return (
            <span className="flex justify-end">
              {count > 0 ? (
                <span className="text-red-600 dark:text-red-400 font-medium">{count}</span>
              ) : (
                <span className="text-gray-400">0</span>
              )}
            </span>
          );
        },
      },
      {
        accessorKey: 'self_approval_rate',
        header: () => <span className="flex justify-end">自己承認率</span>,
        cell: ({ getValue }) => {
          const rate = getValue<number>();
          return (
            <span className="flex justify-end">
              {rate > 0 ? (
                <span
                  className={
                    rate > 10
                      ? 'text-red-600 dark:text-red-400 font-medium'
                      : 'text-gray-700 dark:text-gray-300'
                  }
                >
                  {rate.toFixed(1)}%
                </span>
              ) : (
                <span className="text-gray-400">0%</span>
              )}
            </span>
          );
        },
      },
    ],
    []
  );

  if (error) {
    return (
      <div className="card p-6 text-center text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
        データの取得に失敗しました
      </div>
    );
  }

  const departments = data?.departments || [];

  return (
    <div className="card overflow-hidden">
      <DataTable
        columns={columns}
        data={departments}
        isLoading={isLoading}
        emptyIcon={<Building2 className="w-12 h-12 text-gray-300" />}
        emptyTitle="部門データがありません"
        footer={<>{data?.total || 0} 部門</>}
      />
    </div>
  );
}

// =============================================================================
// Vendor Tab
// =============================================================================

function VendorsTab({ fiscalYear }: { fiscalYear: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['vendors', fiscalYear],
    queryFn: () => api.getVendors(fiscalYear, 50),
  });

  const columns = useMemo<ColumnDef<VendorItem, any>[]>(
    () => [
      {
        accessorKey: 'vendor_code',
        header: '取引先コード',
        cell: ({ getValue }) => (
          <span className="font-medium text-gray-900 dark:text-white">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: 'entry_count',
        header: () => <span className="flex justify-end">取引件数</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {getValue<number>().toLocaleString()}
          </span>
        ),
      },
      {
        accessorKey: 'total_amount',
        header: () => <span className="flex justify-end">取引金額</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'avg_amount',
        header: () => <span className="flex justify-end">平均金額</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'max_amount',
        header: () => <span className="flex justify-end">最大金額</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'avg_risk_score',
        header: () => <span className="flex justify-end">平均リスク</span>,
        cell: ({ getValue }) => {
          const score = getValue<number>();
          return (
            <span className="flex justify-end">
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${riskBadge(score)}`}
              >
                {score.toFixed(1)}
              </span>
            </span>
          );
        },
      },
      {
        accessorKey: 'concentration_pct',
        header: () => <span className="flex justify-end">集中度</span>,
        cell: ({ getValue }) => {
          const pct = getValue<number>();
          return (
            <div className="flex items-center justify-end gap-1.5">
              <div className="w-16 h-2 bg-gray-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full"
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-10 text-right">{pct.toFixed(1)}%</span>
            </div>
          );
        },
      },
      {
        accessorKey: 'high_risk_count',
        header: () => <span className="flex justify-end">高リスク</span>,
        cell: ({ getValue }) => {
          const count = getValue<number>();
          return (
            <span className="flex justify-end">
              {count > 0 ? (
                <span className="text-red-600 dark:text-red-400 font-medium">{count}</span>
              ) : (
                <span className="text-gray-400">0</span>
              )}
            </span>
          );
        },
      },
    ],
    []
  );

  if (error) {
    return (
      <div className="card p-6 text-center text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
        データの取得に失敗しました
      </div>
    );
  }

  const vendors = data?.vendors || [];

  return (
    <div className="card overflow-hidden">
      <DataTable
        columns={columns}
        data={vendors}
        isLoading={isLoading}
        emptyIcon={<Users className="w-12 h-12 text-gray-300" />}
        emptyTitle="取引先データがありません"
        footer={<>{data?.total || 0} 取引先</>}
      />
    </div>
  );
}

// =============================================================================
// Account Flow Tab
// =============================================================================

function AccountFlowTab({ fiscalYear }: { fiscalYear: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['account-flow', fiscalYear],
    queryFn: () => api.getAccountFlow(fiscalYear, 0, 50),
  });

  const flows = data?.flows || [];
  const maxAmount = useMemo(
    () => (flows.length > 0 ? Math.max(...flows.map((f) => f.flow_amount)) : 0),
    [flows]
  );

  const columns = useMemo<ColumnDef<AccountFlowItem, any>[]>(
    () => [
      {
        accessorKey: 'source_account',
        header: '借方勘定',
        cell: ({ getValue }) => (
          <span className="inline-flex items-center gap-1.5">
            <TrendingDown className="w-3.5 h-3.5 text-blue-500" />
            <span className="font-mono font-medium text-gray-900 dark:text-white">
              {getValue<string>()}
            </span>
          </span>
        ),
        enableSorting: false,
      },
      {
        id: 'arrow',
        header: '',
        cell: () => <ArrowRightLeft className="w-4 h-4 text-gray-400 mx-auto" />,
        enableSorting: false,
        size: 48,
      },
      {
        accessorKey: 'target_account',
        header: '貸方勘定',
        cell: ({ getValue }) => (
          <span className="inline-flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-green-500" />
            <span className="font-mono font-medium text-gray-900 dark:text-white">
              {getValue<string>()}
            </span>
          </span>
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'transaction_count',
        header: () => <span className="flex justify-end">取引件数</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {getValue<number>().toLocaleString()}
          </span>
        ),
      },
      {
        accessorKey: 'flow_amount',
        header: () => <span className="flex justify-end">フロー金額</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end font-medium text-gray-900 dark:text-white">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'avg_amount',
        header: () => <span className="flex justify-end">平均金額</span>,
        cell: ({ getValue }) => (
          <span className="flex justify-end text-gray-700 dark:text-gray-300">
            {formatAmount(getValue<number>())}
          </span>
        ),
      },
      {
        id: 'ratio',
        header: '金額比率',
        cell: ({ row }) => (
          <div className="w-full h-2 bg-gray-200 dark:bg-neutral-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full transition-all"
              style={{
                width: `${maxAmount > 0 ? (row.original.flow_amount / maxAmount) * 100 : 0}%`,
              }}
            />
          </div>
        ),
        enableSorting: false,
        size: 128,
      },
    ],
    [maxAmount]
  );

  if (error) {
    return (
      <div className="card p-6 text-center text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
        データの取得に失敗しました
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <DataTable
        columns={columns}
        data={flows}
        isLoading={isLoading}
        emptyIcon={<ArrowRightLeft className="w-12 h-12 text-gray-300" />}
        emptyTitle="勘定科目フローデータがありません"
        footer={<>{data?.total || 0} フロー</>}
      />
    </div>
  );
}

// =============================================================================
// Main Page
// =============================================================================

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'departments', label: '部門分析', icon: <Building2 size={18} /> },
  { key: 'vendors', label: '取引先分析', icon: <Users size={18} /> },
  { key: 'account-flow', label: '勘定科目フロー', icon: <ArrowRightLeft size={18} /> },
];

export default function AnalyticsPage() {
  const [fiscalYear] = useFiscalYear();
  const [activeTab, setActiveTab] = useState<Tab>('departments');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">詳細分析</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {fiscalYear}年度の部門・取引先・勘定科目フロー分析
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-neutral-700">
        <nav className="flex gap-1" aria-label="分析タブ">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-primary-600 text-primary-700 dark:text-primary-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'departments' && <DepartmentsTab fiscalYear={fiscalYear} />}
      {activeTab === 'vendors' && <VendorsTab fiscalYear={fiscalYear} />}
      {activeTab === 'account-flow' && <AccountFlowTab fiscalYear={fiscalYear} />}
    </div>
  );
}

/**
 * Time Series Analysis Page
 *
 * Monthly/weekly/daily trend analysis with interactive charts.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import {
  TrendingUp,
  Calendar,
  BarChart3,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import { api, type PeriodComparisonItem } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import { DataTable } from '@/components/ui/DataTable';
import clsx from 'clsx';

type Aggregation = 'daily' | 'weekly' | 'monthly';
type ComparisonType = 'mom' | 'yoy';

const CHART_COLORS = {
  amount: '#102a43',
  count: '#319795',
  debit: '#2563eb',
  credit: '#dc2626',
  area: 'rgba(16, 42, 67, 0.1)',
};

// =============================================================================
// Period Comparison Table
// =============================================================================

const comparisonColumns: ColumnDef<PeriodComparisonItem, any>[] = [
  {
    accessorKey: 'account_code',
    header: '勘定科目',
    cell: ({ row }) => (
      <>
        <span className="text-neutral-500 text-xs mr-1">{row.original.account_code}</span>
        {row.original.account_name}
      </>
    ),
    enableSorting: false,
  },
  {
    accessorKey: 'current_amount',
    header: () => <span className="flex justify-end">当期</span>,
    cell: ({ getValue }) => (
      <span className="flex justify-end">¥{getValue<number>().toLocaleString()}</span>
    ),
  },
  {
    accessorKey: 'previous_amount',
    header: () => <span className="flex justify-end">前期</span>,
    cell: ({ getValue }) => (
      <span className="flex justify-end">¥{getValue<number>().toLocaleString()}</span>
    ),
  },
  {
    accessorKey: 'change_amount',
    header: () => <span className="flex justify-end">増減額</span>,
    cell: ({ getValue }) => {
      const amount = getValue<number>();
      return (
        <span
          className={clsx(
            'flex items-center justify-end gap-0.5 font-medium',
            amount > 0 ? 'text-red-600' : amount < 0 ? 'text-green-600' : 'text-neutral-500'
          )}
        >
          {amount > 0 ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : amount < 0 ? (
            <ArrowDownRight className="w-3 h-3" />
          ) : null}
          ¥{Math.abs(amount).toLocaleString()}
        </span>
      );
    },
  },
  {
    accessorKey: 'change_percent',
    header: () => <span className="flex justify-end">増減率</span>,
    cell: ({ getValue }) => {
      const pct = getValue<number | null>();
      return (
        <span
          className={clsx(
            'flex justify-end',
            pct !== null && pct > 0
              ? 'text-red-600'
              : pct !== null && pct < 0
                ? 'text-green-600'
                : 'text-neutral-500'
          )}
        >
          {pct !== null ? `${pct.toFixed(1)}%` : '-'}
        </span>
      );
    },
  },
];

function ComparisonTable({
  items,
  isLoading,
  currentPeriod,
  previousPeriod,
}: {
  items: PeriodComparisonItem[];
  isLoading: boolean;
  currentPeriod?: string;
  previousPeriod?: string;
}) {
  if (!isLoading && items.length === 0) {
    return (
      <div className="text-center py-8 text-neutral-500">
        {previousPeriod === 'N/A'
          ? '第1期には前月比較データがありません'
          : '比較データがありません'}
      </div>
    );
  }

  return (
    <div>
      {currentPeriod && previousPeriod && items.length > 0 && (
        <div className="text-sm text-neutral-500 mb-3">
          {currentPeriod} vs {previousPeriod}
        </div>
      )}
      <DataTable
        columns={comparisonColumns}
        data={items}
        isLoading={isLoading}
        enableSorting={false}
        emptyTitle="比較データがありません"
      />
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export default function TimeSeriesPage() {
  const [fiscalYear] = useFiscalYear();
  const [aggregation, setAggregation] = useState<Aggregation>('monthly');
  const [chartType, setChartType] = useState<'area' | 'bar' | 'line'>('area');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [comparisonType, setComparisonType] = useState<ComparisonType>('mom');
  const [comparisonPeriod, setComparisonPeriod] = useState(6);

  const {
    data: timeSeries,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['timeseries', fiscalYear, aggregation],
    queryFn: () => api.getTimeSeries(fiscalYear, aggregation),
  });

  const { data: comparison, isLoading: comparisonLoading } = useQuery({
    queryKey: ['period-comparison', fiscalYear, comparisonPeriod, comparisonType],
    queryFn: () => api.getPeriodComparison(fiscalYear, comparisonPeriod, comparisonType, 20),
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  // Calculate period-over-period changes
  const periodStats = (() => {
    if (!timeSeries?.data || timeSeries.data.length < 2) return null;
    const data = timeSeries.data;
    const latest = data[data.length - 1];
    const prev = data[data.length - 2];
    const amountChange = prev.amount ? ((latest.amount - prev.amount) / prev.amount) * 100 : 0;
    const countChange = prev.count ? ((latest.count - prev.count) / prev.count) * 100 : 0;
    return { latest, prev, amountChange, countChange };
  })();

  const formatDate = (value: string) => {
    const d = new Date(value);
    if (aggregation === 'monthly') return `${d.getMonth() + 1}月`;
    if (aggregation === 'weekly') return `${d.getMonth() + 1}/${d.getDate()}`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };

  const formatAmount = (value: number) => {
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(0)}M`;
    return `${(value / 1_000).toFixed(0)}K`;
  };

  const renderChart = () => {
    if (!timeSeries?.data || timeSeries.data.length === 0) {
      return (
        <div className="empty-state h-80">
          <BarChart3 className="empty-state-icon" />
          <p className="empty-state-title">データがありません</p>
          <p className="empty-state-description">仕訳データを取り込んでから分析してください</p>
        </div>
      );
    }

    const commonProps = {
      data: timeSeries.data,
    };

    if (chartType === 'bar') {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={formatAmount} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value: number, name: string) => [
                name === 'count' ? value.toLocaleString() : `¥${value.toLocaleString()}`,
                name === 'count' ? '件数' : '金額',
              ]}
              labelFormatter={(label) => new Date(label).toLocaleDateString('ja-JP')}
            />
            <Legend />
            <Bar dataKey="amount" fill={CHART_COLORS.amount} name="金額" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      );
    }

    if (chartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" tickFormatter={formatAmount} tick={{ fontSize: 12 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value: number, name: string) => [
                name === '件数' ? value.toLocaleString() : `¥${value.toLocaleString()}`,
                name,
              ]}
              labelFormatter={(label) => new Date(label).toLocaleDateString('ja-JP')}
            />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="amount"
              stroke={CHART_COLORS.amount}
              strokeWidth={2}
              dot={{ r: 4 }}
              name="金額"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="count"
              stroke={CHART_COLORS.count}
              strokeWidth={2}
              dot={{ r: 4 }}
              name="件数"
            />
          </LineChart>
        </ResponsiveContainer>
      );
    }

    // Default: area
    return (
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart {...commonProps}>
          <defs>
            <linearGradient id="tsColorAmount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.amount} stopOpacity={0.15} />
              <stop offset="95%" stopColor={CHART_COLORS.amount} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={formatAmount} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: number) => [`¥${value.toLocaleString()}`, '金額']}
            labelFormatter={(label) => new Date(label).toLocaleDateString('ja-JP')}
          />
          <Area
            type="monotone"
            dataKey="amount"
            stroke={CHART_COLORS.amount}
            strokeWidth={2}
            fill="url(#tsColorAmount)"
            name="取引金額"
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${fiscalYear}年度 時系列分析`}
        subtitle="仕訳データの月次・週次・日次トレンドを分析"
        actions={
          <button onClick={handleRefresh} disabled={isRefreshing} className="btn btn-secondary">
            <RefreshCw className={clsx('w-4 h-4', isRefreshing && 'animate-spin')} />
            更新
          </button>
        }
      />

      {/* Period Stats */}
      {periodStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-sm text-neutral-500">最新期間の金額</p>
            <p className="text-2xl font-bold text-neutral-900">
              ¥{formatAmount(periodStats.latest.amount)}
            </p>
            <div
              className={clsx(
                'flex items-center gap-1 text-sm mt-1',
                periodStats.amountChange >= 0 ? 'text-red-600' : 'text-green-600'
              )}
            >
              {periodStats.amountChange >= 0 ? (
                <ArrowUpRight className="w-4 h-4" />
              ) : (
                <ArrowDownRight className="w-4 h-4" />
              )}
              {Math.abs(periodStats.amountChange).toFixed(1)}%
            </div>
          </div>
          <div className="card p-4">
            <p className="text-sm text-neutral-500">最新期間の件数</p>
            <p className="text-2xl font-bold text-neutral-900">
              {periodStats.latest.count.toLocaleString()}
            </p>
            <div
              className={clsx(
                'flex items-center gap-1 text-sm mt-1',
                periodStats.countChange >= 0 ? 'text-blue-600' : 'text-neutral-500'
              )}
            >
              {periodStats.countChange >= 0 ? (
                <ArrowUpRight className="w-4 h-4" />
              ) : (
                <ArrowDownRight className="w-4 h-4" />
              )}
              {Math.abs(periodStats.countChange).toFixed(1)}%
            </div>
          </div>
          <div className="card p-4">
            <p className="text-sm text-neutral-500">期間合計金額</p>
            <p className="text-2xl font-bold text-neutral-900">
              ¥{formatAmount(timeSeries?.data.reduce((sum, d) => sum + d.amount, 0) || 0)}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-neutral-500">期間合計件数</p>
            <p className="text-2xl font-bold text-neutral-900">
              {(timeSeries?.data.reduce((sum, d) => sum + d.count, 0) || 0).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Chart Controls & Chart */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-neutral-400" />
            <h3 className="font-semibold text-neutral-800">トレンドチャート</h3>
          </div>
          <div className="flex gap-2">
            {/* Aggregation toggle */}
            <div className="flex bg-neutral-100 rounded-lg p-0.5">
              {(['monthly', 'weekly', 'daily'] as Aggregation[]).map((agg) => (
                <button
                  key={agg}
                  onClick={() => setAggregation(agg)}
                  className={clsx(
                    'px-3 py-1 rounded-md text-sm transition-colors',
                    aggregation === agg
                      ? 'bg-white shadow-sm text-neutral-900 font-medium'
                      : 'text-neutral-500 hover:text-neutral-700'
                  )}
                >
                  {agg === 'monthly' ? '月次' : agg === 'weekly' ? '週次' : '日次'}
                </button>
              ))}
            </div>

            {/* Chart type toggle */}
            <div className="flex bg-neutral-100 rounded-lg p-0.5">
              {(['area', 'bar', 'line'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setChartType(type)}
                  className={clsx(
                    'px-3 py-1 rounded-md text-sm transition-colors',
                    chartType === type
                      ? 'bg-white shadow-sm text-neutral-900 font-medium'
                      : 'text-neutral-500 hover:text-neutral-700'
                  )}
                >
                  {type === 'area' ? 'エリア' : type === 'bar' ? '棒' : '折線'}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="card-body">
          {isLoading ? (
            <div className="flex items-center justify-center h-80">
              <div className="spinner" />
            </div>
          ) : (
            renderChart()
          )}
        </div>
      </div>

      {/* Debit/Credit Breakdown */}
      {timeSeries?.data && timeSeries.data.length > 0 && (
        <div className="card">
          <div className="card-header flex items-center gap-2">
            <Calendar className="w-5 h-5 text-neutral-400" />
            <h3 className="font-semibold text-neutral-800">借方・貸方の推移</h3>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={timeSeries.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={formatAmount} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number, name: string) => [`¥${value.toLocaleString()}`, name]}
                  labelFormatter={(label) => new Date(label).toLocaleDateString('ja-JP')}
                />
                <Legend />
                <Bar dataKey="debit" fill={CHART_COLORS.debit} name="借方" radius={[4, 4, 0, 0]} />
                <Bar
                  dataKey="credit"
                  fill={CHART_COLORS.credit}
                  name="貸方"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Period Comparison */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-neutral-400" />
            <h3 className="font-semibold text-neutral-800">期間比較</h3>
          </div>
          <div className="flex gap-2 items-center">
            <select
              value={comparisonPeriod}
              onChange={(e) => setComparisonPeriod(Number(e.target.value))}
              className="input text-sm py-1 w-24"
            >
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>
                  第{i + 1}期
                </option>
              ))}
            </select>
            <div className="flex bg-neutral-100 rounded-lg p-0.5">
              {(['mom', 'yoy'] as ComparisonType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => setComparisonType(type)}
                  className={clsx(
                    'px-3 py-1 rounded-md text-sm transition-colors',
                    comparisonType === type
                      ? 'bg-white shadow-sm text-neutral-900 font-medium'
                      : 'text-neutral-500 hover:text-neutral-700'
                  )}
                >
                  {type === 'mom' ? '前月比' : '前年比'}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="card-body">
          <ComparisonTable
            items={comparison?.items ?? []}
            isLoading={comparisonLoading}
            currentPeriod={comparison?.current_period}
            previousPeriod={comparison?.previous_period}
          />
        </div>
      </div>
    </div>
  );
}

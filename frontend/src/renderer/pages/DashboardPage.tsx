/**
 * Dashboard Page
 *
 * Professional consulting-style dashboard with summary statistics and charts.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import {
  FileText,
  TrendingUp,
  AlertTriangle,
  Users,
  RefreshCw,
  ArrowRight,
  Shield,
  BarChart3,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';
import { api } from '../lib/api';
import PageHeader from '../components/ui/PageHeader';
import StatCard from '../components/dashboard/StatCard';
import HelpTooltip from '../components/ui/HelpTooltip';
import clsx from 'clsx';

// Professional color palette
const RISK_COLORS = {
  high: '#c81e1e',
  medium: '#3f83f8',
  low: '#0e9f6e',
  minimal: '#9ca3af',
};

const CHART_COLORS = {
  primary: '#102a43',
  secondary: '#319795',
  area: 'rgba(16, 42, 67, 0.1)',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [fiscalYear] = useFiscalYear();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const {
    data: summary,
    isLoading: summaryLoading,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['dashboard', 'summary', fiscalYear],
    queryFn: () => api.getDashboardSummary(fiscalYear),
  });

  const { data: timeSeries, isLoading: timeSeriesLoading } = useQuery({
    queryKey: ['dashboard', 'timeseries', fiscalYear],
    queryFn: () => api.getTimeSeries(fiscalYear, 'monthly'),
  });

  const { data: kpi } = useQuery({
    queryKey: ['dashboard', 'kpi', fiscalYear],
    queryFn: () => api.getKPI(fiscalYear),
  });

  const { data: risk } = useQuery({
    queryKey: ['dashboard', 'risk', fiscalYear],
    queryFn: () => api.getRiskAnalysis(fiscalYear),
  });

  const { data: benford } = useQuery({
    queryKey: ['dashboard', 'benford', fiscalYear],
    queryFn: () => api.getBenford(fiscalYear),
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetchSummary();
    setIsRefreshing(false);
  };

  if (summaryLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-neutral-500">データを読み込んでいます...</p>
        </div>
      </div>
    );
  }

  const riskPieData = risk
    ? [
        { name: '高リスク', value: risk.risk_distribution.high, color: RISK_COLORS.high },
        { name: '中リスク', value: risk.risk_distribution.medium, color: RISK_COLORS.medium },
        { name: '低リスク', value: risk.risk_distribution.low, color: RISK_COLORS.low },
        { name: '最小', value: risk.risk_distribution.minimal, color: RISK_COLORS.minimal },
      ].filter((d) => d.value > 0)
    : [];

  const benfordConformityLabel: Record<string, string> = {
    close: '適合',
    acceptable: '許容範囲',
    marginally_acceptable: '境界',
    nonconforming: '不適合',
  };

  const benfordConformityColor: Record<string, string> = {
    close: 'badge-success',
    acceptable: 'badge-success',
    marginally_acceptable: 'badge-warning',
    nonconforming: 'badge-danger',
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <PageHeader
        title={`${fiscalYear}年度 分析ダッシュボード`}
        subtitle={
          summary?.date_range
            ? `対象期間: ${summary.date_range.from} ～ ${summary.date_range.to}`
            : undefined
        }
        actions={
          <button onClick={handleRefresh} disabled={isRefreshing} className="btn btn-secondary">
            <RefreshCw className={clsx('w-4 h-4', isRefreshing && 'animate-spin')} />
            更新
          </button>
        }
      />

      {/* Executive Summary Banner */}
      {summary && kpi && (
        <div className="card bg-gradient-to-r from-primary-900 to-primary-700 text-white p-6">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-2">エグゼクティブサマリー</h3>
              <p className="text-primary-100 max-w-2xl">
                {fiscalYear}年度の仕訳データ {summary.total_entries.toLocaleString()}
                件を分析しました。 高リスク仕訳が {summary.high_risk_count.toLocaleString()}件 (
                {kpi.high_risk_pct.toFixed(1)}%) 検出されています。詳細な調査を推奨します。
              </p>
            </div>
            <button
              className="btn bg-white/10 text-white hover:bg-white/20 border-0"
              onClick={() => navigate('/reports')}
            >
              詳細レポート
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="仕訳件数"
          value={(summary?.total_entries || 0).toLocaleString()}
          subtitle={`${(kpi?.total_journals || 0).toLocaleString()} 仕訳帳票`}
          icon={<FileText className="w-6 h-6 text-primary-600" />}
          iconBgColor="bg-primary-100"
        />
        <StatCard
          title="総取引金額"
          value={`¥${((summary?.total_amount || 0) / 1000000000).toFixed(1)}B`}
          subtitle="億円単位"
          icon={<TrendingUp className="w-6 h-6 text-accent-600" />}
          iconBgColor="bg-accent-100"
        />
        <StatCard
          title="高リスク項目"
          value={(summary?.high_risk_count || 0).toLocaleString()}
          subtitle={kpi ? `全体の ${kpi.high_risk_pct.toFixed(1)}%` : ''}
          icon={<AlertTriangle className="w-6 h-6 text-risk-critical" />}
          iconBgColor="bg-red-50"
          variant="danger"
        />
        <StatCard
          title="自己承認"
          value={(kpi?.self_approval_count || 0).toLocaleString()}
          subtitle="要確認項目"
          icon={<Users className="w-6 h-6 text-risk-high" />}
          iconBgColor="bg-amber-50"
          variant="warning"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Time Series Chart */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 size={20} className="text-neutral-400" />
              <h3 className="font-semibold text-neutral-800">月次推移</h3>
            </div>
            <HelpTooltip id="dashboard-timeseries" position="left" />
          </div>
          <div className="card-body">
            {timeSeriesLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="spinner" />
              </div>
            ) : timeSeries?.data && timeSeries.data.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={timeSeries.data}>
                  <defs>
                    <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.15} />
                      <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return `${date.getMonth() + 1}月`;
                    }}
                    tick={{ fill: '#737373', fontSize: 12 }}
                    axisLine={{ stroke: '#e5e5e5' }}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(value) => `${(value / 1000000).toFixed(0)}M`}
                    tick={{ fill: '#737373', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(value: number) => [`¥${value.toLocaleString()}`, '金額']}
                    labelFormatter={(label) => new Date(label).toLocaleDateString('ja-JP')}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e5e5',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="amount"
                    stroke={CHART_COLORS.primary}
                    strokeWidth={2}
                    fill="url(#colorAmount)"
                    name="取引金額"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state h-64">
                <BarChart3 className="empty-state-icon" />
                <p className="empty-state-title">データがありません</p>
              </div>
            )}
          </div>
        </div>

        {/* Risk Distribution */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield size={20} className="text-neutral-400" />
              <h3 className="font-semibold text-neutral-800">リスク分布</h3>
            </div>
            <HelpTooltip id="dashboard-risk-distribution" position="left" />
          </div>
          <div className="card-body">
            {riskPieData.length > 0 ? (
              <div className="flex items-center">
                <ResponsiveContainer width="60%" height={280}>
                  <PieChart>
                    <Pie
                      data={riskPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={110}
                      dataKey="value"
                      paddingAngle={2}
                    >
                      {riskPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => [value.toLocaleString(), '件数']} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="w-40 space-y-3">
                  {riskPieData.map((item, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-neutral-700">{item.name}</p>
                        <p className="text-xs text-neutral-500">{item.value.toLocaleString()}件</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state h-64">
                <Shield className="empty-state-icon" />
                <p className="empty-state-title">データがありません</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* KPI Summary */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-neutral-800">KPIサマリー</h3>
          </div>
          <div className="card-body space-y-4">
            {[
              { label: '仕訳帳票数', value: (kpi?.total_journals || 0).toLocaleString() },
              { label: 'ユニーク勘定', value: (kpi?.unique_accounts || 0).toLocaleString() },
              { label: 'ユニークユーザー', value: (kpi?.unique_users || 0).toLocaleString() },
              { label: '平均リスクスコア', value: (kpi?.avg_risk_score || 0).toFixed(1) },
            ].map((item, index) => (
              <div
                key={index}
                className="flex justify-between items-center py-2 border-b border-neutral-100 last:border-0"
              >
                <span className="text-neutral-600">{item.label}</span>
                <span className="font-semibold text-neutral-900">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Benford Analysis */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h3 className="font-semibold text-neutral-800">ベンフォード分析</h3>
            <HelpTooltip id="benford-analysis" position="left" />
          </div>
          <div className="card-body">
            {benford?.distribution && benford.distribution.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={benford.distribution} barGap={2}>
                    <XAxis
                      dataKey="digit"
                      tick={{ fill: '#737373', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                      tick={{ fill: '#737373', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, '']}
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e5e5',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar
                      dataKey="actual_pct"
                      fill={CHART_COLORS.primary}
                      radius={[2, 2, 0, 0]}
                      name="実績"
                    />
                    <Bar
                      dataKey="expected_pct"
                      fill="#d4d4d4"
                      radius={[2, 2, 0, 0]}
                      name="期待値"
                    />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-4 pt-4 border-t border-neutral-100 flex items-center justify-between">
                  <span className="text-neutral-600">適合度判定</span>
                  <span className={clsx('badge', benfordConformityColor[benford.conformity])}>
                    {benfordConformityLabel[benford.conformity]}
                  </span>
                </div>
              </>
            ) : (
              <div className="empty-state h-48">
                <BarChart3 className="empty-state-icon" />
                <p className="empty-state-title">データがありません</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent High Risk */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h3 className="font-semibold text-neutral-800">高リスク仕訳（上位5件）</h3>
            <button
              className="text-sm text-accent-600 hover:text-accent-700 font-medium"
              onClick={() => navigate('/risk')}
            >
              すべて表示
            </button>
          </div>
          <div className="card-body">
            {risk?.high_risk && risk.high_risk.length > 0 ? (
              <div className="space-y-3">
                {risk.high_risk.slice(0, 5).map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors cursor-pointer"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-neutral-800 truncate">
                        {item.journal_id}
                      </p>
                      <p className="text-xs text-neutral-500">¥{item.amount.toLocaleString()}</p>
                    </div>
                    <div className="ml-3">
                      <span className="badge badge-risk-critical">
                        {item.risk_score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state h-48">
                <Shield className="empty-state-icon" />
                <p className="empty-state-title">高リスク仕訳なし</p>
                <p className="empty-state-description">検出された高リスク仕訳はありません</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

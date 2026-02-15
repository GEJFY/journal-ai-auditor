/**
 * Risk Analysis Page
 *
 * Displays risk analysis results with detailed views.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import { AlertTriangle, AlertCircle, Info, ChevronRight, Filter } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { api, type RiskItem } from '../lib/api';

const RISK_COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
  minimal: '#94a3b8',
};

interface RiskCardProps {
  item: RiskItem;
  level: 'high' | 'medium' | 'low';
}

function RiskCard({ item, level }: RiskCardProps) {
  const colors = {
    high: 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20',
    medium: 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20',
    low: 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20',
  };

  const icons = {
    high: <AlertTriangle className="w-5 h-5 text-red-600" />,
    medium: <AlertCircle className="w-5 h-5 text-yellow-600" />,
    low: <Info className="w-5 h-5 text-green-600" />,
  };

  return (
    <div className={`border rounded-lg p-4 ${colors[level]}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          {icons[level]}
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{item.journal_id}</p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {item.description || '説明なし'}
            </p>
            <div className="flex flex-wrap gap-1 mt-2">
              {item.risk_factors.slice(0, 3).map((factor, i) => (
                <span key={i} className="px-2 py-0.5 bg-white dark:bg-gray-800 rounded text-xs">
                  {factor}
                </span>
              ))}
              {item.risk_factors.length > 3 && (
                <span className="px-2 py-0.5 text-xs text-gray-500">
                  +{item.risk_factors.length - 3}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold">{item.risk_score.toFixed(0)}</div>
          <div className="text-sm text-gray-500">¥{item.amount.toLocaleString()}</div>
          <div className="text-xs text-gray-400">{item.date}</div>
        </div>
      </div>
    </div>
  );
}

export default function RiskPage() {
  const [fiscalYear] = useFiscalYear();
  const [selectedLevel, setSelectedLevel] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const { data: riskData, isLoading } = useQuery({
    queryKey: ['risk', fiscalYear],
    queryFn: () => api.getRiskAnalysis(fiscalYear),
  });

  const { data: violationsData } = useQuery({
    queryKey: ['violations', fiscalYear],
    queryFn: () => api.getViolations(fiscalYear, { limit: 100 }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  const distributionData = riskData
    ? [
        { name: '高リスク', value: riskData.risk_distribution.high, color: RISK_COLORS.high },
        { name: '中リスク', value: riskData.risk_distribution.medium, color: RISK_COLORS.medium },
        { name: '低リスク', value: riskData.risk_distribution.low, color: RISK_COLORS.low },
        { name: '最小', value: riskData.risk_distribution.minimal, color: RISK_COLORS.minimal },
      ]
    : [];

  const filteredItems = (() => {
    if (!riskData) return [];
    if (selectedLevel === 'all') {
      return [
        ...riskData.high_risk.map((item) => ({ ...item, level: 'high' as const })),
        ...riskData.medium_risk.map((item) => ({ ...item, level: 'medium' as const })),
        ...riskData.low_risk.map((item) => ({ ...item, level: 'low' as const })),
      ].sort((a, b) => b.risk_score - a.risk_score);
    }
    const items = riskData[`${selectedLevel}_risk` as keyof typeof riskData] as RiskItem[];
    return items.map((item) => ({ ...item, level: selectedLevel }));
  })();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">リスク分析</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {fiscalYear}年度の仕訳リスク評価
          </p>
        </div>
      </div>

      {/* Distribution Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">リスク分布</h3>
          {distributionData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={distributionData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={80} />
                <Tooltip formatter={(value: number) => [value.toLocaleString(), '件数']} />
                <Bar dataKey="value">
                  {distributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              データがありません
            </div>
          )}
        </div>

        {/* Violation Summary */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">違反サマリー</h3>
          {violationsData ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                  <p className="text-sm text-gray-500">総違反件数</p>
                  <p className="text-2xl font-bold">
                    {violationsData.total_count.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                  <p className="text-sm text-gray-500">カテゴリ数</p>
                  <p className="text-2xl font-bold">
                    {Object.keys(violationsData.by_category).length}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-2">深刻度別</p>
                <div className="space-y-2">
                  {Object.entries(violationsData.by_severity).map(([severity, count]) => (
                    <div key={severity} className="flex justify-between items-center">
                      <span className="text-sm capitalize">{severity}</span>
                      <span className="font-medium">{count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              データがありません
            </div>
          )}
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-gray-500" />
        <span className="text-sm text-gray-500">フィルター:</span>
        {(['all', 'high', 'medium', 'low'] as const).map((level) => (
          <button
            key={level}
            onClick={() => setSelectedLevel(level)}
            className={`px-3 py-1 rounded-full text-sm ${
              selectedLevel === level
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {level === 'all'
              ? 'すべて'
              : level === 'high'
                ? '高'
                : level === 'medium'
                  ? '中'
                  : '低'}
          </button>
        ))}
      </div>

      {/* Risk Items List */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          リスク項目一覧 ({filteredItems.length}件)
        </h3>
        {filteredItems.length > 0 ? (
          <div className="space-y-3">
            {filteredItems.slice(0, 20).map((item, index) => (
              <RiskCard key={index} item={item} level={item.level} />
            ))}
            {filteredItems.length > 20 && (
              <div className="text-center py-4">
                <button className="btn-secondary">
                  さらに表示
                  <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="card p-8 text-center text-gray-500">該当するリスク項目がありません</div>
        )}
      </div>
    </div>
  );
}



import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';
import HelpTooltip from '../ui/HelpTooltip';

interface FinancialMetricsWidgetProps {
    fiscalYear: number;
}

const COLORS = {
    revenue: '#10B981', // Emerald 500
    expense: '#EF4444', // Red 500
    profit: '#3B82F6',  // Blue 500
    asset: '#3B82F6',
    liability: '#EF4444',
    equity: '#10B981',
};

export default function FinancialMetricsWidget({ fiscalYear }: FinancialMetricsWidgetProps) {
    const { data, isLoading, error } = useQuery({
        queryKey: ['financial-metrics', fiscalYear],
        queryFn: () => api.getFinancialMetrics(fiscalYear),
    });

    if (isLoading) {
        return (
            <div className="card h-96 flex items-center justify-center">
                <div className="spinner" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="card h-96 flex items-center justify-center text-red-500">
                <p>データの読み込みに失敗しました。</p>
            </div>
        );
    }

    const { pl_metrics, bs_metrics } = data;

    // PL Data for Chart
    // We want to show Revenue, Expenses, and Operating Income
    const revenue = pl_metrics.find(m => m.label === 'Net Sales')?.amount || 0;
    const costOfSales = pl_metrics.find(m => m.label === 'Cost of Sales')?.amount || 0;
    const expenses = pl_metrics.find(m => m.label === 'Operating Expenses')?.amount || 0;
    const operatingIncome = pl_metrics.find(m => m.label === 'Operating Income')?.amount || 0;

    // Custom PL Waterfall-like data
    const plChartData = [
        { name: '売上高', value: revenue, color: COLORS.revenue },
        { name: '売上原価', value: costOfSales, color: COLORS.expense },
        { name: '販管費', value: expenses, color: COLORS.expense },
        { name: '営業利益', value: operatingIncome, color: COLORS.profit },
    ];

    // BS Data for Composition
    const totalLiabilitiesAndEquity = bs_metrics.liabilities + bs_metrics.equity;

    // Avoid division by zero
    const liabilityPct = totalLiabilitiesAndEquity ? (bs_metrics.liabilities / totalLiabilitiesAndEquity) * 100 : 0;
    const equityPct = totalLiabilitiesAndEquity ? (bs_metrics.equity / totalLiabilitiesAndEquity) * 100 : 0;

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* PL Summary */}
                <div className="card">
                    <div className="card-header flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <TrendingUp size={20} className="text-neutral-400" />
                            <h3 className="font-semibold text-neutral-800">損益サマリー (P/L)</h3>
                        </div>
                        <HelpTooltip id="metrics-pl" position="left" />
                    </div>
                    <div className="card-body">
                        <div className="flex flex-col h-full">
                            {/* Key Metrics Grid */}
                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="p-3 bg-emerald-50 rounded-lg">
                                    <p className="text-xs text-neutral-500 mb-1">売上高</p>
                                    <p className="text-lg font-bold text-emerald-700">
                                        ¥{(revenue / 1000000).toFixed(0)}M
                                    </p>
                                </div>
                                <div className="p-3 bg-blue-50 rounded-lg">
                                    <p className="text-xs text-neutral-500 mb-1">営業利益</p>
                                    <p className="text-lg font-bold text-blue-700">
                                        ¥{(operatingIncome / 1000000).toFixed(0)}M
                                    </p>
                                    <p className="text-xs text-blue-600">
                                        {revenue ? ((operatingIncome / revenue) * 100).toFixed(1) : 0}%
                                    </p>
                                </div>
                            </div>

                            {/* Chart */}
                            <div className="flex-1 w-full min-h-[200px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={plChartData} layout="vertical" margin={{ left: 40, right: 40 }}>
                                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                        <XAxis type="number" hide />
                                        <YAxis
                                            type="category"
                                            dataKey="name"
                                            tick={{ fontSize: 12 }}
                                            width={60}
                                        />
                                        <Tooltip
                                            formatter={(value: number) => `¥${value.toLocaleString()}`}
                                            cursor={{ fill: 'transparent' }}
                                        />
                                        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
                                            {plChartData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </div>

                {/* BS Summary */}
                <div className="card">
                    <div className="card-header flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Activity size={20} className="text-neutral-400" />
                            <h3 className="font-semibold text-neutral-800">貸借対照表サマリー (B/S)</h3>
                        </div>
                        <HelpTooltip id="metrics-bs" position="left" />
                    </div>
                    <div className="card-body">
                        <div className="flex flex-col justify-center h-full space-y-8">
                            {/* Assets Bar */}
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="font-medium">総資産</span>
                                    <span className="font-bold">¥{bs_metrics.assets.toLocaleString()}</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                                    <div
                                        className="bg-blue-500 h-4 rounded-full"
                                        style={{ width: '100%' }}
                                    />
                                </div>
                            </div>

                            {/* Liabilities & Equity Bar */}
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="font-medium">負債・純資産</span>
                                    <span className="font-bold">¥{(bs_metrics.liabilities + bs_metrics.equity).toLocaleString()}</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden flex">
                                    <div
                                        className="bg-red-500 h-4"
                                        style={{ width: `${liabilityPct}%` }}
                                        title={`負債: ¥${bs_metrics.liabilities.toLocaleString()}`}
                                    />
                                    <div
                                        className="bg-emerald-500 h-4"
                                        style={{ width: `${equityPct}%` }}
                                        title={`純資産: ¥${bs_metrics.equity.toLocaleString()}`}
                                    />
                                </div>
                                <div className="flex justify-between text-xs text-neutral-500 mt-2">
                                    <div className="flex items-center gap-1">
                                        <div className="w-2 h-2 rounded-full bg-red-500"></div>
                                        <span>負債 ({(liabilityPct).toFixed(1)}%)</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                                        <span>純資産 ({(equityPct).toFixed(1)}%)</span>
                                    </div>
                                </div>
                            </div>

                            {/* Imbalance Warning */}
                            {Math.abs(bs_metrics.imbalance) > 1 && (
                                <div className="p-3 bg-red-50 text-red-700 text-sm rounded border border-red-200 flex items-center gap-2">
                                    <Activity size={16} />
                                    <span>貸借不一致: ¥{bs_metrics.imbalance.toLocaleString()} の差額があります</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Detailed Metrics Table */}
            <div className="card">
                <div className="card-header">
                    <h3 className="font-semibold text-neutral-800">主要財務指標詳細</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="table w-full">
                        <thead>
                            <tr>
                                <th className="text-left pl-6">項目</th>
                                <th className="text-right">金額</th>
                                <th className="text-right pr-6">対売上比率</th>
                            </tr>
                        </thead>
                        <tbody>
                            {pl_metrics.sort((a, b) => a.order - b.order).map((metric) => (
                                <tr key={metric.label} className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
                                    <td className="pl-6 py-3 font-medium text-neutral-700">{metric.label}</td>
                                    <td className="text-right py-3 font-mono">¥{metric.amount.toLocaleString()}</td>
                                    <td className="text-right pr-6 py-3">
                                        {metric.ratio !== null ? (
                                            <span className={`badge ${metric.label === 'Operating Income' && (metric.ratio || 0) < 0 ? 'badge-danger' :
                                                metric.label === 'Operating Income' ? 'badge-success' : 'badge-neutral'
                                                }`}>
                                                {metric.ratio}%
                                            </span>
                                        ) : '-'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

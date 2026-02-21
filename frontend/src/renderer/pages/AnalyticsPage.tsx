/**
 * Analytics Page
 *
 * Department, vendor, and account flow analysis.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
import {
  Building2,
  Users,
  ArrowRightLeft,
  AlertTriangle,
  Loader2,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { api, type DepartmentItem, type VendorItem, type AccountFlowItem } from '../lib/api';

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6 text-center text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
        データの取得に失敗しました
      </div>
    );
  }

  const departments = data?.departments || [];

  if (departments.length === 0) {
    return (
      <div className="card p-8 text-center">
        <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">部門データがありません</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-neutral-800 border-b border-gray-200 dark:border-neutral-700">
              <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                部門コード
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                仕訳件数
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                借方合計
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                貸方合計
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                平均リスク
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                高リスク件数
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                自己承認率
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-neutral-700">
            {departments.map((dept: DepartmentItem) => (
              <tr
                key={dept.dept_code}
                className="hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                  {dept.dept_code}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {dept.entry_count.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {formatAmount(dept.total_debit)}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {formatAmount(dept.total_credit)}
                </td>
                <td className="px-4 py-3 text-right">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${riskBadge(dept.avg_risk_score)}`}
                  >
                    {dept.avg_risk_score.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {dept.high_risk_count > 0 ? (
                    <span className="text-red-600 dark:text-red-400 font-medium">
                      {dept.high_risk_count}
                    </span>
                  ) : (
                    <span className="text-gray-400">0</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {dept.self_approval_rate > 0 ? (
                    <span
                      className={
                        dept.self_approval_rate > 10
                          ? 'text-red-600 dark:text-red-400 font-medium'
                          : 'text-gray-700 dark:text-gray-300'
                      }
                    >
                      {dept.self_approval_rate.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-gray-400">0%</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-3 bg-gray-50 dark:bg-neutral-800 border-t border-gray-200 dark:border-neutral-700 text-sm text-gray-500">
        {data?.total || 0} 部門
      </div>
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6 text-center text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
        データの取得に失敗しました
      </div>
    );
  }

  const vendors = data?.vendors || [];

  if (vendors.length === 0) {
    return (
      <div className="card p-8 text-center">
        <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">取引先データがありません</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-neutral-800 border-b border-gray-200 dark:border-neutral-700">
              <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                取引先コード
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                取引件数
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                取引金額
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                平均金額
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                最大金額
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                平均リスク
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                集中度
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                高リスク
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-neutral-700">
            {vendors.map((v: VendorItem) => (
              <tr
                key={v.vendor_code}
                className="hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                  {v.vendor_code}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {v.entry_count.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {formatAmount(v.total_amount)}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {formatAmount(v.avg_amount)}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {formatAmount(v.max_amount)}
                </td>
                <td className="px-4 py-3 text-right">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${riskBadge(v.avg_risk_score)}`}
                  >
                    {v.avg_risk_score.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1.5">
                    <div className="w-16 h-2 bg-gray-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full"
                        style={{ width: `${Math.min(v.concentration_pct, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-10 text-right">
                      {v.concentration_pct.toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  {v.high_risk_count > 0 ? (
                    <span className="text-red-600 dark:text-red-400 font-medium">
                      {v.high_risk_count}
                    </span>
                  ) : (
                    <span className="text-gray-400">0</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-3 bg-gray-50 dark:bg-neutral-800 border-t border-gray-200 dark:border-neutral-700 text-sm text-gray-500">
        {data?.total || 0} 取引先
      </div>
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6 text-center text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
        データの取得に失敗しました
      </div>
    );
  }

  const flows = data?.flows || [];

  if (flows.length === 0) {
    return (
      <div className="card p-8 text-center">
        <ArrowRightLeft className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">勘定科目フローデータがありません</p>
      </div>
    );
  }

  const maxAmount = Math.max(...flows.map((f) => f.flow_amount));

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-neutral-800 border-b border-gray-200 dark:border-neutral-700">
              <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                借方勘定
              </th>
              <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                &nbsp;
              </th>
              <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                貸方勘定
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                取引件数
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                フロー金額
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                平均金額
              </th>
              <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300 w-32">
                金額比率
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-neutral-700">
            {flows.map((f: AccountFlowItem, idx: number) => (
              <tr
                key={`${f.source_account}-${f.target_account}-${idx}`}
                className="hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5">
                    <TrendingDown className="w-3.5 h-3.5 text-blue-500" />
                    <span className="font-mono font-medium text-gray-900 dark:text-white">
                      {f.source_account}
                    </span>
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <ArrowRightLeft className="w-4 h-4 text-gray-400 mx-auto" />
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-green-500" />
                    <span className="font-mono font-medium text-gray-900 dark:text-white">
                      {f.target_account}
                    </span>
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {f.transaction_count.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-white">
                  {formatAmount(f.flow_amount)}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                  {formatAmount(f.avg_amount)}
                </td>
                <td className="px-4 py-3">
                  <div className="w-full h-2 bg-gray-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full transition-all"
                      style={{
                        width: `${maxAmount > 0 ? (f.flow_amount / maxAmount) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-3 bg-gray-50 dark:bg-neutral-800 border-t border-gray-200 dark:border-neutral-700 text-sm text-gray-500">
        {data?.total || 0} フロー
      </div>
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

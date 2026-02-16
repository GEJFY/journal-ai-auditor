/**
 * Rules Section Component
 *
 * Audit rule management UI with category tabs, enable/disable toggles,
 * and severity controls. Used within SettingsPage.
 */

import { useState, useEffect, useCallback } from 'react';
import { Shield, RefreshCw, Loader2 } from 'lucide-react';
import { api, type AuditRule, type RuleCategoryInfo } from '@/lib/api';

const SEVERITY_COLORS: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-orange-100 text-orange-700',
  CRITICAL: 'bg-red-100 text-red-700',
};

export default function RulesSection() {
  const [categories, setCategories] = useState<RuleCategoryInfo[]>([]);
  const [rules, setRules] = useState<AuditRule[]>([]);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      const data = await api.getRuleCategories();
      setCategories(data.categories);
      if (data.categories.length > 0) {
        setActiveCategory((prev) => prev ?? data.categories[0].category);
      }
    } catch {
      // バックエンド未接続時は空表示
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRules = useCallback(async (category: string) => {
    try {
      const data = await api.getRules(category);
      setRules(data.rules);
    } catch {
      setRules([]);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  useEffect(() => {
    if (activeCategory) {
      loadRules(activeCategory);
    }
  }, [activeCategory, loadRules]);

  const handleToggle = async (rule: AuditRule) => {
    setUpdating(rule.rule_id);
    try {
      const updated = await api.updateRule(rule.rule_id, { is_enabled: !rule.is_enabled });
      setRules((prev) => prev.map((r) => (r.rule_id === updated.rule_id ? updated : r)));
      loadCategories(); // カウント更新
    } catch {
      // エラー時は状態を戻さない（楽観的更新なし）
    } finally {
      setUpdating(null);
    }
  };

  const handleSeverityChange = async (rule: AuditRule, severity: string) => {
    setUpdating(rule.rule_id);
    try {
      const updated = await api.updateRule(rule.rule_id, { severity });
      setRules((prev) => prev.map((r) => (r.rule_id === updated.rule_id ? updated : r)));
    } catch {
      // 失敗時はUI変更なし
    } finally {
      setUpdating(null);
    }
  };

  const handleReset = async (ruleId: string) => {
    setUpdating(ruleId);
    try {
      const updated = await api.resetRule(ruleId);
      setRules((prev) => prev.map((r) => (r.rule_id === updated.rule_id ? updated : r)));
      loadCategories();
    } catch {
      // 失敗時は変更なし
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">監査ルール設定</h2>
        </div>
        <div className="flex items-center justify-center py-8 text-neutral-400">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          読み込み中...
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-5 h-5 text-primary-600" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">監査ルール設定</h2>
      </div>

      {categories.length === 0 ? (
        <p className="text-sm text-neutral-500">
          バックエンドに接続してルールを読み込んでください。
        </p>
      ) : (
        <>
          {/* Category Tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {categories.map((cat) => (
              <button
                key={cat.category}
                onClick={() => setActiveCategory(cat.category)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeCategory === cat.category
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                }`}
              >
                {cat.category}
                <span className="ml-1.5 text-xs opacity-70">
                  ({cat.enabled}/{cat.total})
                </span>
              </button>
            ))}
          </div>

          {/* Rules Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200">
                  <th className="text-left py-2 pr-2 font-medium text-neutral-500">ID</th>
                  <th className="text-left py-2 pr-2 font-medium text-neutral-500">ルール名</th>
                  <th className="text-left py-2 pr-2 font-medium text-neutral-500">重要度</th>
                  <th className="text-center py-2 pr-2 font-medium text-neutral-500">有効</th>
                  <th className="text-center py-2 font-medium text-neutral-500">操作</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr
                    key={rule.rule_id}
                    className="border-b border-neutral-100 hover:bg-neutral-50"
                  >
                    <td className="py-2 pr-2 font-mono text-xs text-neutral-400">
                      {rule.rule_id}
                    </td>
                    <td className="py-2 pr-2">
                      <div className="font-medium text-neutral-800">{rule.rule_name}</div>
                      {rule.description && (
                        <div className="text-xs text-neutral-400 mt-0.5">{rule.description}</div>
                      )}
                    </td>
                    <td className="py-2 pr-2">
                      <select
                        value={rule.severity}
                        onChange={(e) => handleSeverityChange(rule, e.target.value)}
                        disabled={updating === rule.rule_id}
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          SEVERITY_COLORS[rule.severity] || 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        <option value="LOW">LOW</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="HIGH">HIGH</option>
                        <option value="CRITICAL">CRITICAL</option>
                      </select>
                    </td>
                    <td className="py-2 pr-2 text-center">
                      <button
                        onClick={() => handleToggle(rule)}
                        disabled={updating === rule.rule_id}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                          rule.is_enabled ? 'bg-primary-600' : 'bg-neutral-300'
                        }`}
                        aria-label={`${rule.rule_name}を${rule.is_enabled ? '無効' : '有効'}にする`}
                      >
                        <span
                          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                            rule.is_enabled ? 'translate-x-4' : 'translate-x-0.5'
                          }`}
                        />
                      </button>
                    </td>
                    <td className="py-2 text-center">
                      <button
                        onClick={() => handleReset(rule.rule_id)}
                        disabled={updating === rule.rule_id}
                        className="p-1 rounded text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100"
                        title="デフォルトに戻す"
                      >
                        <RefreshCw size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

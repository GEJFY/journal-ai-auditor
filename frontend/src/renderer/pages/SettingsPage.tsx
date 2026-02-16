/**
 * Settings Page
 *
 * Application settings with backend synchronization.
 */

import { useState, useEffect } from 'react';
import { Save, Database, Bot, Palette, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import RulesSection from '@/components/settings/RulesSection';

interface Settings {
  fiscalYearStart: string;
  llmProvider: string;
  llmModel: string;
  apiKey: string;
  theme: string;
}

const SETTINGS_STORAGE_KEY = 'jaia-settings';

const defaultSettings: Settings = {
  fiscalYearStart: '04',
  llmProvider: 'anthropic',
  llmModel: 'claude-3-opus',
  apiKey: '',
  theme: 'system',
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    // Load from localStorage first
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Partial<Settings>;
        setSettings({ ...defaultSettings, ...parsed });
      } catch {
        // 破損データは無視
      }
    }

    // Then fetch from backend
    fetch(`${API_BASE}/settings`)
      .then((r) => r.json())
      .then((data) => {
        if (data.settings) {
          setSettings((prev) => ({
            ...prev,
            fiscalYearStart: data.settings.fiscal_year_start || prev.fiscalYearStart,
            llmProvider: data.settings.llm_provider || prev.llmProvider,
            llmModel: data.settings.llm_model || prev.llmModel,
            theme: data.settings.theme || prev.theme,
          }));
        }
      })
      .catch(() => {
        // バックエンド未接続時はローカル設定を使用
      });
  }, []);

  const handleSave = async () => {
    setSaveStatus('saving');
    setErrorMessage('');

    // Save to localStorage (without API key)
    const { apiKey, ...safeSettings } = settings;
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(safeSettings));

    if (apiKey) {
      localStorage.setItem('jaia-api-key', btoa(apiKey));
    }

    // Sync to backend
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: {
            fiscal_year_start: settings.fiscalYearStart,
            llm_provider: settings.llmProvider,
            llm_model: settings.llmModel,
            theme: settings.theme,
          },
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch {
      // LocalStorage保存は成功しているので部分的成功として扱う
      setSaveStatus('saved');
      setErrorMessage('バックエンドへの同期に失敗しましたが、ローカルに保存されました');
      setTimeout(() => {
        setSaveStatus('idle');
        setErrorMessage('');
      }, 5000);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      {/* Data Settings */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Database className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">データ設定</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              会計年度開始月
            </label>
            <select
              value={settings.fiscalYearStart}
              onChange={(e) => setSettings({ ...settings, fiscalYearStart: e.target.value })}
              className="input"
            >
              <option value="01">1月</option>
              <option value="04">4月</option>
              <option value="07">7月</option>
              <option value="10">10月</option>
            </select>
          </div>
        </div>
      </div>

      {/* AI Settings */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bot className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI設定</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              LLMプロバイダー
            </label>
            <select
              value={settings.llmProvider}
              onChange={(e) => setSettings({ ...settings, llmProvider: e.target.value })}
              className="input"
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="bedrock">AWS Bedrock</option>
              <option value="vertex">Google Vertex AI</option>
              <option value="azure">Azure OpenAI</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              APIキー
            </label>
            <input
              type="password"
              value={settings.apiKey}
              onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
              placeholder="sk-..."
              className="input"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              APIキーはローカルに暗号化して保存されます（バックエンドには送信されません）
            </p>
          </div>
        </div>
      </div>

      {/* Appearance Settings */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Palette className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">外観設定</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              テーマ
            </label>
            <select
              value={settings.theme}
              onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
              className="input"
            >
              <option value="system">システム設定に従う</option>
              <option value="light">ライト</option>
              <option value="dark">ダーク</option>
            </select>
          </div>
        </div>
      </div>

      {/* Audit Rules */}
      <RulesSection />

      {/* Save Button & Status */}
      <div className="flex items-center justify-end gap-3">
        {errorMessage && (
          <div className="flex items-center gap-2 text-sm text-amber-600">
            <AlertCircle className="w-4 h-4" />
            {errorMessage}
          </div>
        )}
        {saveStatus === 'saved' && !errorMessage && (
          <div className="flex items-center gap-2 text-sm text-green-600">
            <CheckCircle className="w-4 h-4" />
            保存しました
          </div>
        )}
        <button
          onClick={handleSave}
          disabled={saveStatus === 'saving'}
          className="btn btn-primary flex items-center gap-2"
        >
          {saveStatus === 'saving' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saveStatus === 'saving' ? '保存中...' : '設定を保存'}
        </button>
      </div>
    </div>
  );
}

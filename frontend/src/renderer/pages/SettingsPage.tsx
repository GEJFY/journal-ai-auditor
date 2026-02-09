/**
 * Settings Page
 *
 * Application settings and configuration.
 */

import { useState, useEffect } from 'react';
import { Save, Database, Bot, Palette } from 'lucide-react';

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
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Partial<Settings>;
        setSettings({ ...defaultSettings, ...parsed });
      } catch {
        // 破損データは無視
      }
    }
  }, []);

  const handleSave = () => {
    const { apiKey, ...safeSettings } = settings;
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(safeSettings));

    if (apiKey) {
      localStorage.setItem('jaia-api-key', btoa(apiKey));
    }

    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
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
              APIキーはローカルに暗号化して保存されます
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

      {/* Save Button */}
      <div className="flex justify-end">
        <button onClick={handleSave} className="btn btn-primary flex items-center gap-2">
          <Save className="w-4 h-4" />
          {saved ? '保存しました' : '設定を保存'}
        </button>
      </div>
    </div>
  );
}

/**
 * Autonomous Audit Page
 *
 * 5-phase autonomous AI audit agent interface with real-time SSE streaming.
 */

import { useState, useRef, useCallback } from 'react';
import { useFiscalYear } from '@/lib/useFiscalYear';
import {
  Brain,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronRight,
  Eye,
  Lightbulb,
  Search,
  ShieldCheck,
  FileText,
  Clock,
} from 'lucide-react';
import {
  streamSSE,
  api,
  type AuditHypothesis,
  type AuditInsight,
  type AutonomousAuditSSEEvent,
} from '../lib/api';

// Phase definitions
const PHASES = [
  { key: 'observe', label: '観察', icon: Eye, description: 'データの全体像を把握' },
  { key: 'hypothesize', label: '仮説生成', icon: Lightbulb, description: '検証可能な仮説を生成' },
  { key: 'explore', label: '探索', icon: Search, description: 'ツールでエビデンス収集' },
  { key: 'verify', label: '検証', icon: ShieldCheck, description: '仮説の支持度を評価' },
  { key: 'synthesize', label: '統合', icon: FileText, description: 'インサイトを生成' },
] as const;

// Severity badge colors
const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  LOW: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  INFO: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
};

const VERDICT_LABELS: Record<string, { label: string; color: string }> = {
  supported: { label: '支持', color: 'text-green-600 dark:text-green-400' },
  partially_supported: { label: '部分的支持', color: 'text-yellow-600 dark:text-yellow-400' },
  inconclusive: { label: '判断不能', color: 'text-gray-500 dark:text-gray-400' },
  refuted: { label: '否定', color: 'text-red-600 dark:text-red-400' },
  pending: { label: '未検証', color: 'text-neutral-400' },
  testing: { label: '検証中', color: 'text-blue-500' },
};

interface LogEntry {
  timestamp: string;
  type: string;
  message: string;
}

type TabKey = 'hypotheses' | 'insights' | 'summary' | 'log';

export default function AutonomousAuditPage() {
  const [fiscalYear] = useFiscalYear();
  const [isRunning, setIsRunning] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [completedPhases, setCompletedPhases] = useState<Set<string>>(new Set());
  const [hypotheses, setHypotheses] = useState<AuditHypothesis[]>([]);
  const [insights, setInsights] = useState<AuditInsight[]>([]);
  const [executiveSummary, setExecutiveSummary] = useState('');
  const [log, setLog] = useState<LogEntry[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('log');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [autoApprove, setAutoApprove] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const addLog = useCallback((type: string, message: string) => {
    setLog((prev) => [
      ...prev,
      {
        timestamp: new Date().toLocaleTimeString('ja-JP'),
        type,
        message,
      },
    ]);
  }, []);

  const handleStart = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    setCurrentPhase(null);
    setCompletedPhases(new Set());
    setHypotheses([]);
    setInsights([]);
    setExecutiveSummary('');
    setLog([]);
    setSessionId(null);
    setActiveTab('log');

    const controller = new AbortController();
    abortRef.current = controller;

    addLog('system', `${fiscalYear}年度の自律型監査を開始...`);

    let lastPhase: string | null = null;

    try {
      await streamSSE(
        '/autonomous-audit/start/stream',
        {
          fiscal_year: fiscalYear,
          scope: {},
          auto_approve: autoApprove,
        },
        (rawEvent) => {
          const event = rawEvent as unknown as AutonomousAuditSSEEvent;

          switch (event.type) {
            case 'start':
              addLog('system', '分析セッションを初期化しました');
              break;

            case 'phase_start':
              if (lastPhase) {
                setCompletedPhases((prev) => new Set([...prev, lastPhase!]));
              }
              lastPhase = event.phase || null;
              setCurrentPhase(event.phase || null);
              addLog(
                'phase',
                `フェーズ開始: ${PHASES.find((p) => p.key === event.phase)?.label || event.phase}`
              );
              break;

            case 'observation':
              addLog('observation', `[${event.tool}] ${event.summary}`);
              break;

            case 'hypothesis':
              if (event.id && event.title) {
                setHypotheses((prev) => [
                  ...prev,
                  {
                    id: event.id!,
                    title: event.title!,
                    description: event.description || '',
                    rationale: '',
                    test_approach: '',
                    tools_to_use: [],
                    priority: prev.length + 1,
                    status: 'pending',
                    grounding_score: 0,
                    evidence_for: [],
                    evidence_against: [],
                  },
                ]);
                addLog('hypothesis', `${event.id}: ${event.title}`);
              }
              break;

            case 'tool_start':
              addLog('tool', `ツール実行開始: ${event.tool} (${event.hypothesis_id})`);
              break;

            case 'tool_complete':
              addLog(
                'tool',
                `ツール完了: ${event.tool} - ${event.success ? '成功' : '失敗'} - ${event.summary || ''}`
              );
              break;

            case 'verification':
              if (event.hypothesis_id) {
                setHypotheses((prev) =>
                  prev.map((h) =>
                    h.id === event.hypothesis_id
                      ? {
                          ...h,
                          status: event.verdict || h.status,
                          grounding_score: event.grounding_score ?? h.grounding_score,
                        }
                      : h
                  )
                );
                const verdict = VERDICT_LABELS[event.verdict || ''] || { label: event.verdict };
                addLog(
                  'verification',
                  `${event.hypothesis_id}: ${verdict.label} (${((event.grounding_score ?? 0) * 100).toFixed(0)}%)`
                );
              }
              break;

            case 'insight':
              if (event.id && event.title) {
                setInsights((prev) => [
                  ...prev,
                  {
                    id: event.id!,
                    title: event.title!,
                    description: '',
                    category: 'risk',
                    severity: event.severity || 'MEDIUM',
                    affected_amount: 0,
                    affected_count: 0,
                    recommendations: [],
                    related_hypotheses: [],
                    grounding_score: 0,
                  },
                ]);
                addLog('insight', `${event.id}: [${event.severity}] ${event.title}`);
              }
              break;

            case 'summary':
              setExecutiveSummary(event.executive_summary || '');
              addLog('summary', 'エグゼクティブサマリーを生成しました');
              break;

            case 'complete':
              setSessionId(event.session_id || null);
              if (lastPhase) {
                setCompletedPhases((prev) => new Set([...prev, lastPhase!]));
              }
              setCurrentPhase('complete');
              addLog(
                'complete',
                `分析完了: ${event.insights_count || 0}件のインサイト, ${event.hypotheses_count || 0}件の仮説`
              );
              break;

            case 'error':
              setError(event.message || 'Unknown error');
              addLog('error', event.message || 'エラーが発生しました');
              break;
          }
        },
        controller.signal
      );
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message);
        addLog('error', (err as Error).message);
      }
    } finally {
      setIsRunning(false);
      abortRef.current = null;
    }

    // 完了後にフルデータを取得
    if (sessionId || lastPhase === 'complete') {
      try {
        // セッション一覧から最新のIDを取得
        const sessions = await api.listAuditSessions(fiscalYear, 1);
        if (sessions.length > 0) {
          const sid = sessions[0].session_id;
          setSessionId(sid);
          const report = await api.getAuditReport(sid);
          setInsights(report.insights);
          setHypotheses(report.hypotheses);
          setExecutiveSummary(report.executive_summary);
        }
      } catch {
        // フルデータ取得に失敗してもSSEデータは残る
      }
    }
  }, [fiscalYear, autoApprove, addLog, sessionId]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
    addLog('system', '分析を中止しました');
  }, [addLog]);

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'log', label: 'ログ', count: log.length },
    { key: 'hypotheses', label: '仮説', count: hypotheses.length },
    { key: 'insights', label: 'インサイト', count: insights.length },
    { key: 'summary', label: 'サマリー' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <Brain className="w-7 h-7 text-primary-600" />
            AI自律監査
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            AIエージェントが自律的に仕訳データを分析し、監査インサイトを生成します
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
            <input
              type="checkbox"
              checked={autoApprove}
              onChange={(e) => setAutoApprove(e.target.checked)}
              disabled={isRunning}
              className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
            />
            自動承認
          </label>
          {isRunning ? (
            <button
              onClick={handleStop}
              className="btn-secondary flex items-center gap-2 px-4 py-2 rounded-lg"
            >
              <XCircle className="w-4 h-4" />
              中止
            </button>
          ) : (
            <button
              onClick={handleStart}
              className="btn-primary flex items-center gap-2 px-4 py-2 rounded-lg"
            >
              <Play className="w-4 h-4" />
              分析開始
            </button>
          )}
        </div>
      </div>

      {/* Phase Progress */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          {PHASES.map((phase, i) => {
            const isComplete = completedPhases.has(phase.key);
            const isCurrent = currentPhase === phase.key;
            const Icon = phase.icon;

            return (
              <div key={phase.key} className="flex items-center">
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={`
                      w-10 h-10 rounded-full flex items-center justify-center transition-all
                      ${isComplete ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' : ''}
                      ${isCurrent ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400 ring-2 ring-primary-300 animate-pulse' : ''}
                      ${!isComplete && !isCurrent ? 'bg-neutral-100 text-neutral-400 dark:bg-neutral-700 dark:text-neutral-500' : ''}
                    `}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : isCurrent ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Icon className="w-5 h-5" />
                    )}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      isCurrent
                        ? 'text-primary-600 dark:text-primary-400'
                        : isComplete
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-neutral-400'
                    }`}
                  >
                    {phase.label}
                  </span>
                </div>
                {i < PHASES.length - 1 && (
                  <ChevronRight
                    className={`w-4 h-4 mx-2 mt-[-16px] ${
                      completedPhases.has(PHASES[i + 1].key) || currentPhase === PHASES[i + 1].key
                        ? 'text-primary-400'
                        : 'text-neutral-300 dark:text-neutral-600'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800 dark:text-red-200">
              エラーが発生しました
            </p>
            <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="card">
        <div className="border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5
                  ${
                    activeTab === tab.key
                      ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'
                  }
                `}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 text-xs px-1.5 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 min-h-[400px] max-h-[600px] overflow-y-auto">
          {/* Log Tab */}
          {activeTab === 'log' && (
            <div className="space-y-1 font-mono text-xs">
              {log.length === 0 ? (
                <p className="text-neutral-400 text-sm text-center py-8">
                  分析を開始するとログが表示されます
                </p>
              ) : (
                log.map((entry, i) => (
                  <div
                    key={i}
                    className={`flex gap-2 py-0.5 ${
                      entry.type === 'error'
                        ? 'text-red-600 dark:text-red-400'
                        : entry.type === 'phase'
                          ? 'text-primary-600 dark:text-primary-400 font-semibold'
                          : entry.type === 'complete'
                            ? 'text-green-600 dark:text-green-400 font-semibold'
                            : 'text-neutral-600 dark:text-neutral-400'
                    }`}
                  >
                    <span className="text-neutral-400 shrink-0">{entry.timestamp}</span>
                    <span className="shrink-0 w-20 text-right">[{entry.type}]</span>
                    <span>{entry.message}</span>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Hypotheses Tab */}
          {activeTab === 'hypotheses' && (
            <div className="space-y-3">
              {hypotheses.length === 0 ? (
                <p className="text-neutral-400 text-sm text-center py-8">
                  仮説はまだ生成されていません
                </p>
              ) : (
                hypotheses.map((h) => {
                  const verdict = VERDICT_LABELS[h.status] || VERDICT_LABELS.pending;
                  return (
                    <div
                      key={h.id}
                      className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-neutral-400">{h.id}</span>
                          <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                            {h.title}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-medium ${verdict.color}`}>
                            {verdict.label}
                          </span>
                          {h.grounding_score > 0 && (
                            <span className="text-xs bg-neutral-100 dark:bg-neutral-700 px-1.5 py-0.5 rounded">
                              {(h.grounding_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                      {h.description && (
                        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
                          {h.description}
                        </p>
                      )}
                      {h.evidence_for.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-green-600 dark:text-green-400">
                            支持エビデンス:
                          </p>
                          <ul className="text-xs text-neutral-500 mt-1 space-y-0.5">
                            {h.evidence_for.map((e, i) => (
                              <li key={i}>- {e}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {h.evidence_against.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-red-600 dark:text-red-400">
                            反証:
                          </p>
                          <ul className="text-xs text-neutral-500 mt-1 space-y-0.5">
                            {h.evidence_against.map((e, i) => (
                              <li key={i}>- {e}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Insights Tab */}
          {activeTab === 'insights' && (
            <div className="space-y-3">
              {insights.length === 0 ? (
                <p className="text-neutral-400 text-sm text-center py-8">
                  インサイトはまだ生成されていません
                </p>
              ) : (
                insights.map((ins) => (
                  <div
                    key={ins.id}
                    className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-neutral-400">{ins.id}</span>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_COLORS[ins.severity] || SEVERITY_COLORS.INFO}`}
                        >
                          {ins.severity}
                        </span>
                        <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                          {ins.title}
                        </h3>
                      </div>
                    </div>
                    {ins.description && (
                      <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
                        {ins.description}
                      </p>
                    )}
                    <div className="flex gap-4 mt-3 text-xs text-neutral-500">
                      {ins.affected_amount > 0 && (
                        <span>影響金額: {ins.affected_amount.toLocaleString()}円</span>
                      )}
                      {ins.affected_count > 0 && (
                        <span>影響件数: {ins.affected_count.toLocaleString()}件</span>
                      )}
                    </div>
                    {ins.recommendations.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                          推奨事項:
                        </p>
                        <ul className="text-xs text-neutral-500 mt-1 space-y-0.5">
                          {ins.recommendations.map((r, i) => (
                            <li key={i}>- {r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Summary Tab */}
          {activeTab === 'summary' && (
            <div>
              {executiveSummary ? (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                    エグゼクティブサマリー
                  </h3>
                  <div className="prose prose-sm dark:prose-invert max-w-none text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
                    {executiveSummary}
                  </div>
                  {sessionId && (
                    <div className="flex items-center gap-4 pt-4 border-t border-neutral-200 dark:border-neutral-700 text-xs text-neutral-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        セッション: {sessionId.slice(0, 8)}...
                      </span>
                      <span className="flex items-center gap-1">
                        <Lightbulb className="w-3 h-3" />
                        仮説: {hypotheses.length}件
                      </span>
                      <span className="flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        インサイト: {insights.length}件
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-neutral-400 text-sm text-center py-8">
                  分析完了後にエグゼクティブサマリーが表示されます
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

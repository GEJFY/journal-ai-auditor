/**
 * Onboarding Component
 *
 * First-time user welcome wizard with step-by-step introduction.
 */

import { useState, useEffect } from 'react';
import {
  Activity,
  Upload,
  BarChart3,
  Shield,
  Bot,
  ClipboardList,
  ArrowRight,
  ArrowLeft,
  Check,
  X,
} from 'lucide-react';
import clsx from 'clsx';

const ONBOARDING_VERSION = '1.0';
const STORAGE_KEY = 'jaia_onboarding';

interface OnboardingState {
  version: string;
  completed: boolean;
  completedAt?: string;
}

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  details: string[];
}

const steps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'JAIAへようこそ',
    description: 'Journal entry AI Analyzer - AI駆動の仕訳分析プラットフォーム',
    icon: <Activity size={48} className="text-primary-600" />,
    details: [
      '仕訳データの自動リスク分析',
      '58種類の監査ルールによる違反検出',
      'AIによる異常パターンの発見',
    ],
  },
  {
    id: 'import',
    title: 'データの取り込み',
    description: 'CSVまたはExcel形式の仕訳データをインポートします',
    icon: <Upload size={48} className="text-accent-600" />,
    details: [
      'AICPA GL_Detail標準フォーマット対応',
      'ドラッグ&ドロップで簡単アップロード',
      '自動バリデーションとエラー検出',
    ],
  },
  {
    id: 'analysis',
    title: 'リスク分析',
    description: 'ルールベースとMLによる多角的なリスク評価',
    icon: <Shield size={48} className="text-risk-critical" />,
    details: [
      '高額取引、自己承認、期末集中の検出',
      'ベンフォード分析による数値異常検出',
      'リスクスコアによる優先順位付け',
    ],
  },
  {
    id: 'ai',
    title: 'AI分析',
    description: 'AIエージェントによる対話型分析',
    icon: <Bot size={48} className="text-accent-600" />,
    details: [
      '自然言語での質問・調査依頼',
      '自動仮説生成と検証',
      '分析結果の要約と提案',
    ],
  },
  {
    id: 'reports',
    title: 'レポート生成',
    description: '監査調書・分析レポートを自動作成',
    icon: <ClipboardList size={48} className="text-primary-600" />,
    details: [
      'エグゼクティブサマリー',
      '詳細な違反一覧レポート',
      'PowerPoint/PDF出力対応',
    ],
  },
];

interface OnboardingProps {
  onComplete: () => void;
}

export default function Onboarding({ onComplete }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  const step = steps[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;
  const progress = ((currentStep + 1) / steps.length) * 100;

  const handleNext = () => {
    if (isLast) {
      handleComplete();
    } else {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (!isFirst) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleComplete = () => {
    const state: OnboardingState = {
      version: ONBOARDING_VERSION,
      completed: true,
      completedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    setIsVisible(false);
    setTimeout(onComplete, 300);
  };

  const handleSkip = () => {
    handleComplete();
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-neutral-100">
          <div
            className="h-full bg-gradient-to-r from-primary-600 to-accent-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-8 py-4 border-b border-neutral-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-brand rounded-lg flex items-center justify-center">
              <Activity size={18} className="text-white" />
            </div>
            <span className="font-bold text-primary-900">JAIA</span>
          </div>
          <button
            onClick={handleSkip}
            className="text-neutral-400 hover:text-neutral-600 p-1"
            title="スキップ"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-8 py-10">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-neutral-50 mb-6">
              {step.icon}
            </div>
            <h2 className="text-2xl font-bold text-neutral-900 mb-3">
              {step.title}
            </h2>
            <p className="text-neutral-600 max-w-md mx-auto">
              {step.description}
            </p>
          </div>

          <div className="bg-neutral-50 rounded-xl p-6 mb-8">
            <ul className="space-y-3">
              {step.details.map((detail, index) => (
                <li
                  key={index}
                  className="flex items-start gap-3 animate-slide-up"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="w-5 h-5 rounded-full bg-accent-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Check size={12} className="text-accent-600" />
                  </div>
                  <span className="text-neutral-700">{detail}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Step indicators */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {steps.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentStep(index)}
                className={clsx(
                  'w-2.5 h-2.5 rounded-full transition-all',
                  index === currentStep
                    ? 'w-8 bg-primary-600'
                    : index < currentStep
                    ? 'bg-primary-300'
                    : 'bg-neutral-200'
                )}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-8 py-5 bg-neutral-50 border-t border-neutral-100">
          <button
            onClick={handlePrev}
            disabled={isFirst}
            className={clsx(
              'btn btn-secondary',
              isFirst && 'opacity-50 cursor-not-allowed'
            )}
          >
            <ArrowLeft size={18} />
            戻る
          </button>
          <span className="text-sm text-neutral-500">
            {currentStep + 1} / {steps.length}
          </span>
          <button onClick={handleNext} className="btn btn-primary">
            {isLast ? (
              <>
                はじめる
                <Check size={18} />
              </>
            ) : (
              <>
                次へ
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Hook to check if onboarding should be shown
export function useOnboarding() {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        setShowOnboarding(true);
        return;
      }

      const state: OnboardingState = JSON.parse(stored);
      if (!state.completed || state.version !== ONBOARDING_VERSION) {
        setShowOnboarding(true);
      }
    } catch {
      setShowOnboarding(true);
    }
  }, []);

  const completeOnboarding = () => {
    setShowOnboarding(false);
  };

  const resetOnboarding = () => {
    localStorage.removeItem(STORAGE_KEY);
    setShowOnboarding(true);
  };

  return { showOnboarding, completeOnboarding, resetOnboarding };
}

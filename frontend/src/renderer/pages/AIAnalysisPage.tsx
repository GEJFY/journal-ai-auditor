/**
 * AI Analysis Page
 *
 * Interactive AI chat interface with SSE streaming support.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { useFiscalYear } from '@/lib/useFiscalYear';
import { Send, Bot, User, Loader2, FileText, Search, AlertTriangle, Sparkles } from 'lucide-react';
import { streamSSE, type SSEEvent } from '../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agentType?: string;
  isStreaming?: boolean;
}

const QUICK_ACTIONS = [
  {
    icon: <Search className="w-4 h-4" />,
    label: '高リスク仕訳を検索',
    query: '高リスクの仕訳を見せてください',
  },
  {
    icon: <AlertTriangle className="w-4 h-4" />,
    label: '異常検知結果',
    query: '今期の異常検知結果を説明してください',
  },
  {
    icon: <FileText className="w-4 h-4" />,
    label: 'サマリーレポート',
    query: '今期の仕訳検証サマリーを作成してください',
  },
  {
    icon: <Sparkles className="w-4 h-4" />,
    label: 'リスク評価',
    query: '現在のリスク評価と主要な懸念事項を教えてください',
  },
];

export default function AIAnalysisPage() {
  const [fiscalYear] = useFiscalYear();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content:
        'こんにちは！JAIAのAIアシスタントです。仕訳データの分析、リスク評価、監査に関する質問にお答えします。何かお手伝いできることはありますか？',
      timestamp: new Date(),
      agentType: 'QA',
    },
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinkingText, setThinkingText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinkingText]);

  const sendQuery = useCallback(
    async (query: string) => {
      if (isStreaming) return;

      setIsStreaming(true);
      setThinkingText('');
      const messageId = Date.now().toString();
      const controller = new AbortController();
      abortRef.current = controller;

      // ストリーミングメッセージを追加（空で開始）
      const streamingMessage: Message = {
        id: messageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, streamingMessage]);

      try {
        await streamSSE(
          '/agents/ask/stream',
          { question: query, fiscal_year: fiscalYear },
          (event: SSEEvent) => {
            switch (event.type) {
              case 'start':
                setMessages((prev) =>
                  prev.map((m) => (m.id === messageId ? { ...m, agentType: event.agent } : m))
                );
                break;

              case 'thinking':
                setThinkingText(event.content || '');
                break;

              case 'chunk':
                setThinkingText('');
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === messageId ? { ...m, content: m.content + (event.content || '') } : m
                  )
                );
                break;

              case 'complete':
                setMessages((prev) =>
                  prev.map((m) => (m.id === messageId ? { ...m, isStreaming: false } : m))
                );
                break;

              case 'error':
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === messageId
                      ? {
                          ...m,
                          content: `エラーが発生しました: ${event.message}`,
                          isStreaming: false,
                        }
                      : m
                  )
                );
                break;
            }
          },
          controller.signal
        );
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? {
                    ...m,
                    content: `エラーが発生しました: ${(error as Error).message}`,
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      } finally {
        setIsStreaming(false);
        setThinkingText('');
        abortRef.current = null;
      }
    },
    [fiscalYear, isStreaming]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    sendQuery(input);
    setInput('');
  };

  const handleQuickAction = (query: string) => {
    if (isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    sendQuery(query);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Bot className="w-6 h-6 text-primary-600" />
            AI分析アシスタント
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            仕訳データの分析や監査に関する質問にお答えします
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="py-4 flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action, index) => (
          <button
            key={index}
            onClick={() => handleQuickAction(action.query)}
            disabled={isStreaming}
            className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.role === 'user'
                  ? 'bg-primary-100 dark:bg-primary-900'
                  : 'bg-gray-100 dark:bg-gray-700'
              }`}
            >
              {message.role === 'user' ? (
                <User className="w-4 h-4 text-primary-600" />
              ) : (
                <Bot className="w-4 h-4 text-gray-600 dark:text-gray-400" />
              )}
            </div>
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              {message.agentType && message.role === 'assistant' && (
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  {message.agentType} Agent
                </div>
              )}
              <div className="whitespace-pre-wrap">
                {message.content}
                {message.isStreaming && <span className="animate-pulse">|</span>}
              </div>
              {!message.isStreaming && (
                <div
                  className={`text-xs mt-2 ${
                    message.role === 'user' ? 'text-primary-200' : 'text-gray-400'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString('ja-JP', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              )}
            </div>
          </div>
        ))}

        {thinkingText && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </div>
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
              <div className="flex items-center gap-2 text-gray-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                {thinkingText}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="質問を入力してください..."
            className="flex-1 px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          AIの回答は参考情報です。重要な判断には専門家の確認をお勧めします。
        </p>
      </form>
    </div>
  );
}

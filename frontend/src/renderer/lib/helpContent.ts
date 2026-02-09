/**
 * Help Content Definitions
 *
 * Centralized help content for tooltips and contextual help.
 */

interface HelpContentItem {
  title: string;
  description: string;
  learnMoreUrl?: string;
}

export const helpContent: Record<string, HelpContentItem> = {
  // Dashboard
  'dashboard-overview': {
    title: 'ダッシュボード',
    description:
      '仕訳データの分析結果を一覧表示します。KPI、リスク分布、時系列トレンドを確認できます。',
    learnMoreUrl: '#',
  },
  'dashboard-risk-score': {
    title: 'リスクスコア',
    description:
      '各仕訳のリスクを0-100のスコアで表示します。60以上が高リスク、40-60が中リスク、40未満が低リスクです。',
    learnMoreUrl: '#',
  },
  'dashboard-high-risk': {
    title: '高リスク項目',
    description:
      'リスクスコアが60以上の仕訳件数です。Critical、Highレベルの違反を含む仕訳が該当します。',
  },
  'dashboard-self-approval': {
    title: '自己承認',
    description: '作成者と承認者が同一人物の仕訳です。内部統制上の問題がある可能性があります。',
  },
  'dashboard-timeseries': {
    title: '月次推移',
    description: '月ごとの取引金額の推移を表示します。期末集中や異常な変動を視覚的に確認できます。',
  },
  'dashboard-risk-distribution': {
    title: 'リスク分布',
    description:
      '全仕訳をリスクレベル別に分類した円グラフです。高リスク比率が高い場合は詳細調査が必要です。',
  },

  // Benford Analysis
  'benford-analysis': {
    title: 'ベンフォード分析',
    description:
      'ベンフォードの法則に基づき、金額の先頭桁分布を分析します。自然なデータは特定の分布に従うため、偏りは異常の兆候となります。',
    learnMoreUrl: '#',
  },
  'benford-conformity': {
    title: '適合度判定',
    description:
      '実際の分布と理論値の乖離度を判定します。「適合」「許容範囲」「境界」「不適合」の4段階で評価されます。',
  },

  // Risk Analysis
  'risk-analysis': {
    title: 'リスク分析',
    description: '58種類の監査ルールと機械学習モデルによる多角的なリスク評価結果を表示します。',
  },
  'risk-violations': {
    title: 'ルール違反',
    description: '監査ルールに違反した仕訳の一覧です。違反の種類、重要度、該当金額を確認できます。',
  },

  // Import
  'import-format': {
    title: 'データ形式',
    description:
      'AICPA GL_Detail標準フォーマットのCSVまたはExcelファイルをサポートしています。必須項目：仕訳ID、日付、勘定コード、金額。',
    learnMoreUrl: '#',
  },
  'import-validation': {
    title: 'バリデーション',
    description:
      'インポート前に必須項目、データ型、整合性を自動検証します。エラーがある場合は該当行と理由が表示されます。',
  },

  // AI Analysis
  'ai-analysis': {
    title: 'AI分析',
    description:
      'AIエージェントに自然言語で質問や調査依頼ができます。データの傾向分析、異常調査、仮説検証などを実行できます。',
  },
  'ai-agent': {
    title: 'AIエージェント',
    description:
      '10種類の専門エージェント（トレンド分析、リスク分析、調査、レポート作成など）が連携して分析を行います。',
  },

  // Reports
  'reports-templates': {
    title: 'レポートテンプレート',
    description:
      'エグゼクティブサマリー、詳細分析、違反一覧、監査調書など7種類のテンプレートから選択できます。',
  },
  'reports-export': {
    title: 'エクスポート',
    description: 'レポートはPowerPoint（.pptx）またはPDF形式でダウンロードできます。',
  },

  // Settings
  'settings-llm': {
    title: 'LLMプロバイダー',
    description:
      'AI分析に使用するLLMを選択します。Anthropic Claude、AWS Bedrock、Google Vertex AI、Azure OpenAIに対応しています。',
    learnMoreUrl: '#',
  },
  'settings-rules': {
    title: 'ルール設定',
    description:
      '監査ルールのしきい値をカスタマイズできます。例：高額取引の基準金額、期末集中日数など。',
  },
};

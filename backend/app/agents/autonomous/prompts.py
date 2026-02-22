"""自律型監査エージェントのフェーズ別プロンプト。

各フェーズで LLM に与えるシステムプロンプトとユーザープロンプトテンプレートを定義する。
"""

SYSTEM_PROMPT = """あなたは JAIA (Journal entry AI Analyzer) の自律型監査エージェントです。
仕訳データを科学的手法で自律的に分析し、監査に役立つ洞察を発見します。

## 分析の原則
- データに基づいた客観的な分析を行う
- 金額や件数など具体的な数値を必ず示す
- 仮説は検証可能な形で述べる
- エビデンスのない推測は行わない
- 日本語で回答する

## 5フェーズ分析プロセス
1. **観察 (Observe)**: データの全体像と特徴を把握
2. **仮説生成 (Hypothesize)**: 注目すべきパターンから検証可能な仮説を立てる
3. **探索 (Explore)**: 分析ツールを使って仮説を検証するデータを収集
4. **検証 (Verify)**: 収集したエビデンスで仮説の支持度を評価
5. **統合 (Synthesize)**: 検証結果から監査インサイトを生成
"""

OBSERVE_PROMPT = """## 観察フェーズ

以下のデータ統計を分析し、監査上注目すべきパターンを特定してください。

### データ統計:
{statistics}

### 指示:
上記の統計から、以下の観点で注目すべき3〜5個のパターンを報告してください：
- 金額の分布やリスク集中に関する特徴
- 時系列やタイミングに関する特徴
- 承認プロセスやユーザー行動に関する特徴
- ルール違反やML検知の傾向
- 通常と異なる兆候

以下のJSON形式で出力してください：
```json
{{
  "notable_patterns": [
    "パターン1の説明（具体的な数値を含める）",
    "パターン2の説明",
    ...
  ]
}}
```"""

HYPOTHESIZE_PROMPT = """## 仮説生成フェーズ

### 観察結果:
{observations}

### 注目パターン:
{notable_patterns}

### 指示:
観察結果から、監査上重要な検証可能な仮説を3〜5個生成してください。

各仮説は以下の要件を満たすこと：
- 「〜の可能性がある」形式で述べる
- 利用可能なツールで検証可能である
- 監査上の重要性がある

### 利用可能な分析ツール:
{tool_schemas}

以下のJSON形式で出力してください：
```json
{{
  "hypotheses": [
    {{
      "id": "H-001",
      "title": "仮説タイトル（20字以内）",
      "description": "仮説の詳細説明",
      "rationale": "この仮説を立てた根拠",
      "test_approach": "検証方法の説明",
      "tools_to_use": ["tool_name1", "tool_name2"],
      "priority": 1
    }}
  ]
}}
```"""

EXPLORE_PROMPT = """## 探索フェーズ — ツール選択

### 検証する仮説:
{hypotheses}

### 利用可能なツール:
{tool_schemas}

### これまでのツール実行結果:
{previous_results}

### 指示:
各仮説を検証するために実行すべきツールを選択してください。
既に実行済みのツールは避け、追加情報が得られるツールを選んでください。

以下のJSON形式で出力してください：
```json
{{
  "tool_calls": [
    {{
      "hypothesis_id": "H-001",
      "tool_name": "population_statistics",
      "parameters": {{"fiscal_year": {fiscal_year}}},
      "reason": "母集団の全体像を把握するため"
    }}
  ]
}}
```"""

VERIFY_PROMPT = """## 検証フェーズ

### 仮説:
{hypotheses}

### ツール実行結果:
{tool_results}

### 指示:
各仮説について、ツール実行結果に基づきエビデンスを評価し、
支持度（0.0〜1.0）と判定を行ってください。

判定基準:
- **supported** (≥0.7): 十分なエビデンスで支持される
- **partially_supported** (0.4〜0.7): 部分的に支持されるが追加検証が必要
- **inconclusive** (0.2〜0.4): エビデンス不十分で判断不能
- **refuted** (<0.2): エビデンスが仮説を否定

以下のJSON形式で出力してください：
```json
{{
  "verifications": [
    {{
      "hypothesis_id": "H-001",
      "grounding_score": 0.85,
      "verdict": "supported",
      "evidence_for": ["支持するエビデンス1", "支持するエビデンス2"],
      "evidence_against": ["反証1"],
      "needs_more_exploration": false
    }}
  ]
}}
```"""

SYNTHESIZE_PROMPT = """## 統合フェーズ — インサイト生成

### 検証済み仮説:
{verified_hypotheses}

### 全ツール実行結果の要約:
{tool_summaries}

### 指示:
検証結果から、監査チームに報告すべきインサイトを生成してください。

各インサイトは以下を含むこと：
- 具体的な数値に基づく発見事項
- 重篤度の評価 (CRITICAL/HIGH/MEDIUM/LOW/INFO)
- 改善推奨事項

最後にエグゼクティブサマリー（300〜500字）も生成してください。

以下のJSON形式で出力してください：
```json
{{
  "insights": [
    {{
      "id": "INS-001",
      "title": "インサイトタイトル",
      "description": "詳細説明（具体的な数値を含む、200〜400字）",
      "category": "risk",
      "severity": "HIGH",
      "affected_amount": 50000000,
      "affected_count": 150,
      "recommendations": ["推奨事項1", "推奨事項2"],
      "related_hypotheses": ["H-001"]
    }}
  ],
  "executive_summary": "エグゼクティブサマリー本文..."
}}
```"""

# JAIA 開発計画書

## 1. 開発フェーズ概要

### 1.1 フェーズ構成

```
Phase 0: 基盤構築          [2週間]  ━━━━━━━━━━
Phase 1: データ基盤        [3週間]  ━━━━━━━━━━━━━━━
Phase 2: バッチ処理        [4週間]  ━━━━━━━━━━━━━━━━━━━━
Phase 3: ダッシュボード    [5週間]  ━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 4: AIエージェント    [5週間]  ━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 5: レポート生成      [3週間]  ━━━━━━━━━━━━━━━
Phase 6: 統合・品質保証    [3週間]  ━━━━━━━━━━━━━━━
Phase 7: デプロイ準備      [2週間]  ━━━━━━━━━━
────────────────────────────────────────────────
合計:                      27週間 (約7ヶ月)
```

### 1.2 マイルストーン

| マイルストーン | 到達基準 | 目標週 |
|--------------|---------|--------|
| M1: 基盤完了 | 開発環境構築、CI/CD、プロジェクト構造 | Week 2 |
| M2: データ取込可能 | AICPA準拠インポート、検証、DB構築 | Week 5 |
| M3: バッチ処理完了 | 85ルール、5ML手法、集計テーブル | Week 9 |
| M4: MVP | サマリー+3タブ、基本フィルタ | Week 12 |
| M5: ダッシュボード完了 | 11タブ全機能 | Week 14 |
| M6: AI分析可能 | 10エージェント、自律分析 | Week 19 |
| M7: レポート生成 | PPT/PDF自動生成 | Week 22 |
| M8: β版リリース | 統合テスト完了、ドキュメント | Week 25 |
| M9: 本番リリース | インストーラー、配布準備 | Week 27 |

---

## 2. Phase 0: 基盤構築 [Week 1-2]

### 2.1 目標
- 開発環境の標準化
- プロジェクト構造の確立
- CI/CDパイプラインの構築

### 2.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| P0-01 | Git リポジトリ初期化、ブランチ戦略定義 | Dev | 0.5d | - |
| P0-02 | Python環境構築 (pyproject.toml, ruff, mypy) | Backend | 1d | P0-01 |
| P0-03 | Node環境構築 (package.json, ESLint, Prettier) | Frontend | 1d | P0-01 |
| P0-04 | ディレクトリ構造作成 | Dev | 0.5d | P0-02, P0-03 |
| P0-05 | DuckDB/SQLite 接続モジュール | Backend | 1d | P0-02 |
| P0-06 | FastAPI アプリケーション雛形 | Backend | 1d | P0-02 |
| P0-07 | Electron + React 雛形 | Frontend | 2d | P0-03 |
| P0-08 | IPC通信基盤 | Frontend | 1d | P0-07 |
| P0-09 | CI/CDパイプライン (GitHub Actions) | DevOps | 1d | P0-01 |
| P0-10 | 開発ドキュメント (CONTRIBUTING.md) | Dev | 0.5d | - |

### 2.3 成果物
- [x] プロジェクトリポジトリ
- [x] 開発環境構築手順書
- [x] CI/CD設定ファイル
- [x] 基本アプリケーション雛形

---

## 3. Phase 1: データ基盤 [Week 3-5]

### 3.1 目標
- AICPA準拠データモデル実装
- データインポート機能
- 入力検証・マッピング機能

### 3.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| P1-01 | DuckDBスキーマ定義 (journal_entries等) | Backend | 2d | P0-05 |
| P1-02 | SQLiteスキーマ定義 (metadata等) | Backend | 1d | P0-05 |
| P1-03 | マイグレーション機構実装 | Backend | 1d | P1-01, P1-02 |
| P1-04 | Pydanticモデル定義 | Backend | 2d | P1-01 |
| P1-05 | CSVインポート (Polars) | Backend | 2d | P1-04 |
| P1-06 | Excelインポート | Backend | 1d | P1-05 |
| P1-07 | 入力検証エンジン (10チェック) | Backend | 3d | P1-05 |
| P1-08 | 科目マッピングサービス | Backend | 2d | P1-01 |
| P1-09 | 網羅性チェック (TB/CoA/JE照合) | Backend | 2d | P1-07 |
| P1-10 | インポートAPIエンドポイント | Backend | 1d | P1-05, P1-07 |
| P1-11 | インポートUI (ファイル選択、プレビュー) | Frontend | 3d | P1-10 |
| P1-12 | マッピングUI | Frontend | 2d | P1-08 |
| P1-13 | 会計期間管理API/UI | Full | 2d | P1-01 |

### 3.3 成果物
- [x] データベーススキーマ
- [x] インポート機能（CSV/Excel）
- [x] 入力検証レポート
- [x] 科目マッピング機能
- [x] 会計期間管理画面

---

## 4. Phase 2: バッチ処理 [Week 6-9]

### 4.1 目標
- 85ルールの実装
- 5種類のML異常検知
- 集計テーブル生成
- 財務指標計算

### 4.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| **ルールエンジン** |
| P2-01 | ルールエンジン基盤 | Backend | 2d | P1-04 |
| P2-02 | 金額ルール (15件) | Backend | 3d | P2-01 |
| P2-03 | 時間ルール (10件) | Backend | 2d | P2-01 |
| P2-04 | 勘定ルール (20件) | Backend | 3d | P2-01 |
| P2-05 | 承認ルール (8件) | Backend | 2d | P2-01 |
| P2-06 | 摘要ルール (12件) | Backend | 2d | P2-01 |
| P2-07 | パターンルール (10件) | Backend | 3d | P2-01 |
| P2-08 | 趨勢ルール (10件) | Backend | 3d | P2-01 |
| **機械学習** |
| P2-09 | Isolation Forest実装 | Backend | 2d | P1-04 |
| P2-10 | Local Outlier Factor実装 | Backend | 1d | P2-09 |
| P2-11 | One-Class SVM実装 | Backend | 1d | P2-09 |
| P2-12 | Autoencoder実装 | Backend | 2d | P2-09 |
| P2-13 | Benford分析実装 | Backend | 2d | P2-09 |
| P2-14 | 統合スコアリング | Backend | 2d | P2-02~P2-13 |
| **集計** |
| P2-15 | 期間×勘定集計 | Backend | 1d | P1-01 |
| P2-16 | トレンド集計 (MoM/YoY) | Backend | 2d | P2-15 |
| P2-17 | ベンフォード集計 | Backend | 1d | P2-13 |
| P2-18 | 資金フロー集計 | Backend | 1d | P2-15 |
| P2-19 | 時間分布集計 | Backend | 1d | P2-15 |
| P2-20 | ユーザーパターン集計 | Backend | 1d | P2-15 |
| **財務指標** |
| P2-21 | 回転期間計算 | Backend | 1d | P1-01 |
| P2-22 | 流動性比率計算 | Backend | 1d | P2-21 |
| P2-23 | 収益性指標計算 | Backend | 1d | P2-21 |
| **バッチオーケストレーション** |
| P2-24 | バッチ実行管理 | Backend | 2d | P2-14~P2-23 |
| P2-25 | 進捗通知 (WebSocket/SSE) | Backend | 1d | P2-24 |

### 4.3 成果物
- [x] 85ルール実装
- [x] 5種ML異常検知
- [x] 17集計テーブル
- [x] 財務指標計算エンジン
- [x] バッチ実行管理

---

## 5. Phase 3: ダッシュボード [Week 10-14]

### 5.1 目標
- 11タブのダッシュボード
- グローバルフィルタ
- インタラクティブチャート

### 5.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| **共通基盤** |
| P3-01 | Zustand ストア設計 | Frontend | 2d | P0-07 |
| P3-02 | APIクライアント | Frontend | 1d | P0-08 |
| P3-03 | グローバルフィルタUI | Frontend | 3d | P3-01 |
| P3-04 | フィルタプリセット機能 | Frontend | 1d | P3-03 |
| P3-05 | チャート共通コンポーネント | Frontend | 2d | P3-01 |
| **タブ実装** |
| P3-06 | サマリータブ | Frontend | 3d | P3-05 |
| P3-07 | 時系列分析タブ | Frontend | 3d | P3-06 |
| P3-08 | 勘定科目分析タブ | Frontend | 4d | P3-07 |
| P3-09 | 試算表・財務諸表タブ | Frontend | 3d | P3-08 |
| P3-10 | 財務指標分析タブ | Frontend | 3d | P2-23 |
| P3-11 | 資金フロー分析タブ (サンキー) | Frontend | 4d | P2-18 |
| P3-12 | 異常検知・リスクタブ | Frontend | 4d | P2-14 |
| P3-13 | ベンフォード分析タブ | Frontend | 2d | P2-17 |
| P3-14 | ユーザー・承認タブ | Frontend | 3d | P2-20 |
| P3-15 | 仕訳明細検索タブ | Frontend | 3d | P3-05 |
| P3-16 | AI分析レポートタブ (枠) | Frontend | 1d | - |
| **ドリルダウン** |
| P3-17 | ドリルダウン機能実装 | Frontend | 2d | P3-06~P3-15 |
| P3-18 | 仕訳詳細モーダル | Frontend | 2d | P3-17 |
| **Dashboard API** |
| P3-19 | Dashboard API実装 | Backend | 5d | P2-15~P2-23 |

### 5.3 成果物
- [x] 11タブダッシュボード
- [x] グローバルフィルタ
- [x] インタラクティブドリルダウン
- [x] 仕訳詳細表示

---

## 6. Phase 4: AIエージェント [Week 15-19]

### 6.1 目標
- 10エージェント実装
- LangGraphワークフロー
- Human-in-the-Loop
- 操作可視化UI

### 6.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| **LLMプロバイダー** |
| P4-01 | LLMプロバイダー抽象化 | Backend | 2d | - |
| P4-02 | AWS Bedrock実装 | Backend | 2d | P4-01 |
| P4-03 | Vertex AI実装 | Backend | 2d | P4-01 |
| P4-04 | Azure OpenAI実装 | Backend | 2d | P4-01 |
| P4-05 | Anthropic Direct実装 | Backend | 1d | P4-01 |
| P4-06 | フォールバック機構 | Backend | 1d | P4-02~P4-05 |
| **エージェントツール** |
| P4-07 | Dashboard Tools実装 | Backend | 3d | P3-19 |
| P4-08 | Data Tools実装 | Backend | 2d | P1-04 |
| P4-09 | Visualization Tools実装 | Backend | 2d | P3-05 |
| P4-10 | Verification Tools実装 | Backend | 2d | P2-14 |
| **専門エージェント** |
| P4-11 | Orchestrator Agent | Backend | 3d | P4-07~P4-10 |
| P4-12 | Explorer Agent | Backend | 2d | P4-07 |
| P4-13 | TrendAnalyzer Agent | Backend | 2d | P4-08 |
| P4-14 | RiskAnalyzer Agent | Backend | 2d | P4-08 |
| P4-15 | FinancialAnalyzer Agent | Backend | 2d | P4-08 |
| P4-16 | Investigator Agent | Backend | 2d | P4-07 |
| P4-17 | Verifier Agent | Backend | 2d | P4-10 |
| P4-18 | Hypothesis Agent | Backend | 2d | P4-01 |
| P4-19 | Visualizer Agent | Backend | 2d | P4-09 |
| P4-20 | Reporter Agent | Backend | 2d | P4-01 |
| **LangGraphワークフロー** |
| P4-21 | State Machine設計 | Backend | 2d | P4-11~P4-20 |
| P4-22 | 自律分析フロー実装 | Backend | 3d | P4-21 |
| P4-23 | Human-in-the-Loop実装 | Backend | 2d | P4-22 |
| P4-24 | 判断ルール実装 | Backend | 2d | P4-22 |
| **UI** |
| P4-25 | チャットUI | Frontend | 3d | P0-07 |
| P4-26 | 操作可視化パネル | Frontend | 3d | P4-22 |
| P4-27 | 進捗表示・操作履歴 | Frontend | 2d | P4-26 |
| P4-28 | Human-in-the-Loop UI | Frontend | 2d | P4-23 |
| **メモ・タグ** |
| P4-29 | メモ機能実装 | Full | 2d | P1-04 |
| P4-30 | タグ機能実装 | Full | 2d | P4-29 |

### 6.3 成果物
- [x] 10エージェント
- [x] 4LLMプロバイダー対応
- [x] 自律分析ワークフロー
- [x] Human-in-the-Loop
- [x] チャットUI
- [x] 操作可視化

---

## 7. Phase 5: レポート生成 [Week 20-22]

### 7.1 目標
- 洞察生成エンジン
- PPT自動生成 (10スライド)
- PDF自動生成 (20-30ページ)

### 7.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| **洞察生成** |
| P5-01 | 洞察生成エンジン | Backend | 3d | P4-22 |
| P5-02 | 重要度評価・優先順位付け | Backend | 2d | P5-01 |
| P5-03 | クラスタリング・ストーリー構築 | Backend | 2d | P5-02 |
| P5-04 | 提言生成 | Backend | 2d | P5-03 |
| **PPT生成** |
| P5-05 | PPTテンプレート設計 | Design | 2d | - |
| P5-06 | python-pptx基盤 | Backend | 2d | P5-05 |
| P5-07 | 表紙・サマリースライド | Backend | 1d | P5-06 |
| P5-08 | チャート埋め込み | Backend | 2d | P5-06 |
| P5-09 | 発見事項スライド生成 | Backend | 2d | P5-04, P5-08 |
| P5-10 | 提言スライド生成 | Backend | 1d | P5-09 |
| **PDF生成** |
| P5-11 | PDFテンプレート設計 | Design | 2d | - |
| P5-12 | ReportLab基盤 | Backend | 2d | P5-11 |
| P5-13 | セクション生成 | Backend | 3d | P5-12 |
| P5-14 | 詳細データテーブル | Backend | 2d | P5-13 |
| **UI** |
| P5-15 | レポート生成UI | Frontend | 2d | P5-06, P5-12 |
| P5-16 | レポートプレビュー | Frontend | 2d | P5-15 |
| P5-17 | ダウンロード機能 | Frontend | 1d | P5-16 |

### 7.3 成果物
- [x] 洞察生成エンジン
- [x] PPT自動生成 (10スライド標準)
- [x] PDF自動生成 (20-30ページ標準)
- [x] レポートプレビュー・ダウンロード

---

## 8. Phase 6: 統合・品質保証 [Week 23-25]

### 8.1 目標
- 全機能統合テスト
- パフォーマンス最適化
- セキュリティ確認
- ドキュメント整備

### 8.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| **テスト** |
| P6-01 | 単体テスト補完 | Dev | 3d | - |
| P6-02 | 統合テスト作成 | QA | 5d | Phase 1-5 |
| P6-03 | E2Eテスト作成 | QA | 5d | P6-02 |
| P6-04 | パフォーマンステスト | QA | 3d | P6-03 |
| P6-05 | 大規模データテスト (1000万件) | QA | 2d | P6-04 |
| **最適化** |
| P6-06 | クエリ最適化 | Backend | 3d | P6-04 |
| P6-07 | フロントエンド最適化 | Frontend | 2d | P6-04 |
| P6-08 | メモリ使用量最適化 | Dev | 2d | P6-05 |
| **セキュリティ** |
| P6-09 | セキュリティレビュー | Security | 2d | - |
| P6-10 | データマスキング確認 | Backend | 1d | P6-09 |
| P6-11 | 監査ログ確認 | Backend | 1d | P6-09 |
| **ドキュメント** |
| P6-12 | ユーザーマニュアル作成 | Tech Writer | 5d | Phase 1-5 |
| P6-13 | 管理者ガイド作成 | Tech Writer | 3d | P6-12 |
| P6-14 | APIドキュメント (OpenAPI) | Backend | 2d | Phase 1-5 |

### 8.3 成果物
- [x] テストレポート
- [x] パフォーマンス報告書
- [x] セキュリティ確認書
- [x] ユーザーマニュアル
- [x] APIドキュメント

---

## 9. Phase 7: デプロイ準備 [Week 26-27]

### 9.1 目標
- インストーラー作成
- 配布パッケージ準備
- 運用準備

### 9.2 タスク一覧

| ID | タスク | 担当 | 工数 | 依存 |
|----|-------|------|------|------|
| P7-01 | PyInstaller設定 | DevOps | 2d | Phase 6 |
| P7-02 | Electron Builder設定 | DevOps | 2d | Phase 6 |
| P7-03 | Windowsインストーラー作成 | DevOps | 2d | P7-01, P7-02 |
| P7-04 | macOS DMG作成 | DevOps | 2d | P7-01, P7-02 |
| P7-05 | ポータブル版作成 | DevOps | 1d | P7-03 |
| P7-06 | 自動更新機構 | DevOps | 2d | P7-03, P7-04 |
| P7-07 | リリースノート作成 | PM | 1d | - |
| P7-08 | 最終検証 | QA | 2d | P7-03~P7-05 |
| P7-09 | 本番リリース | DevOps | 1d | P7-08 |

### 9.3 成果物
- [x] Windowsインストーラー (.exe)
- [x] macOS DMGパッケージ
- [x] ポータブル版 (.zip)
- [x] リリースノート

---

## 10. リソース計画

### 10.1 チーム構成

| ロール | 人数 | 担当フェーズ |
|--------|------|-------------|
| プロジェクトマネージャー | 1 | 全フェーズ |
| バックエンドエンジニア | 2 | Phase 1-5 |
| フロントエンドエンジニア | 2 | Phase 0, 3-5 |
| MLエンジニア | 1 | Phase 2, 4 |
| QAエンジニア | 1 | Phase 6-7 |
| テクニカルライター | 0.5 | Phase 6 |
| DevOpsエンジニア | 0.5 | Phase 0, 7 |

### 10.2 工数サマリー

| フェーズ | 期間 | 工数 (人日) |
|---------|------|------------|
| Phase 0 | 2週間 | 20 |
| Phase 1 | 3週間 | 45 |
| Phase 2 | 4週間 | 80 |
| Phase 3 | 5週間 | 75 |
| Phase 4 | 5週間 | 90 |
| Phase 5 | 3週間 | 45 |
| Phase 6 | 3週間 | 60 |
| Phase 7 | 2週間 | 25 |
| **合計** | **27週間** | **440人日** |

---

## 11. リスク管理

### 11.1 リスク一覧

| ID | リスク | 影響度 | 発生確率 | 対策 |
|----|-------|--------|---------|------|
| R1 | LLMプロバイダーAPI変更 | 高 | 中 | 抽象化層で吸収、複数プロバイダー対応 |
| R2 | パフォーマンス目標未達 | 高 | 中 | 早期からベンチマーク、事前集計最適化 |
| R3 | 大規模データでのメモリ不足 | 中 | 中 | ストリーミング処理、Polarsの活用 |
| R4 | Electron更新による破壊的変更 | 低 | 低 | バージョン固定、慎重なアップデート |
| R5 | AICPA規格の改定 | 低 | 低 | 拡張可能なデータモデル設計 |

### 11.2 コンティンジェンシー

- バッファ期間: 各フェーズに10%のバッファを含む
- スコープ調整: Phase 5のPDF生成を簡略化可能
- リソース追加: Phase 3-4でフロントエンド1名追加可能

---

## 12. 品質基準

### 12.1 コード品質

| 指標 | 基準 |
|------|------|
| テストカバレッジ | Backend: 80%以上、Frontend: 70%以上 |
| 静的解析 | ruff/mypy: エラーゼロ |
| コードレビュー | 全PRに1名以上のレビュー必須 |
| ドキュメント | 全publicクラス・関数にdocstring |

### 12.2 パフォーマンス基準

| 操作 | 目標 |
|------|------|
| ダッシュボード初期表示 | 500ms以下 |
| フィルタ適用 | 200ms以下 |
| チャット応答 | 2秒以下 |
| 自律分析1サイクル | 30秒以下 |
| レポート生成 (PPT) | 45秒以下 |

---

## 13. 開発環境

### 13.1 必要ツール

```
# Python
Python 3.11+
Poetry or pip with pyproject.toml

# Node.js
Node.js 20 LTS
npm or yarn

# エディタ
VSCode with extensions:
  - Python
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense

# データベース
DuckDB CLI
SQLite Browser (optional)

# Git
Git 2.40+
GitHub CLI (gh)
```

### 13.2 セットアップコマンド

```bash
# リポジトリクローン
git clone https://github.com/yourorg/jaia.git
cd jaia

# バックエンドセットアップ
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"

# フロントエンドセットアップ
cd ../frontend
npm install

# 開発サーバー起動
# ターミナル1: Backend
cd backend && uvicorn app.main:app --reload

# ターミナル2: Frontend
cd frontend && npm run dev
```

---

## 14. コミュニケーション計画

### 14.1 定例ミーティング

| 会議 | 頻度 | 参加者 | 目的 |
|------|------|--------|------|
| デイリースタンドアップ | 毎日 | 開発チーム | 進捗確認、ブロッカー共有 |
| スプリントレビュー | 週次 | 全員 | デモ、フィードバック |
| スプリント計画 | 週次 | 全員 | 次週タスク計画 |
| アーキテクチャレビュー | 隔週 | シニア | 設計判断、技術的負債 |

### 14.2 進捗報告

- GitHub Projects: タスク管理
- Slack/Teams: 日常コミュニケーション
- 週次レポート: ステークホルダー向け

---

**作成日**: 2026年2月1日
**作成者**: JAIA開発チーム
**次回レビュー**: Phase 0完了時

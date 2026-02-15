# JAIA API クイックリファレンス

本ドキュメントは、JAIAのAPIを素早く利用するためのリファレンスガイドです。
詳細な仕様は [04_api_design.md](04_api_design.md) を参照してください。

---

## 基本情報

| 項目 | 値 |
| ---- | --- |
| ベースURL | `http://localhost:8090/api/v1` |
| 認証 | 不要（ローカル実行） |
| Content-Type | `application/json` |
| 文字コード | UTF-8 |

---

## エンドポイント一覧（全41エンドポイント）

### システム（2）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| GET | `/health` | アプリケーションヘルスチェック |
| GET | `/` | アプリ情報（名称・バージョン・APIパス） |

### ヘルス（2）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| GET | `/api/v1/health/health` | API健全性確認 |
| GET | `/api/v1/health/status` | 詳細ステータス（DB接続含む） |

### データインポート（7）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| POST | `/api/v1/import/upload` | ファイルアップロード（CSV/XLSX/XLS） |
| GET | `/api/v1/import/preview/{temp_file_id}` | アップロードファイルのプレビュー |
| POST | `/api/v1/import/validate/{temp_file_id}` | バリデーション（エラー・警告レポート） |
| POST | `/api/v1/import/execute` | インポート実行（カラムマッピング指定） |
| POST | `/api/v1/import/master` | マスタデータインポート（勘定科目/部門/取引先/ユーザー） |
| GET | `/api/v1/import/mapping/suggest` | カラムマッピング自動提案 |
| DELETE | `/api/v1/import/temp/{temp_file_id}` | 一時ファイル削除 |

### ダッシュボード（6）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| GET | `/api/v1/dashboard/summary` | サマリー（件数・金額・リスク件数） |
| GET | `/api/v1/dashboard/timeseries` | 時系列データ（日次/週次/月次） |
| GET | `/api/v1/dashboard/accounts` | 勘定科目別分析（借方/貸方合計） |
| GET | `/api/v1/dashboard/risk` | リスク分析（High/Medium/Low/Minimal） |
| GET | `/api/v1/dashboard/kpi` | KPI指標 |
| GET | `/api/v1/dashboard/benford` | Benford分布分析 |

### バッチ処理（5）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| POST | `/api/v1/batch/start` | 非同期バッチ開始（full/quick/ml_only/rules_only） |
| GET | `/api/v1/batch/status/{job_id}` | ジョブ状況確認 |
| GET | `/api/v1/batch/jobs` | 最近のジョブ一覧 |
| GET | `/api/v1/batch/rules` | 登録ルール一覧（カテゴリ別） |
| POST | `/api/v1/batch/run-sync` | 同期バッチ実行（時間がかかる場合あり） |

### 分析（6）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| GET | `/api/v1/analysis/violations` | ルール違反一覧（フィルタ対応） |
| GET | `/api/v1/analysis/ml-anomalies` | ML異常検知結果（手法別） |
| GET | `/api/v1/analysis/risk-details` | リスクスコア詳細（エントリ別） |
| GET | `/api/v1/analysis/benford-detail` | Benford詳細分析（桁別分布） |
| GET | `/api/v1/analysis/rules-summary` | ルール違反サマリー（ルール別・カテゴリ別） |
| POST | `/api/v1/analysis/recalculate-scores` | リスクスコア再計算 |

### AIエージェント（8）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| POST | `/api/v1/agents/ask` | QAエージェントに質問 |
| POST | `/api/v1/agents/analyze` | リスク分析実行（分布・Benford・期間比較） |
| POST | `/api/v1/agents/investigate` | 調査実行（エントリ・ユーザー・ルール・仕訳） |
| POST | `/api/v1/agents/document` | 監査ドキュメント生成（サマリー・所見・マネジメントレター） |
| POST | `/api/v1/agents/review` | 所見レビュー（レビュー・優先順位・改善提案） |
| POST | `/api/v1/agents/workflow` | マルチエージェントワークフロー実行 |
| GET | `/api/v1/agents/workflows` | 利用可能ワークフロー一覧 |
| POST | `/api/v1/agents/route` | リクエスト自動ルーティング |

### レポート（5）

| メソッド | パス | 説明 |
| ------- | ---- | ---- |
| POST | `/api/v1/reports/generate` | レポート生成（7種類対応） |
| GET | `/api/v1/reports/templates` | テンプレート一覧 |
| GET | `/api/v1/reports/history` | 生成履歴 |
| GET | `/api/v1/reports/export/ppt` | PowerPointエクスポート |
| GET | `/api/v1/reports/export/pdf` | PDFエクスポート |

---

## 共通クエリパラメータ

| パラメータ | 型 | 説明 | 例 |
| --------- | -- | ---- | --- |
| `fiscal_year` | integer | 会計年度（必須が多い） | `2024` |
| `period_from` | integer | 期間開始（会計期間番号） | `1` |
| `period_to` | integer | 期間終了（会計期間番号） | `4` |
| `limit` | integer | 取得件数上限 | `100` |
| `offset` | integer | オフセット | `0` |

---

## リクエスト例

### ヘルスチェック

```bash
curl http://localhost:8090/health
```

レスポンス:

```json
{
  "status": "healthy",
  "app": "JAIA",
  "version": "0.2.1",
  "timestamp": "2026-02-15T10:00:00Z"
}
```

### ダッシュボードサマリー取得

```bash
curl "http://localhost:8090/api/v1/dashboard/summary?fiscal_year=2024"
```

### ファイルアップロード

```bash
curl -X POST "http://localhost:8090/api/v1/import/upload" \
  -F "file=@journal_entries.csv"
```

### バッチ処理実行（非同期）

```bash
curl -X POST "http://localhost:8090/api/v1/batch/start" \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "fiscal_year": 2024}'
```

### AIエージェントに質問

```bash
curl -X POST "http://localhost:8090/api/v1/agents/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "2024年度の高リスク仕訳を説明してください"}'
```

### PPTレポートエクスポート

```bash
curl "http://localhost:8090/api/v1/reports/export/ppt?fiscal_year=2024" \
  --output report.pptx
```

---

## レスポンス形式

### 成功時

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "abc123",
    "timestamp": "2026-02-15T10:00:00Z",
    "processing_time_ms": 150
  }
}
```

### エラー時

```json
{
  "success": false,
  "error": {
    "error_code": "VALIDATION_ERROR",
    "message": "パラメータが不正です",
    "detail": { ... }
  },
  "meta": {
    "request_id": "abc123",
    "timestamp": "2026-02-15T10:00:00Z"
  }
}
```

---

## エラーコード

| コード | HTTPステータス | 説明 |
| ------ | ------------- | ---- |
| `VALIDATION_ERROR` | 400 | リクエスト検証エラー |
| `SUSPICIOUS_REQUEST` | 400 | 不正リクエスト検出 |
| `IP_BLOCKED` | 403 | IPブロック |
| `NOT_FOUND` | 404 | リソースが見つからない |
| `CONFLICT` | 409 | リソース競合 |
| `IMPORT_ERROR` | 422 | インポート処理失敗 |
| `RATE_LIMIT_EXCEEDED` | 429 | レート制限超過 |
| `ANALYSIS_ERROR` | 500 | 分析処理失敗 |
| `INTERNAL_ERROR` | 500 | 内部エラー |
| `LLM_PROVIDER_ERROR` | 503 | LLMプロバイダーエラー |

---

## レート制限

| ヘッダー | 説明 |
| ------- | ---- |
| `X-RateLimit-Limit` | ウィンドウあたりの最大リクエスト数（デフォルト: 100） |
| `X-RateLimit-Remaining` | 残りリクエスト数 |
| `Retry-After` | 制限解除までの秒数（429レスポンス時） |

---

## リスクレベル定義

| レベル | スコア範囲 | 説明 |
| ------ | --------- | ---- |
| Critical | 80-100 | 即時対応が必要 |
| High | 60-79 | 優先的な確認が必要 |
| Medium | 40-59 | 通常の確認対象 |
| Low | 0-39 | 低リスク |

---

## 監査ルールカテゴリ

| カテゴリ | コード | ルール数 | 説明 |
| ------- | ------ | ------- | ---- |
| 金額 | AMT | 12 | 金額に関する異常検出 |
| 時間 | TIM | 10 | 時間・日付に関する異常検出 |
| 勘定科目 | ACC | 10 | 勘定科目に関する異常検出 |
| 承認 | APR | 10 | 承認フローに関する異常検出 |
| ML異常 | ML | 6 | 機械学習による異常検出 |
| Benford | BEN | 10 | Benfordの法則による分析 |

---

## Swagger UI

開発環境（`DEBUG=true`）では Swagger UI が利用可能です:

- Swagger UI: `http://localhost:8090/docs`
- ReDoc: `http://localhost:8090/redoc`
- OpenAPI JSON: `http://localhost:8090/openapi.json`

※ 本番環境（`DEBUG=false`）ではセキュリティ上の理由で無効化されます。

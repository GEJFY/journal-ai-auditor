# JAIA トラブルシューティングガイド

よくある問題と解決方法をまとめています。

---

## 1. 起動・接続

### バックエンドが起動しない

**症状**: `uvicorn` 実行時にエラーが発生する

**原因と解決策**:

```powershell
# ポートが既に使用中
# → 別プロセスを停止するか、PORT環境変数で変更
netstat -ano | findstr :8090

# モジュールが見つからない
# → 仮想環境をアクティベート
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# データディレクトリがない
# → 自動作成されるが、権限問題の場合は手動作成
mkdir data
```

### フロントエンドが起動しない

**症状**: `npm run dev` でエラーが発生する

```powershell
# node_modules がない
npm install

# ポート5290が使用中
# → vite.config.ts の server.port を変更、または他プロセスを停止

# Electron の dist/main/index.js が見つからない
npm run build:main
```

### API に接続できない

**症状**: フロントエンドから「接続エラー」が表示される

- バックエンドが起動しているか確認: `curl http://localhost:8090/health`
- CORS設定を確認: `CORS_ALLOWED_ORIGINS` にフロントエンドのURLが含まれているか
- ファイアウォールがポート8090をブロックしていないか確認

---

## 2. データインポート

### CSV ファイルがインポートできない

**原因**:
- **文字コード**: UTF-8 または Shift_JIS に対応。その他のエンコーディングはUTF-8に変換してください
- **ファイルサイズ**: nginx経由の場合は100MB制限（`client_max_body_size`）
- **カラム名**: AICPA GL_Detail 標準に準拠したカラム名を推奨

**対処**:

```powershell
# プレビューでカラムを確認
curl "http://localhost:8090/api/v1/import/preview/{temp_file_id}"

# マッピング自動提案を利用
curl "http://localhost:8090/api/v1/import/mapping/suggest?columns=col1,col2,col3"
```

### Excel ファイルがインポートできない

- `.xlsx` と `.xls` 形式に対応
- パスワード保護されたファイルは非対応
- シートが複数ある場合、最初のシートが使用されます

---

## 3. LLM / AIエージェント

### LLM プロバイダーエラー

**症状**: `LLM_PROVIDER_ERROR` が返される

```powershell
# 環境変数を確認
# backend/.env でプロバイダーとAPIキーが設定されているか
cat backend/.env | Select-String "LLM_PROVIDER|API_KEY"
```

**プロバイダー別チェック**:

| プロバイダー | 確認事項 |
| ----------- | ------- |
| `azure_foundry` | `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, `AZURE_FOUNDRY_DEPLOYMENT` が設定済みか |
| `bedrock` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` が設定済みか |
| `anthropic` | `ANTHROPIC_API_KEY` が `sk-ant-` で始まるか |
| `openai` | `OPENAI_API_KEY` が `sk-` で始まるか |
| `ollama` | Ollama がローカルで起動しているか (`curl http://localhost:11434/api/tags`) |

### AIエージェントのレスポンスが遅い

- LLMの応答時間に依存します（通常5-30秒）
- `batch/run-sync` は大量データ処理時に数分かかる場合があります
- 非同期版 `batch/start` の使用を推奨

---

## 4. バッチ処理

### バッチジョブが失敗する

```powershell
# ジョブ状況を確認
curl "http://localhost:8090/api/v1/batch/status/{job_id}"

# 最近のジョブ一覧で失敗を確認
curl "http://localhost:8090/api/v1/batch/jobs?limit=5"
```

**よくある原因**:
- データが未インポート（`fiscal_year` のデータが存在しない）
- DuckDB ファイルが破損（`data/jaia.duckdb` を削除して再起動）
- メモリ不足（大量データ処理時は `BATCH_SIZE` を下げる）

---

## 5. Docker

### Docker Compose で起動できない

```powershell
# ログを確認
docker-compose logs backend
docker-compose logs frontend

# ビルドし直す
docker-compose build --no-cache
docker-compose up -d
```

### バックエンドコンテナが落ちる

- メモリ不足の可能性。`docker stats` で確認
- `.env` ファイルがマウントされているか確認
- ポート8090が他のサービスと競合していないか確認

---

## 6. テスト

### バックエンドテストが失敗する

```powershell
# 仮想環境で実行
cd backend
.venv\Scripts\Activate.ps1
python -m pytest tests/ -v

# 特定のテストだけ実行
python -m pytest tests/test_models.py -v

# LLM関連テストをスキップ
python -m pytest tests/ -v -k "not llm"
```

### フロントエンドテストが失敗する

```powershell
cd frontend
npm test

# カバレッジ確認
npm run test:coverage
```

**カバレッジ閾値**: statements 50%, branches 45%, functions 30%, lines 50%

---

## 7. パフォーマンス

### API レスポンスが遅い

- `X-Processing-Time-Ms` ヘッダーで処理時間を確認
- DuckDB インデックスが適切か確認
- `CACHE_TTL_SECONDS` を調整（デフォルト: 300秒）
- `MAX_WORKERS` を増やす（デフォルト: 4）

### レート制限に引っかかる

- デフォルト: 100リクエスト/分
- `X-RateLimit-Remaining` ヘッダーで残り回数を確認
- `/health` エンドポイントはレート制限対象外

---

## 8. セキュリティ

### IP がブロックされた

**症状**: 403 `IP_BLOCKED` レスポンス

- 疑わしいリクエスト（SQLインジェクション、XSS等のパターン）を10回送信するとIPが15分間ブロックされます
- サーバー再起動でブロックはリセットされます

### Swagger UI にアクセスできない

- 本番環境（`DEBUG=false`）では無効化されています
- 開発環境では `http://localhost:8090/docs` でアクセス可能
- `backend/.env` で `DEBUG=true` に設定してください

---

## ログの確認

```powershell
# アプリケーションログ（起動時のコンソール出力）
# ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR）

# Docker 環境の場合
docker-compose logs -f backend

# リクエストIDでトレース
# レスポンスの X-Request-ID ヘッダーでログを検索
```

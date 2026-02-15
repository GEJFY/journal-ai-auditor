# JAIA スクリプト一覧

開発・運用に使用するユーティリティスクリプトです。

## セットアップ

| スクリプト | 説明 |
| --------- | ---- |
| `setup.ps1` | 開発環境の初期セットアップ（Python venv作成、依存インストール、npm install） |
| `setup_azure.ps1` | Azure AI Foundry のセットアップ（Azure CLI使用、`-Model`, `-Location`, `-Destroy` パラメータ対応） |
| `quick_setup.py` | 対話式セットアップウィザード（日本語/英語対応、LLMプロバイダー選択） |

## 起動

| スクリプト | 説明 |
| --------- | ---- |
| `start_all.ps1` | バックエンド + フロントエンドを同時起動 |
| `start_backend.ps1` | FastAPI バックエンドのみ起動（`http://localhost:8090`） |
| `start_frontend.ps1` | Electron + React フロントエンドのみ起動（`http://localhost:5290`） |

## テスト

| スクリプト | 説明 |
| --------- | ---- |
| `run_tests.ps1` | テストスイート実行（`-Unit`, `-Integration`, `-E2E`, `-Coverage` パラメータ対応） |
| `test_integration.ps1` | APIエンドポイントの統合テスト |

## デモ

| スクリプト | 説明 |
| --------- | ---- |
| `demo.ps1` | デモ実行（環境チェック、サンプルデータ読込、バックエンド起動、APIテスト） |

## データベースユーティリティ

| スクリプト | 説明 |
| --------- | ---- |
| `init_full_schema.py` | データベーススキーマの完全初期化（rule_violationsテーブル含む） |
| `add_analysis_columns.py` | journal_entriesテーブルに分析用カラムを追加 |
| `recreate_violations_table.py` | rule_violationsテーブルの再作成（auto-increment対応） |
| `load_sample_data.py` | サンプルデータをデータベースに直接読み込み |
| `insert_sample_violations.py` | テスト用サンプル違反データの挿入 |
| `run_batch_with_violations.py` | バッチ処理を実行して違反を保存 |

## 使い方

```powershell
# 初回セットアップ
.\scripts\setup.ps1

# 起動
.\scripts\start_all.ps1

# テスト
.\scripts\run_tests.ps1 -Unit -Coverage
```

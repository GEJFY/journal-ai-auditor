# JAIA 開発ガイド

## 1. ブランチ戦略

### 1.1 ブランチ構成

```
main                    # 本番リリース用（保護）
├── develop            # 開発統合ブランチ
│   ├── feature/*      # 機能開発ブランチ
│   ├── bugfix/*       # バグ修正ブランチ
│   └── refactor/*     # リファクタリングブランチ
├── release/*          # リリース準備ブランチ
└── hotfix/*           # 緊急修正ブランチ
```

### 1.2 ブランチ命名規則

| ブランチタイプ | 命名規則 | 例 |
|--------------|---------|-----|
| feature | `feature/{issue-id}-{short-description}` | `feature/P1-05-csv-import` |
| bugfix | `bugfix/{issue-id}-{short-description}` | `bugfix/123-filter-error` |
| refactor | `refactor/{short-description}` | `refactor/dashboard-state` |
| release | `release/v{major}.{minor}.{patch}` | `release/v1.0.0` |
| hotfix | `hotfix/v{version}-{description}` | `hotfix/v1.0.1-crash-fix` |

### 1.3 マージルール

1. **develop → main**: リリース時のみ、PRレビュー必須
2. **feature → develop**: PRレビュー1名以上必須
3. **hotfix → main/develop**: 緊急時のみ、事後レビュー可

---

## 2. 開発環境セットアップ

### 2.1 必要条件

- Python 3.11+
- Node.js 20 LTS
- Git 2.40+
- VSCode（推奨）

### 2.2 初期セットアップ

```bash
# リポジトリクローン
git clone https://github.com/yourorg/jaia.git
cd jaia

# バックエンドセットアップ
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -e ".[dev]"

# フロントエンドセットアップ
cd ../frontend
npm install
```

### 2.3 開発サーバー起動

```bash
# ターミナル1: バックエンド
cd backend
uvicorn app.main:app --reload --port 8000

# ターミナル2: フロントエンド
cd frontend
npm run dev
```

---

## 3. コーディング規約

### 3.1 Python

- **フォーマッター**: ruff format
- **リンター**: ruff check
- **型チェック**: mypy（strict mode）
- **docstring**: Google Style

```python
def process_journal(
    entries: list[JournalEntry],
    *,
    validate: bool = True,
) -> ProcessResult:
    """仕訳データを処理する。

    Args:
        entries: 処理対象の仕訳エントリリスト
        validate: 検証を実行するかどうか

    Returns:
        処理結果を含むProcessResultオブジェクト

    Raises:
        ValidationError: 検証に失敗した場合
    """
    ...
```

### 3.2 TypeScript/React

- **フォーマッター**: Prettier
- **リンター**: ESLint
- **コンポーネント**: 関数コンポーネント + hooks
- **状態管理**: Zustand

```typescript
interface DashboardProps {
  /** 表示期間 */
  period: FiscalPeriod;
  /** フィルタ設定 */
  filters: FilterState;
}

/**
 * メインダッシュボードコンポーネント
 */
export function Dashboard({ period, filters }: DashboardProps): JSX.Element {
  const { data, isLoading } = useDashboardData(period, filters);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="dashboard">
      {/* ... */}
    </div>
  );
}
```

---

## 4. コミット規約

### 4.1 コミットメッセージ形式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.2 タイプ一覧

| タイプ | 説明 |
|--------|------|
| feat | 新機能追加 |
| fix | バグ修正 |
| docs | ドキュメント変更 |
| style | フォーマット変更（動作に影響なし） |
| refactor | リファクタリング |
| perf | パフォーマンス改善 |
| test | テスト追加・修正 |
| chore | ビルド・ツール変更 |

### 4.3 例

```
feat(import): CSVインポート機能を追加

- Polarsを使用した高速CSV読み込み
- AICPA GL_Detail形式のバリデーション
- エラー行のスキップ機能

Closes #P1-05
```

---

## 5. プルリクエスト

### 5.1 PRテンプレート

```markdown
## 概要
<!-- 変更内容の簡潔な説明 -->

## 変更タイプ
- [ ] 新機能
- [ ] バグ修正
- [ ] リファクタリング
- [ ] ドキュメント

## テスト
- [ ] 単体テスト追加
- [ ] 統合テスト追加
- [ ] 手動テスト実施

## チェックリスト
- [ ] コードがスタイルガイドに準拠
- [ ] セルフレビュー完了
- [ ] コメント追加（必要な箇所）
- [ ] ドキュメント更新（必要な場合）

## 関連Issue
Closes #XX
```

### 5.2 レビュー基準

1. **機能**: 仕様通りに動作するか
2. **コード品質**: 可読性、保守性
3. **テスト**: カバレッジ、エッジケース
4. **パフォーマンス**: 明らかな問題がないか
5. **セキュリティ**: 脆弱性がないか

---

## 6. テスト

### 6.1 バックエンド

```bash
# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=app --cov-report=html

# 特定テスト
pytest tests/test_import.py -v
```

### 6.2 フロントエンド

```bash
# 全テスト実行
npm test

# カバレッジ付き
npm run test:coverage

# E2Eテスト
npm run test:e2e
```

---

## 7. CI/CD

### 7.1 自動チェック

PRごとに以下が自動実行されます：

1. **Lint**: ruff, ESLint
2. **Format Check**: ruff format, Prettier
3. **Type Check**: mypy, TypeScript
4. **Unit Tests**: pytest, Jest
5. **Build Check**: Electron build

### 7.2 リリースフロー

1. `release/vX.Y.Z` ブランチ作成
2. バージョン番号更新
3. リリースノート作成
4. `main` へマージ
5. タグ付け → 自動ビルド・配布

---

## 8. ディレクトリ構造

```
jaia/
├── backend/                 # バックエンド (Python/FastAPI)
│   ├── app/
│   │   ├── api/            # APIエンドポイント
│   │   ├── core/           # 設定、セキュリティ
│   │   ├── db/             # データベース
│   │   ├── models/         # Pydanticモデル
│   │   ├── services/       # ビジネスロジック
│   │   │   ├── import/     # インポート処理
│   │   │   ├── rules/      # ルールエンジン
│   │   │   ├── ml/         # 機械学習
│   │   │   └── agents/     # AIエージェント
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/                # フロントエンド (Electron/React)
│   ├── src/
│   │   ├── main/           # Electronメインプロセス
│   │   ├── renderer/       # Reactアプリ
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── stores/
│   │   │   └── pages/
│   │   └── preload/        # プリロードスクリプト
│   ├── package.json
│   └── electron-builder.yml
├── docs/                    # ドキュメント
├── sample_data/             # サンプルデータ
└── .github/                 # GitHub設定
    └── workflows/
```

---

## 9. 問い合わせ

- **Slack**: #jaia-dev
- **Issue**: GitHub Issues
- **緊急時**: プロジェクトマネージャーへ連絡

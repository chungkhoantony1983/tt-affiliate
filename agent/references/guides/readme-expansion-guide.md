# README 展開ガイドライン

> **SSoT**: `.claude/references/guides/readme-expansion-guide.md` が正本。`/sync` で全リポに配布される。

各リポジトリの主要コードディレクトリに README.md を展開する際の基準・手順を定義する。

## 「主要コードディレクトリ」の定義

### 対象階層

リポジトリルートから **第1階層および第2階層** のディレクトリを対象とする。

- 例: `src/`（対象）、`src/api/`（対象）、`src/api/v1/`（対象外）

### 除外対象

| 除外ディレクトリ | 理由 |
|:----------------|:-----|
| `node_modules/`, `vendor/` | 依存パッケージ（自動生成） |
| `__pycache__/`, `.pytest_cache/` | キャッシュ |
| `.git/`, `.worktrees/` | バージョン管理 |
| `.claude/` | `/sync` で SSoT から配布（リポ固有 README 不要） |
| `.venv/`, `venv/` | Python 仮想環境 |

### 「主要」の判断基準

除外対象でないディレクトリのうち、以下の **いずれか1つ以上** を満たすもの:

1. **量的基準（ファイル数）**: 直下に **5つ以上のファイル** が存在
2. **量的基準（サブディレクトリ数）**: 直下に **2つ以上のサブディレクトリ** が存在
3. **質的基準（内容）**: ビジネスロジック、ドメインモデル、または重要な設定（IaC マニフェスト、デプロイ定義、DB 初期化等）を含む

## README レベルの選択

| Lv | 対象 | 行数 |
|:--:|:-----|:----:|
| 1 | リーフ/自明なディレクトリ | 4-8 |
| 2 | 主要機能ディレクトリ | 10-30 |
| 3 | フレームワーク中核ディレクトリ | 30+ |

テンプレート: `references/templates/readme-template.md`

### Lv 選択の目安

- **Lv.1**: ファイル数が少なく用途が単一（scripts/, mysql-init/ 等）
- **Lv.2**: 複数サブディレクトリを持つ機能モジュール（src/, jobs/, deploy/ 等）
- **Lv.3**: リポルートの README（通常既存）。コードディレクトリでは稀

## カバレッジ目標

**第1-2階層の主要コードディレクトリに限定して計測**（全ディレクトリは母数が大きすぎるため非現実的）。

| 段階 | 目標 |
|:-----|:----:|
| Phase 4 完了時 | 主要コードディレクトリの **80%** |
| 将来的理想値 | 主要コードディレクトリの **100%** |

## 実行手順（`/task @{repo}` での README 作成）

### 1. 対象ディレクトリの特定

```bash
# リポの第1-2階層ディレクトリを一覧化（除外適用）
find {repo}/ -maxdepth 2 -type d \
  ! -path '*/node_modules/*' ! -path '*/vendor/*' \
  ! -path '*/__pycache__/*' ! -path '*/.git/*' \
  ! -path '*/.worktrees/*' ! -path '*/.claude/*' \
  ! -path '*/.venv/*' | sort
```

### 2. 「主要」判定

各ディレクトリに対して判断基準を適用し、README 作成対象を確定する。

### 3. README 作成

1. `references/templates/readme-template.md` を参照
2. 適切な Lv を選択
3. ディレクトリの内容を Read ツールで確認
4. README.md を Write ツールで作成

### 4. 検証

```bash
bash .claude/scripts/verify-readme-coverage.sh {repo}/
```

### 5. コミット・PR

通常の `/push` フローに従う。ブランチ名: `docs/readme-expansion`

## 各リポの具体的対象（Phase 4 調査結果）

### module-d（パイロット候補）

| ディレクトリ | Lv | 内容 |
|:------------|:--:|:-----|
| `jobs/` | 2 | Azure Functions 基盤（不正検知） |
| `predictive-analytics/` | 2 | Azure ML パイプライン（6地域対応） |
| `scripts/` | 1 | ビルド・変換スクリプト（7件） |

### module-b（パイロット候補）

| ディレクトリ | Lv | 内容 |
|:------------|:--:|:-----|
| `src/` | 2 | ソースコードルート（15サブディレクトリ） |
| `src/api/` | 1 | REST API エンドポイント（28ファイル） |
| `src/model/` | 1 | データモデル（23ファイル） |
| `src/modules/` | 2 | 機能モジュール（institutions 含む） |
| `src/tasks/` | 1 | バックグラウンドタスク（50ファイル） |
| `test/` | 1 | テストスイート |
| `views/` | 1 | テンプレート（8サブディレクトリ） |

### module-c（パイロット候補）

| ディレクトリ | Lv | 内容 |
|:------------|:--:|:-----|
| `AI-OCRFunctionProj/` | 2 | AI-OCR API（Python） |
| `CorpInfoFunctionProj/` | 2 | Corp Info API（Python） |
| `InvoiceInfoFunctionProj/` | 2 | Invoice Info API（Python） |
| `TimestampFunctionProj/` | 2 | Timestamp API（Java） |

### module-a

| ディレクトリ | Lv | 内容 |
|:------------|:--:|:-----|
| `deploy/` | 2 | デプロイメント設定 |
| `deploy/k8s/` | 1 | Kubernetes マニフェスト |
| `prd/` | 1 | 本番環境設定 |
| `stg/` | 1 | ステージング環境設定 |
| `tst/` | 1 | テスト環境設定 |
| `mysql-init/` | 1 | DB 初期化 |
| `scripts/` | 1 | ユーティリティ |

### wpm

| ディレクトリ | Lv | 内容 |
|:------------|:--:|:-----|
| PJルート × 9 | 1 | 各PJの概要・スコープ |
| `Idemitsu/data/` | 2 | 8層データパイプライン |
| `SMTC/data/` | 2 | 5層データパイプライン |

## パイロット選定

特性の異なる3リポを選定:

| 順序 | リポ | 選定理由 | README 数 |
|:---:|:-----|:---------|:---:|
| 1 | **module-c** | 独立4プロジェクトで構造が単純。最小工数で効果検証可能 | 4 |
| 2 | **module-d** | ビジネスロジック重視。ML パイプラインのドキュメント化パターン確立 | 3 |
| 3 | **module-b** | 典型的 Web アプリ構造。最もREADME数が多く汎用パターン確立 | 7 |

残り（module-a, wpm）はパイロット完了後に展開。

## 関連

- `./document-style-guide.md` — ドキュメントスタイルガイド（命名規則・共存ルール）
- `../templates/readme-template.md` — README テンプレート（3段階成熟度）

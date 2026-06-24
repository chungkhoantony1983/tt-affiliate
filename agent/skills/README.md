# skills/

全スキルの定義を格納するディレクトリ。1スキル = 1ディレクトリ = 1 `SKILL.md`。

## 配置ルール

### skills/ 直下

- `README.md`（このファイル）のみ。スキル定義ファイルは直下に置かない

### skills/{skill-name}/ （各スキルディレクトリの規約）

- `SKILL.md` — スキル実行手順の SSoT（**必須・1ファイルのみ**）
- `references/` — スキル固有のリファレンス（**任意**。存在する場合は `references/README.md` で内容を定義）
- **スキル個別の README は不要**（本 README が全スキルの配置ルールを一元管理）
- スキル名はケバブケース（例: `ai-slides`, `test-error`）
- 上記以外のファイル・ディレクトリは配置禁止

## Tier 定義

| Tier | 実行環境 | 特徴 |
|:----:|---------|------|
| 1 | Claude Code / Codex | 全リポで使用可。platform CLI 不要 |
| 2 | platform CLI | projects/ 環境のみ。マルチモデル連携 |
| — | SSoT ルート専用 | `/sync` のみ |

## スキル一覧（27件）

### Tier 1

| スキル | 用途 |
|--------|------|
| `task/` | ロールベース作業委任 |
| `fix/` | ロールベース課題修正 |
| `spec-update/` | 仕様反映 |
| `review/` | 多角的レビュー |
| `re-review/` | 再レビュー・ディスカッション |
| `survey/` | 不具合調査 |
| `test-error/` | CIエラー調査 |
| `push/` | コミット＆プッシュ＆PR |
| `comment/` | PRコメント |
| `cleanup/` | worktree・ブランチ削除 |
| `issues/` | GitHub Issue 起票 |
| `export/` | 成果物エクスポート |
| `pj-init/` | PJフォルダ初期化 |
| `change-impact/` | 変更影響分析 |
| `pm-planning/` | PM計画策定 |
| `merge/` | PRマージ + クリーンアップ |

### Tier 2

| スキル | 用途 |
|--------|------|
| `ai-review/` | マルチモデルコードレビュー |
| `ai-slides/` | プレゼン全ライフサイクル |
| `ai-task/` | マルチモデルタスク委任 |
| `ai-fix/` | マルチモデル課題修正 |
| `ai-spec-update/` | マルチモデル仕様反映 |
| `ai-survey/` | マルチモデル不具合調査 |
| `ai-change-impact/` | マルチモデル影響分析 |
| `ai-pm-planning/` | マルチモデルPM計画 |
| `slides-export/` | スライドPDF/PPTXエクスポート |
| `ai-learn/` | フィードバック学習 |

### インフラ

| スキル | 用途 |
|--------|------|
| `sync/` | SSoT 全リポ配布 |

## スキル追加手順

1. `skills/{new-skill}/SKILL.md` を作成
2. CLAUDE.md のスキル一覧に追記
3. `/sync` で全リポに配布

## 関連

- `../CLAUDE.md` — スキル一覧・Tier定義・Step 0 共通仕様
- `../references/config/teams.yaml` — ドメイン×ワークフロー×ペルソナ定義

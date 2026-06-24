---

name: cleanup
description: マージ後のworktree・ブランチ削除とベースブランチ最新化
tier: "1"
runtime: Claude Code / Codex
---

作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（後述） |
| 3b. コンテキスト解決 | `cleanup → ops`（確定）: ドメイン ops で固定 |
| 4. ワークスペース確保 | 削除対象の特定のみ（worktree新規作成なし） |

### ステップコントローラー（IMP-071）

共通初期化プロトコル完了後、`workflow_step.py` でフェーズ順序を強制管理する。init は teams.yaml + learned-rules.yaml をプログラム的に読み込み、`config_context`（ペルソナ・制約・ルール・フェーズ担当者）を返す。各フェーズの実行時はこの config_context に従うこと。

| ステップ | コマンド | タイミング |
|---------|---------|----------|
| init | `python .claude/scripts/workflow_step.py init ops --prompt "$ARGUMENTS"` | Step 0 完了後 |
| prereq-done | `python .claude/scripts/workflow_step.py prereq-done --state {state_file}` | Step 7-8 完了後 |
| advance | `python .claude/scripts/workflow_step.py advance --state {state_file} --result {result.json}` | 各 Phase 完了時 |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

**DR_PATH パターン自動判定**（`DR配置方式` フィールド不要。`{DR_PATH}` の形式とファイルシステムを組み合わせて自動判定）: **(A) パス埋め込み型** — `{DR_PATH}` に `{PR番号}` を含む → 展開 / **(B) PJサブフォルダ型** — `{PJフォルダ}` を含む → 推論展開（不可時はユーザーに確認）/ **(C) サブフォルダ検出型** — `pr-{数字}-*` サブフォルダあり＋直置きDRなし → サブフォルダ特定 / **(C') 混在** — サブフォルダ＋直置き共存 → 両方検索、新規はサブフォルダ側 / **(D) フラット** — 上記以外 → そのまま使用

---

### Phase: requirements

### Step 1: PRマージ状態の確認

1. `gh pr view {PR番号} --json state` でPRの状態を確認
2. **MERGED でない場合**: クリーンアップを中止し、PRがマージされていないことを報告
3. **MERGED の場合**: 次のステップに進む

### Phase: implement

### Step 2: Worktree削除

**マルチリポジトリ環境:**
```bash
git -C ./{repo} worktree remove .worktrees/{branch}
```

**単一リポジトリ環境:**
```bash
git worktree remove .worktrees/{branch}
```

### Step 2.5: 一時成果物の削除

`cleanup_artifacts.py` で一時成果物を一括削除する（5点セット: worktree + ブランチ + work-log + セッション状態 + ランタイムキャッシュ）。**手動 rm ではなくスクリプトを使用すること**（リポ作業/SSoT作業の区別なく全一時成果物を確実に削除する）。

```bash
python3 "$CLAUDE_PROJECT_DIR"/.claude/scripts/cleanup_artifacts.py --worktree {worktree_path}
```

- `--worktree`: worktree パス（`.claude-session-lock` の削除に使用。worktree 削除済みの場合は省略可）
- `--dry-run`: 削除せずに対象を表示（確認用）
- スクリプトは以下を削除する:
  - `.claude/logs/work-logs/*.md`（SSoT 側 work-log — リポ/SSoT 作業の区別なし）
  - `.claude/logs/.context-locks/[0-9]*`（stale PID ファイル）
  - `.claude/logs/.worklog-locks/*`（GL-004 所有権ロック — 対応 work-log と同時削除）
  - `.claude/logs/.ssot-impact-declared`, `.workflow-active`, `.workflow-expected`
  - `.claude/logs/.placement-rules-cache`, `.agreement-hashes`
  - `{worktree_path}/.claude-session-lock`
- **削除しない**: `.hook-hash`, `.pending-feedback*.json`（クロスセッション永続ファイル）

### Step 3: ローカルブランチ削除

```bash
git -C ./{repo} branch -d {branch}
```

削除失敗時（未マージ変更あり）は警告してユーザーに確認。

### Step 4: ベースブランチ最新化

```bash
git -C ./{repo} pull
```

### Phase: review

### Step 5: 残存worktreeの確認

```bash
git -C ./{repo} worktree list
```

不要なworktreeがあれば報告し、`git worktree prune` を提案。

### Phase: report

### Step 6: 完了報告

- 削除したworktreeとブランチ
- 削除した一時成果物（work-log、コンテキストロック、キャッシュ等）
- ベースブランチの最新コミット
- 残存worktree一覧

報告は日本語で。

$ARGUMENTS

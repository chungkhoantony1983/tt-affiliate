---

name: merge
description: PRマージ + 全一時成果物の自動クリーンアップ（マージ→cleanup の原子的実行）
tier: "1"
runtime: Claude Code / Codex
---

作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（cleanup と同様） |
| 3b. コンテキスト解決 | `merge → ops`（確定）: ドメイン ops で固定 |
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

---

### Phase: requirements

### Step 1: マージ前の確認

1. `gh pr view {PR番号} --json state,mergeable,reviews,statusCheckRollup` でPRの状態を確認
2. 以下を検証する:
   - **state**: `OPEN` であること（既にマージ済みの場合は `/cleanup` を案内）
   - **mergeable**: `MERGEABLE` であること（コンフリクトがあれば報告し中止）
   - **CIステータス**: 全チェックが pass であること（失敗があれば報告し中止）
3. マージ方法をユーザーに確認する:
   - **Squash merge**（デフォルト）
   - **Merge commit**
   - **Rebase**

### Phase: implement

### Step 2: PRマージ

**重要: `gh pr merge` は GP-014 hook にブロックされるため、`gh api` を使用する。**
Step 1 で CI 確認済みのため、API 直接呼び出しで安全にマージできる。

**マージ実行:**
```bash
# Squash merge（デフォルト）
gh api repos/{owner}/{repo}/pulls/{PR番号}/merge -X PUT -f merge_method=squash

# Merge commit
gh api repos/{owner}/{repo}/pulls/{PR番号}/merge -X PUT -f merge_method=merge

# Rebase
gh api repos/{owner}/{repo}/pulls/{PR番号}/merge -X PUT -f merge_method=rebase
```

**リモートブランチ削除:**
```bash
gh api repos/{owner}/{repo}/git/refs/heads/{branch} -X DELETE
```

- マージ完了を確認: `gh pr view {PR番号} --json state` → `MERGED`

### Step 3: Worktree削除

**マルチリポジトリ環境:**
```bash
git -C ./{repo} worktree remove .worktrees/{branch}
```

**単一リポジトリ環境:**
```bash
git worktree remove .worktrees/{branch}
```

### Step 4: 一時成果物の削除

`cleanup_artifacts.py` で一時成果物を一括削除する。**手動 rm ではなくスクリプトを使用すること**（リポ作業/SSoT作業の区別なく全一時成果物を確実に削除する）。

```bash
python3 "$CLAUDE_PROJECT_DIR"/.claude/scripts/cleanup_artifacts.py --worktree {worktree_path}
```

- `--worktree`: worktree パス（`.claude-session-lock` の削除に使用。worktree 削除済みの場合は省略可）
- `--dry-run`: 削除せずに対象を表示（確認用）
- スクリプトは以下を削除する:
  - `.claude/logs/work-logs/*.md`（SSoT 側 work-log — リポ/SSoT 作業の区別なし）
  - `.claude/logs/.context-locks/[0-9]*`（stale PID ファイル）
  - `.claude/logs/.ssot-impact-declared`, `.workflow-active`, `.workflow-expected`
  - `.claude/logs/.placement-rules-cache`, `.agreement-hashes`
  - `{worktree_path}/.claude-session-lock`
- **削除しない**: `.hook-hash`, `.pending-feedback*.json`（クロスセッション永続ファイル）

### Step 5: ローカルブランチ削除

```bash
git -C ./{repo} branch -d {branch}
```

削除失敗時（未マージ変更あり）は警告してユーザーに確認。

### Step 6: ベースブランチ最新化

```bash
git -C ./{repo} pull
```

### Phase: review

### Step 7: 残存worktreeの確認

```bash
git -C ./{repo} worktree list
```

不要なworktreeがあれば報告し、`git worktree prune` を提案。

### Phase: report

### Step 8: 完了報告

- マージした PR（番号、タイトル、マージ方法）
- 削除したworktreeとブランチ
- 削除した一時成果物（work-log、コンテキストロック、キャッシュ等）
- ベースブランチの最新コミット
- 残存worktree一覧

報告は日本語で。

$ARGUMENTS

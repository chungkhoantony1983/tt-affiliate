---

name: comment
description: レビュー履歴の解説をPRにコメント
tier: "1"
runtime: Claude Code / Codex
---

作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（後述） |
| 3b. コンテキスト解決 | `comment → ops`（確定）: ドメイン ops で固定 |

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

ここまでのレビュー履歴を実装者向けに解説するPRコメントを投稿してください。
レビューで検出された課題、議論の経緯と合意事項、採用した修正方針とその根拠、残存リスクや今後の注意点をまとめること。
報告は日本語で。

### Phase: implement

#### PR review status の自動設定（コメント投稿後に必須）

コメント投稿後、レビュー指摘の状況に基づいて PR の review status を自動設定する:

| 条件 | アクション | コマンド |
|------|----------|---------|
| 未解決指摘あり（Critical/Major/Medium/Minor 問わず） | **Changes Requested** | `gh pr review {PR番号} --repo {owner/repo} --request-changes --body "..."` |
| 全指摘解決済み（収束条件達成） | **Approve** | `gh pr review {PR番号} --repo {owner/repo} --approve --body "..."` |

---

### Phase: review

PRコメントの内容がレビュー履歴を正確に反映しているか、review status の設定が適切かを確認する。

---

### Phase: report

### セッション完了報告

PRコメント投稿後、以下を報告すること：

1. **作業完了サマリ**: 本セッションで実施した作業の要約
2. **残存レビューログ確認**: `{REVIEW_LOG_PATH}` にレビューログが残っている場合、`/push` でのDR転写が未実施である可能性を警告（レビューログはコミット対象外のため、worktree削除で自動消滅する）
3. **day2 指摘の Issue 化**: レビューログに day2 / 推奨指摘が残っている場合、`/issues` でテンプレート準拠の GitHub Issue 起票を案内

---

### 自動クリーンアップ（コメント投稿後に実行）

`/comment` はコード変更を伴わないため、セッション完了報告後にworktreeとブランチを自動削除する。

1. **Worktree削除**:
   - マルチリポ: `git -C ./{repo} worktree remove .worktrees/{branch}`
   - 単一リポ: `git worktree remove .worktrees/{branch}`
2. **ローカルブランチ削除**: `git branch -d {branch}`
   - 削除失敗時（未マージ変更あり）は警告してユーザーに確認
3. **完了報告**: 削除したworktreeとブランチを報告

$ARGUMENTS

---

name: push
description: 変更をコミット＆プッシュしPRにコメント
tier: "1"
runtime: Claude Code / Codex
---

ここまでの変更をコミットとプッシュして下さい。
作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3b. コンテキスト解決 | `push → ops`（確定）: ドメイン ops で固定 |

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

### コード変更後の ai-review 確認（コミット前必須 — IMP-055）

コミット・プッシュ前に以下を確認すること:

1. **未プッシュコミットの確認**: `git log @{u}..HEAD --oneline` でプッシュ予定のコミットを確認する
2. **レビューログ存在確認**: `{REVIEW_LOG_PATH}/review-*.md` が存在する場合のみ以下を実施
3. **最終レビュー以降のコード変更検出**:
   - 最終レビューラウンドのステータスが「収束達成」または「コンセンサス達成」でも
   - 未プッシュコミットに **スペックファイル・ソースコード（ドキュメント以外）の変更が含まれる** 場合
   - → **「最終レビュー以降にコード変更があります。/ai-review を先に実施しますか？」** とユーザーに確認する
4. **例外（確認不要）**: コミット内容がドキュメント（DR/README）のみの変更、または Gemfile.lock のみの変更

> **背景（IMP-055）**: CI バグ修正等で収束後にコードが変更された場合、
> `/push` に直行してしまいレビューが漏れる事例があった（2026-03-03 PR#example 反省）。

---

### affected_ssot チェック（R-009 — コミット前必須）

DRに `affected_ssot` テーブルがある場合、列挙された全SSoTドキュメントが更新済みであることを確認する:

1. worktree内のDR（`{DR_PATH}/DR-*.md`）を検索し、`affected_ssot` セクションを探す
2. テーブル内の各行で「更新済み」が `[ ]`（未チェック）のものがあれば:
   - 該当SSoTドキュメントの更新をユーザーに促す
   - 全て更新済みになるまでコミットに進まない
3. `affected_ssot` セクションが存在しない場合はスキップ

---

### レビューログ→DR転写確認（コミット前必須）
コミット前に、レビューログを検索する。Step 0 でパス解決済みの `{REVIEW_LOG_PATH}/review-*.md` を直接検索する。

レビューログが存在する場合、以下を確認すること：
1. レビューログの主要論点が対応DRに全て記録されていること。DR作業計画テンプレート（`.claude/references/templates/dr-workplan-template.md`）の対応セクション：
   - **根本原因** → DRの「コンテキスト → 課題（根本原因）」
   - **修正方針** → DRの「決定（修正方針）」+「構造変更」
   - **検証基準** → DRの「完了基準（DoD）」→ デシジョンテーブル + E2E検証チェックリスト
2. レビューログファイルはコミットに含めないこと（DRがSSoT、レビューログはworktree内の一時的作業記録であり、worktree削除時に自動消滅する。明示的にコミットを指示された場合を除く）

### Phase: implement

PR上の前回の最終コミットの時点からの変更内容をコメントしてください: 変更の背景、今回のコミットで何を変更したか、影響範囲と具体的な変更点を、根拠とともに解説すること。
PRの本文を、今回のコミット内容までを含めた形で適切になるように、全文修正して下さい。
報告は日本語で。

---

### Phase: review

PRの本文が最新のコミット内容を正しく反映していることを確認し、PRコメントの内容が変更の背景・影響範囲・具体的変更点を網羅していることを検証する。

---

### Phase: report

### 次のアクション案内

Push完了後、以下を案内すること：

- **レビュー結果の解説が必要な場合**: `/comment` でレビュー履歴の解説をPRにコメント
- **レビューログに day2 / 推奨指摘がある場合**: `/issues` でテンプレート準拠の GitHub Issue を起票
- **worktree・ブランチの保持**: コード変更がプッシュ済みのため、worktreeとブランチはPRマージまで保持する（追加の `/fix` や `/re-review` に備える）
- **PRマージ後**: `/cleanup` でworktree・ブランチを削除し、ベースブランチを最新化

$ARGUMENTS

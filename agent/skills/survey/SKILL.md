---

name: survey
description: 不具合報告の調査・原因分析・解決策検討
tier: "1"
runtime: Claude Code / Codex
---

以下の不具合が報告されました。
作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（後述） |
| 3b. コンテキスト解決 | `survey → research`（確定）: ドメイン research で固定 |

### ステップコントローラー（IMP-071）

共通初期化プロトコル完了後、`workflow_step.py` でフェーズ順序を強制管理する。init は teams.yaml + learned-rules.yaml をプログラム的に読み込み、`config_context`（ペルソナ・制約・ルール・フェーズ担当者）を返す。各フェーズの実行時はこの config_context に従うこと。

| ステップ | コマンド | タイミング |
|---------|---------|----------|
| init | `python .claude/scripts/workflow_step.py init research --prompt "$ARGUMENTS"` | Step 0 完了後 |
| prereq-done | `python .claude/scripts/workflow_step.py prereq-done --state {state_file}` | Step 7-8 完了後 |
| advance | `python .claude/scripts/workflow_step.py advance --state {state_file} --result {result.json}` | 下記マッピングの各境界 |

**SKILL.md → teams.yaml フェーズマッピング**（advance は各グループ完了後に1回）:

| teams.yaml Phase | SKILL.md Phase（このグループ完了後に advance） |
|-----------------|----------------------------------------------|
| analyze | requirements + plan |
| propose | （なし — 調査スキルのため省略） |
| implement | implement |
| verify | report |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

**DR_PATH パターン自動判定**（`DR配置方式` フィールド不要。`{DR_PATH}` の形式とファイルシステムを組み合わせて自動判定）: **(A) パス埋め込み型** — `{DR_PATH}` に `{PR番号}` を含む → 展開 / **(B) PJサブフォルダ型** — `{PJフォルダ}` を含む → 推論展開（不可時はユーザーに確認）/ **(C) サブフォルダ検出型** — `pr-{数字}-*` サブフォルダあり＋直置きDRなし → サブフォルダ特定 / **(C') 混在** — サブフォルダ＋直置き共存 → 両方検索、新規はサブフォルダ側 / **(D) フラット** — 上記以外 → そのまま使用

---

### Phase: requirements

**学習ルールの確認**: `.claude/references/rules/learned-rules.yaml` を読み込み、Global および該当ドメイン（`research` — Step 0 b' で確定）の constraints/processes を確認する（ファイル不存在時はスキップ）。

**enforcement 分類の活用**: `hook_strict` ルールは PreToolUse hook で自動ブロックされる。`hook_fuzzy` / `prose_gate` ルールは調査時に手動で確認し、報告時に関連ルールの検証結果を明記すること。

Step 0 b' で解決されたドメインのペルソナ（`persona_refs × phase_affinity` で各フェーズに自動割当）がディスカッションして原因と解決策を検討します。

### Phase: plan

不具合報告の内容を整理し、調査計画を策定する。調査対象のコード範囲、関連する仕様書・DR、確認すべき観点を明確にする。

**並列Agent調査パターン**（大規模調査向け）: 調査対象が広範な場合（多数の制約・ファイル・データソースの網羅調査等）、独立した調査軸を特定し、Agent ツールで並列に調査を実行する。

- 調査軸を2〜3の独立したサブタスクに分割する（例: 制約充足調査 + データソース調査）
- 各 Agent に明確なスコープと期待する出力フォーマットを指定する
- Agent の結果を統合して全体像を把握する
- 単一の逐次調査より効率的で、網羅性も向上する

### Phase: implement

コード、仕様書、過去のDRを確認し、ディスカッションを通じて、課題、原因、解決策、タスクを決定してください。
報告は日本語でお願いします。

---

### Phase: report

### 次のアクション案内

調査報告後、以下を提案すること：

- **修正が必要な場合**: `/fix` で課題修正、または `/task` で作業計画を起票
- **仕様変更が必要な場合**: `/spec-update` でDR・仕様書を更新
- **追加調査が必要な場合**: 調査範囲を明確にして再度 `/survey` を実行
- **PRにコメントする場合**: `/comment` でレビュー履歴の解説を投稿
- **作業完了の場合**: PRマージ後に `/cleanup` でworktree・ブランチを削除

---

### フィードバック自動検出

スキル完了時、セッション中にユーザーが修正指示・禁止事項・再発防止・フラストレーション等の指摘を行っていた場合:

1. 指摘パターンを抽出し一覧表示（修正指示 / 禁止事項 / 再発防止 / 品質問題）
2. `improvement-backlog.yaml` に類似の改善計画がないかチェック
3. ユーザーに報告し、`/ai-learn` の実行を提案

検出なしの場合は「学習候補: なし」と報告してスキップ。

$ARGUMENTS

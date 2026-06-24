---

name: export
description: SSoT資料を提出用にエクスポート（スライドPDF / Excel）
tier: "1"
runtime: Claude Code / Codex
---

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（後述） |
| 3b. コンテキスト解決 | `export → pm-export`（確定）: ドメイン pm-export で固定 |

### ステップコントローラー（IMP-071）

共通初期化プロトコル完了後、`workflow_step.py` でフェーズ順序を強制管理する。init は teams.yaml + learned-rules.yaml をプログラム的に読み込み、`config_context`（ペルソナ・制約・ルール・フェーズ担当者）を返す。各フェーズの実行時はこの config_context に従うこと。

| ステップ | コマンド | タイミング |
|---------|---------|----------|
| init | `python .claude/scripts/workflow_step.py init pm-export --prompt "$ARGUMENTS"` | Step 0 完了後 |
| prereq-done | `python .claude/scripts/workflow_step.py prereq-done --state {state_file}` | Step 7-8 完了後 |
| advance | `python .claude/scripts/workflow_step.py advance --state {state_file} --result {result.json}` | 下記マッピングの各境界 |

**SKILL.md → teams.yaml フェーズマッピング**（advance は各グループ完了後に1回）:

| teams.yaml Phase | SKILL.md Phase（このグループ完了後に advance） |
|-----------------|----------------------------------------------|
| requirements | requirements |
| plan | plan |
| implement | implement |
| export | export |
| report | report |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

**DR_PATH パターン自動判定**（`DR配置方式` フィールド不要。`{DR_PATH}` の形式とファイルシステムを組み合わせて自動判定）: **(A) パス埋め込み型** — `{DR_PATH}` に `{PR番号}` を含む → 展開 / **(B) PJサブフォルダ型** — `{PJフォルダ}` を含む → 推論展開（不可時はユーザーに確認）/ **(C) サブフォルダ検出型** — `pr-{数字}-*` サブフォルダあり＋直置きDRなし → サブフォルダ特定 / **(C') 混在** — サブフォルダ＋直置き共存 → 両方検索、新規はサブフォルダ側 / **(D) フラット** — 上記以外 → そのまま使用

---

### Phase: requirements

このスキルの運用ルールの正本は `.claude/references/guides/export-standard.md` である。以下は実行手順の要約。詳細なルール（配置・命名・チェック要件）は正本を参照すること。

**学習ルールの確認**: `.claude/references/rules/learned-rules.yaml` を読み込み、Global および該当ドメイン（`pm-export` — Step 0 b' で確定。対象種別に応じて slides 等に変動）の constraints/processes/style_config を確認する（ファイル不存在時はスキップ）。

### Phase: plan

### 実行手順

1. 対象PJ・対象ファイル・成果物名（deliverable）・バージョンを確定
2. `.claude/references/guides/export-standard.md` §2〜3 の配置ルール・命名ルールを適用
   - 出力先: `docs/exports/{deliverable-name}/`
   - 命名規則: `{document-name}_{version}_{date}.{ext}`
3. 対象PJの `scripts/export-config.json` を確認（対象ファイル一覧が正か）
   - 全エントリに `deliverable_name`（ケバブケース）と `version` が設定されているか確認
   - 内部管理番号（IDM-001等）が `deliverable_name` / `document_name` に含まれていないか確認
   - オーケストレーターの `validate_deliverable_schema()` が起動時に自動検証する
### Phase: implement

4. 可能な限り一括コマンドを使う
   - `scripts/export_project_deliverables.py --config <PJ>/scripts/export-config.json --date <YYYY-MM-DD>`
5. **AIスライドレビュー（Stage 2 → Stage 3）**: `slide_source_files` に `mode: ai` が指定されている場合、`export-standard.md` §7 に従い Stage 2（構成最適化）→ Stage 3（はみ出しゼロ検証）を実施
   - Stage 2 はファイルごとに **Task サブエージェントに委譲**（コンテキスト溢れ防止。80行未満ならメインで直接実施可）
   - Stage 3 を通過するまでPDF化しない
6. 例外時のみ個別スクリプトを実行（`export_slides_pdf.py` / `export_csv_to_excel.py` / `export_wbs_gantt.py`）
7. 変換前に必要ツールを確認（Marp / mmdc / openpyxl 等）
### Phase: export

8. `export-standard.md` §5 のセルフチェック要件を全て検証
   - §5-1: 一般チェック（はみ出し・内部参照除去・バージョン番号等）
   - §5-2: 課題管理の関心事分離（公開区分フィルタ・課題テーブル埋め込み禁止・内部課題混入チェック）
   - §5-3: 集計サマリ要件（課題CSV→総数/Open/Closed/Critical+High集計、WBS→カテゴリ別合計）
9. 出力ファイル一覧と検証結果を日本語で報告
10. `export-standard.md` §6 のコミット要件に従い成果物をコミット（漏れ厳禁）

報告は日本語で行うこと。

---

### Phase: report

### 次のアクション案内

エクスポート完了後、以下を案内すること：

- **変更をプッシュする場合**: `/push` でコミット済みファイルをプッシュしPRを作成
- **PRマージ後**: `/cleanup` でworktree・ブランチを削除し、ベースブランチを最新化

$ARGUMENTS

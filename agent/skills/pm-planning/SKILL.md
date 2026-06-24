---

name: pm-planning
description: WBS作成・体制表・見積もり・スケジュール策定（ロールベース）
tier: "1"
runtime: Claude Code / Codex
---

Claude Code で直接実行するPM計画スキル（Tier 1）。WBS作成、体制表、見積もり、スケジュール策定を
ロールベースのワークフローで段階的に実施する。

**ドメイン**: pm-planning（`skill_mapping: pm-planning → pm-planning` で確定）
**ワークフロー**: requirements → plan → review → report

---

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3b. コンテキスト解決 | `pm-planning → pm-planning`（確定）: ドメイン pm-planning で固定 |

### ステップコントローラー（IMP-071）

共通初期化プロトコル完了後、`workflow_step.py` でフェーズ順序を強制管理する。init は teams.yaml + learned-rules.yaml をプログラム的に読み込み、`config_context`（ペルソナ・制約・ルール・フェーズ担当者）を返す。各フェーズの実行時はこの config_context に従うこと。

| ステップ | コマンド | タイミング |
|---------|---------|----------|
| init | `python .claude/scripts/workflow_step.py init pm-planning --prompt "$ARGUMENTS"` | Step 0 完了後 |
| prereq-done | `python .claude/scripts/workflow_step.py prereq-done --state {state_file}` | Step 7-8 完了後 |
| advance | `python .claude/scripts/workflow_step.py advance --state {state_file} --result {result.json}` | 下記マッピングの各境界 |

**SKILL.md → teams.yaml フェーズマッピング**（advance は各グループ完了後に1回）:

| teams.yaml Phase | SKILL.md Phase（このグループ完了後に advance） |
|-----------------|----------------------------------------------|
| analyze | requirements + plan |
| propose | （なし — 計画スキルのため省略） |
| implement | review + report |
| verify | （なし — review で兼用） |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

---

以下の作業を、ロールに基づいて段階的に実施する。
各フェーズでは、Step 0 b' で解決された pm-planning ドメインのペルソナ（`persona_refs × phase_affinity` で各フェーズに自動割当）がディスカッションして方針を決定する。
ロール定義の詳細は `.claude/references/guides/role-workflow-guide.md` を参照。

---

### Phase: requirements — 制約プリフライト・要件整理

1. **学習ルールの確認**: `.claude/references/rules/learned-rules.yaml` を読み込み、Global および pm-planning ドメインの constraints/processes を確認する（ファイル不存在時はスキップ）
2. **制約プリフライトチェック（必須出力）**: 上記1で読み込んだ制約・ルールから、今回の計画に関連するものを以下のフォーマットで**必ず出力**すること。

   | # | Rule ID | 要約 | enforcement | 今回の関連度 |
   |---|---------|------|-------------|------------|
   | 1 | GN-001  | 通貨¥のみ | hook_strict | 関連あり/N/A |

3. `$ARGUMENTS` の内容を分析し、計画対象を特定する:
   - **WBS作成**: タスク分解、依存関係、マイルストーン設定
   - **体制表**: ロール定義、担当者割当、責任分担（RACI等）
   - **見積もり**: 工数見積、コスト見積、リスクバッファ
   - **スケジュール**: ガントチャート、クリティカルパス、リソース平準化

---

### Phase: plan — 計画策定・DR起票

1. 計画方針をDRに記載する。テンプレートは `.claude/references/templates/dr-workplan-template.md` を参照
   - コンテキスト（計画の背景・目的）
   - 決定（計画方針）
   - **制約事項**: 本計画で遵守すべき制約を宣言
   - 完了基準（DoD）
2. **ユーザーにDRのレビューを依頼し、承認を得るまで次のフェーズに進まない**

> **重要**: plan フェーズ完了時点で作業を停止し、DRの内容をユーザーに提示して承認を求めて下さい。

3. 承認後、計画成果物を作成する:
   - **WBS**: タスク分解ツリー（CSV/YAML/Markdown）
   - **体制表**: ロール・担当マトリクス
   - **見積もり**: 工数・コスト見積表
   - **スケジュール**: マイルストーンとタイムライン
4. pj-config.yaml が存在する場合、不変条件の整合性を確認する
5. artifact-graph.yaml が存在する場合、成果物の依存関係を更新する
6. **横展開チェック（GP-002）**: 同一パターンが他箇所にないか確認する

---

### plan→review 制約検証ゲート（必須 — 全件 PASS まで review に進むな）

プリフライトで「関連あり」とした各制約について PASS/FAIL を報告:

| Rule ID | 検証方法 | 結果 | 根拠 |
|---------|---------|------|------|
| GN-001 | 出力確認 | PASS | 通貨は全て¥表記 |

FAIL がある場合は plan フェーズに差し戻し。

---

### Phase: review — 計画の整合性・実現可能性の確認

1. 計画成果物がDRの方針から逸脱していないか確認する
2. WBSのタスク分解が適切か（粒度、依存関係、網羅性）
3. 見積もりの根拠が妥当か（過去実績、類似PJ比較）
4. スケジュールの実現可能性（リソース制約、クリティカルパス）
5. 指摘があれば plan フェーズに戻って修正する

---

### Phase: report — 完了報告

1. DRの「実績」セクションに各フェーズの結果サマリを記録する
2. 完了基準（DoD）の全項目が充足されていることを確認する
3. ユーザーに完了報告を行う（計画内容・検証結果・残課題の有無）
4. **次のアクション案内**:
   - `/review` でレビューを依頼
   - レビュー完了後 `/push` でコミット・プッシュ・PR作成
   - `/export` で Excel/PDF にエクスポート

報告は日本語でお願いします。

---

### フィードバック自動検出

スキル完了時、セッション中にユーザーが修正指示・禁止事項・再発防止・フラストレーション等の指摘を行っていた場合:

1. 指摘パターンを抽出し一覧表示（修正指示 / 禁止事項 / 再発防止 / 品質問題）
2. `improvement-backlog.yaml` に類似の改善計画がないかチェック
3. ユーザーに報告し、`/ai-learn` の実行を提案

検出なしの場合は「学習候補: なし」と報告してスキップ。

$ARGUMENTS

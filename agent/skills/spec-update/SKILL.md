---

name: spec-update
description: ロールベース仕様反映（計画→承認→実装→レビュー→テスト→報告）
tier: "1"
runtime: Claude Code / Codex
---

作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（後述） |
| 3b. コンテキスト解決 | `spec-update → spec`（確定）: ドメイン spec で固定 |

### ステップコントローラー（IMP-071）

共通初期化プロトコル完了後、`workflow_step.py` でフェーズ順序を強制管理する。init は teams.yaml + learned-rules.yaml をプログラム的に読み込み、`config_context`（ペルソナ・制約・ルール・フェーズ担当者）を返す。各フェーズの実行時はこの config_context に従うこと。

| ステップ | コマンド | タイミング |
|---------|---------|----------|
| init | `python .claude/scripts/workflow_step.py init spec --prompt "$ARGUMENTS"` | Step 0 完了後 |
| prereq-done | `python .claude/scripts/workflow_step.py prereq-done --state {state_file}` | Step 7-8 完了後 |
| advance | `python .claude/scripts/workflow_step.py advance --state {state_file} --result {result.json}` | 下記マッピングの各境界 |

**SKILL.md → teams.yaml フェーズマッピング**（advance は各グループ完了後に1回）:

| teams.yaml Phase | SKILL.md Phase（このグループ完了後に advance） |
|-----------------|----------------------------------------------|
| analyze | requirements + architecture |
| propose | approve + plan |
| implement | implement + gate |
| verify | review + test + report |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

**DR_PATH パターン自動判定**（`DR配置方式` フィールド不要。`{DR_PATH}` の形式とファイルシステムを組み合わせて自動判定）: **(A) パス埋め込み型** — `{DR_PATH}` に `{PR番号}` を含む → 展開 / **(B) PJサブフォルダ型** — `{PJフォルダ}` を含む → 推論展開（不可時はユーザーに確認）/ **(C) サブフォルダ検出型** — `pr-{数字}-*` サブフォルダあり＋直置きDRなし → サブフォルダ特定 / **(C') 混在** — サブフォルダ＋直置き共存 → 両方検索、新規はサブフォルダ側 / **(D) フラット** — 上記以外 → そのまま使用

---
以下の作業を、ロールに基づいて段階的に実施して下さい。
各フェーズでは、Step 0 で解決されたドメインのペルソナ（`persona_refs × phase_affinity` で各フェーズに自動割当）がディスカッションして更新方針を決定します。
ロール定義の詳細は `.claude/references/guides/role-workflow-guide.md` を参照。

---

### Phase: requirements — 制約プリフライト・要件整理

1. **学習ルールの確認**: `.claude/references/rules/learned-rules.yaml` を読み込み、Global および該当ドメイン（`spec` — Step 0 b' で確定）の constraints/processes を確認する（ファイル不存在時はスキップ）
2. **制約プリフライトチェック（必須出力）**: 上記1で読み込んだ制約・ルールから、今回の仕様反映に関連するものを以下のフォーマットで**必ず出力**すること。このテーブルが出力されていない場合、以降のフェーズで PreToolUse hook がブロックする可能性がある。

   | # | Rule ID | 要約 | enforcement | 今回の関連度 |
   |---|---------|------|-------------|------------|
   | 1 | GN-001  | 通貨¥のみ | hook_strict | 関連あり/N/A |

3. DRと現在の実装を見比べて、乖離箇所を洗い出す。**既存制約への抵触がないことを確認する**

---

### Phase: architecture — 設計・構造分析

4. 変更方針の構造的影響を分析する（データ定義、システムフロー、データフロー、アクション定義への影響）

---

### Phase: approve — 2段階合意 + DR承認ゲート

**2段階合意（CLAUDE.md Phase: approve — R-003）を実行**した上で:

5. **mainにマージ済みのDRを変更する必要がある場合は、既存DRを改変せず新規DRを起票する**（`supersedes` で旧DRを参照）
6. **ユーザーにDRのレビューを依頼し、承認を得るまで次のフェーズに進まない**

> **重要**: approve フェーズ完了時点で作業を停止し、DRの内容をユーザーに提示して承認を求めて下さい。

---

### Phase: plan — 配置ルール・ログ・DR + タスク分解

**CLAUDE.md Phase: plan（R-001, R-004, R-005, R-008, R-009）を実行**した上で:

7. 変更方針をDRに記載する。テンプレートは `.claude/references/templates/dr-workplan-template.md` を参照
   - コンテキスト（乖離の原因・背景）
   - 決定（更新方針）
   - 構造変更: データ定義、システムフロー、データフロー、アクション定義の変更
   - **制約事項**: 本更新で新たに遵守すべき制約を宣言
   - デシジョンテーブル: ドキュメント変更の入力パターンごとの期待結果
   - 完了基準（DoD）

---

### Phase: implement — 承認後にDR・仕様書更新

1. 承認済みDRの方針に沿って、DRと仕様書を更新する
2. DRには特に、データ定義、システムフロー、データフロー、アクション定義などの構造、骨格の変更を記載する
3. SSoTの仕様書を変更する必要がある場合は、仕様書にも修正後仕様を反映し、仕様書の変更内容も本DRに記録する
4. **各変更完了時に実施内容と結果を報告する**

---

### implement→review 制約検証ゲート（必須 — 全件 PASS まで review に進むな）

プリフライトで「関連あり」とした各制約について PASS/FAIL を報告:

| Rule ID | 検証方法 | 結果 | 根拠 |
|---------|---------|------|------|
| GN-001 | L1 hook が検証済み | PASS | hook 通過 |
| GP-002 | grep で同一パターン全箇所確認 | PASS | N ファイル確認済み |

FAIL がある場合は implement フェーズに差し戻し。

---

### Phase: review

**目的**: 仕様変更の整合性・影響範囲の確認

1. 仕様更新がDRの計画から逸脱していないか確認する
2. 他の仕様書・DRとの整合性が保たれているか確認する
3. 構造変更（データ定義・フロー）が正確に反映されているか確認する
4. 指摘があればDRに記録し、implement フェーズに戻って修正する

---

### Phase: test

**目的**: 仕様の検証・デシジョンテーブルの確認

1. デシジョンテーブルの入力パターンと期待結果が正確か確認する
2. 仕様と実装の乖離がないか確認する
3. 完了基準（DoD）に基づいて検証し、DRに結果を記録する

---

### Phase: report

**目的**: 全工程の結果をDRに反映し、完了報告

1. DRの「実績」セクションに各フェーズの結果サマリを記録する
2. 完了基準（DoD）の全項目が充足されていることを確認する
3. ユーザーに完了報告を行う（変更内容・検証結果・残課題の有無）
4. **次のアクション案内**:
   - `/review` でレビューを依頼
   - レビュー完了後 `/push` でコミット・プッシュ・PR作成

報告は日本語でお願いします。

---

### フィードバック自動検出

スキル完了時、セッション中にユーザーが修正指示・禁止事項・再発防止・フラストレーション等の指摘を行っていた場合:

1. 指摘パターンを抽出し一覧表示（修正指示 / 禁止事項 / 再発防止 / 品質問題）
2. `improvement-backlog.yaml` に類似の改善計画がないかチェック
3. ユーザーに報告し、`/ai-learn` の実行を提案

検出なしの場合は「学習候補: なし」と報告してスキップ。

$ARGUMENTS

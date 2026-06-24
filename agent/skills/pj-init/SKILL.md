---

name: pj-init
description: PJフォルダ初期化（入力→設定生成→フォルダ構造→G0〜G1成果物）
tier: "1"
runtime: Claude Code / Codex
---

新規プロジェクトのフォルダ構造と初期成果物を自動生成するスキル。

ビジネス側が記入した入力テンプレート（Excel/CSV）または対話型入力から、
`pj-config.yaml` + `artifact-graph.yaml` + G0〜G1成果物を一括生成する。

---

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3b. コンテキスト解決 | `pj-init → project-mgmt`（確定）: ドメイン project-mgmt で固定 |

### ステップコントローラー（IMP-071）

共通初期化プロトコル完了後、`workflow_step.py` でフェーズ順序を強制管理する。init は teams.yaml + learned-rules.yaml をプログラム的に読み込み、`config_context`（ペルソナ・制約・ルール・フェーズ担当者）を返す。各フェーズの実行時はこの config_context に従うこと。

| ステップ | コマンド | タイミング |
|---------|---------|----------|
| init | `python .claude/scripts/workflow_step.py init project-mgmt --prompt "$ARGUMENTS"` | Step 0 完了後 |
| prereq-done | `python .claude/scripts/workflow_step.py prereq-done --state {state_file}` | Step 7-8 完了後 |
| advance | `python .claude/scripts/workflow_step.py advance --state {state_file} --result {result.json}` | 下記マッピングの各境界 |

**SKILL.md → teams.yaml フェーズマッピング**（advance は各グループ完了後に1回）:

| teams.yaml Phase | SKILL.md Phase（このグループ完了後に advance） |
|-----------------|----------------------------------------------|
| analyze | requirements + plan |
| propose | （なし — 初期化スキルのため省略） |
| implement | implement + report |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

---

### Phase: requirements

### Step 1: 入力収集

**3つの入力方式をサポート（`$ARGUMENTS` で判定）:**

#### 方式A: Excel/CSV テンプレート
- `$ARGUMENTS` にファイルパスが含まれる場合
- テンプレート: `.claude/references/templates/pj-templates/pj-init-input-template.csv`
- CSV/Excel を読み込み、パラメータを抽出

#### 方式B: 対話型入力
- `$ARGUMENTS` にファイルパスが含まれない場合
- 以下の情報を順に質問:
  1. **PJ略称**（英大文字3文字、例: IDM, HKD, TST）
  2. **PJ正式名称**
  3. **クライアント名**
  4. **PJタイプ**: A（フルプロダクト）/ B（既存PF導入）/ C（PoC/分析）
  5. **契約形態**: 準委任 / 請負 / SaaS
  6. **開始日・終了日**（YYYY-MM-DD）
  7. **ロール定義**（ID, 表示名, 単価）— 複数行。日額 or 月額のいずれかで入力。ユーザーに「日額と月額どちらで合意しましたか？」と確認すること
  8. **フェーズ定義**（ID, 名称, 所属ゲート）— 複数行
  9. **ゲート定義**（ID, 名称, 目標日, 期間月数）— 複数行
  10. **コンティンジェンシー率**（デフォルト: 15%）

#### 方式C: 最小入力 + デフォルト
- `$ARGUMENTS` に PJ略称のみ指定された場合
- PJタイプをユーザーに確認し、残りはPJタイプ別デフォルトを使用:
  - **Type A デフォルト**: 7ロール（PM/SA/Platform/SW Dev/ML Dev/DS/QA）、6フェーズ、5ゲート
  - **Type B デフォルト**: 5ロール（PM/SA/Platform/SW Dev/QA）、4フェーズ、3ゲート
  - **Type C デフォルト**: 3ロール（PM/DS/ML Dev）、2フェーズ、2ゲート

**出力**: `pj-config.yaml` のドラフトを生成し、ユーザーに確認を求める。

---

### Phase: plan

### Step 2: 設計確認

1. 入力から生成した `pj-config.yaml` のドラフトをユーザーに提示
2. 生成されるフォルダ構造と成果物一覧を提示
3. ユーザーの修正指示を反映
4. **承認を得てから次のステップに進む**

---

### Phase: implement

### Step 3: pj-config.yaml 生成

1. ユーザー承認済みのパラメータから `{PJフォルダ}/pj-config.yaml` を生成
2. スキーマ: `.claude/references/schemas/pj-config-schema.yaml` に準拠
3. 以下のセクションを設定:
   - `project`: PJ基本情報
   - `roles`: ロール定義（ID, 名前, unit_price and/or monthly_price）。**単価ルール**: 日額で商談した案件は `unit_price` のみ設定（`monthly_price: null`）。月額で商談した案件は `monthly_price` を設定（`unit_price` は `monthly_price ÷ business_days_per_month` で自動算出するか、`null` にして導出スクリプトに委ねる）。両方指定された場合は `monthly_price` を正本とする
   - `phases`: フェーズ定義
   - `gates`: ゲート定義（target_date, months は入力から。start_date, deadline は後で設定可能）
   - `estimate`: コンティンジェンシー率、段階定義、工程分類
   - `wbs.csv_columns`: デフォルト設定
   - `invariants`: 初期は null（導出後に設定）
   - `export`: PJタイプに応じた初期設定

---

### Step 4: フォルダ構造生成

PJタイプに応じたフォルダ構造を生成:

```
{PJ略称}/
├── 0_Project/
├── 1_Strategy/
├── 2_Scope/
├── 3_Structure/
├── 4_Skeleton/
├── 5_Surface/
├── 6_Test/
├── 7_Operations/
├── 8_Modeling/          ← Type C のみ
├── 9_Decision_Records/
├── reference/
├── docs/exports/
├── archive/
└── scripts/
```

- `.gitkeep` を各空フォルダに配置

---

### Step 5: G0成果物生成（テンプレート展開）

以下のテンプレートを展開して成果物を生成:

| 成果物 | テンプレート | 出力先 |
|---|---|---|
| PJ定義 | `pj-definition.md.j2` | `0_Project/{PJ}-001-PJ定義.md` |
| WBS | `wbs-header.csv` + ロール列動的追加 | `0_Project/{PJ}-002-WBS.csv` |
| 課題管理 | `issue-tracker.csv` | `0_Project/{PJ}-003-課題管理.csv` |
| リソース定義 | `resource-definition.md.j2` | `0_Project/{PJ}-004-リソース定義.md` |
| 見積書 | `estimate.md.j2` | `0_Project/{PJ}-005-見積書.md` |

**テンプレート変数の展開**:
- `{{ project_id }}` → PJ略称
- `{{ project_name }}` → PJ正式名称
- `{{ client }}` → クライアント名
- `{{ contract_type }}` → 契約形態
- `{{ start_date }}` / `{{ end_date }}` → PJ期間
- `{{ roles }}` → ロール定義リスト
- `{{ phases }}` → フェーズ定義リスト
- `{{ gates }}` → ゲート定義リスト
- `{{ contingency }}` → コンティンジェンシー率
- `{{ today }}` → 作成日

テンプレートファイル: `.claude/references/templates/pj-templates/`

**WBS CSV のロール列動的追加**: `wbs-header.csv` はベースカラム（14列）のみ含む。Step 5 では pj-config.yaml の `roles` セクションから以下の列を末尾に動的追加すること:
- 各ロールの `{role_id}(人日)` 列（roles の定義順）
- 末尾に `ロール人日計` 列

例（5ロールの場合）:
```
...,備考,PM(人日),SA(人日),Platform(人日),SW Dev(人日),QA(人日),ロール人日計
```

pj-config.yaml の `wbs.csv_columns.role_columns` にカスタムマッピングがある場合はそちらを優先する。空の場合は `{role_id}(人日)` を自動生成する。

**`{{ ROLE_PRICE_TABLE }}` の生成ルール**:
ロール単価テーブル（見積書・リソース定義で共用）は以下のルールで生成する:

**テーブル構造（顧客向け表記）**:
- ヘッダーは `| 役割 | 日単価（円） | 月単価（円） |` とする。「ロールID」列は含めない（内部管理用のため）
- ロール名は pj-config.yaml の `display_name`（日本語）を使用する。`display_name` がない場合は以下のデフォルトマッピングを適用: PM→プロジェクトマネージャー, SA→ソリューションアーキテクト, Platform→基盤エンジニア, SW_Dev→ソフトウェア開発者, ML_Dev→機械学習エンジニア, DS→データサイエンティスト, QA→品質保証

**単価列の算出ルール**:
- `monthly_price` が指定されている場合: 月単価は `monthly_price` をそのまま表示。日単価は `unit_price`（指定があれば）または `monthly_price ÷ business_days_per_month` を表示
- `unit_price` のみ指定されている場合: 日単価は `unit_price` をそのまま表示。月単価は `unit_price × business_days_per_month` を表示
- 月単価の表示は必ず千円未満の端数がないことを確認する。端数が出る場合は `monthly_price` を pj-config.yaml に明示設定するようユーザーに確認する

**Jinja2形式のテンプレート展開**: テンプレート内の `{{ 変数 }}` と `{% for %}...{% endfor %}` を手動で展開する。Python の Jinja2 ライブラリがなくても動作するよう、Claude Code が直接テンプレートを読み込み、変数を置換して出力ファイルを生成する。

**成果物一覧テーブル（`{{ ARTIFACTS_TABLE }}`）の顧客向け表記ルール**:
- **列構成**: `| ゲート | ドキュメントID | タイトル | カテゴリ | ステータス |` の5列とする。「形式」列（md/csv等の内部ファイル形式）は含めない
- **カテゴリ列**: フォルダ名（`0_Project` 等）ではなく日本語名（`PJ管理` 等）を使用。マッピング: 0→PJ管理, 1→戦略定義, 2→要件定義, 3→構造定義, 4→骨格定義, 5→表層定義, 6→テスト仕様, 7→運用定義, 8→モデリング, 9→変更管理
- **ステータス列**: 英語（`active`/`draft`）ではなく日本語（`確定`/`未着手`）を使用

---

### Step 6: G1成果物スケルトン生成

| 成果物 | テンプレート | 出力先 |
|---|---|---|
| ビジネス定義 | `business-definition.md.j2` | `1_Strategy/{PJ}-101-ビジネス定義.md` |
| 機能要件定義 | `functional-requirements.md.j2` | `2_Scope/{PJ}-201-機能要件定義.md` |

---

### Step 7: 運用ファイル生成

| ファイル | テンプレート/元 | 出力先 |
|---|---|---|
| 運用ルール | `operation-rules.md.j2` | `{PJフォルダ}/運用ルール.md` |
| export-config | PJタイプ別テンプレート | `{PJフォルダ}/scripts/export-config.json` |
| artifact-graph | PJタイプ別テンプレート | `{PJフォルダ}/artifact-graph.yaml` |

**artifact-graph.yaml の生成**:
- PJタイプに応じたテンプレートを使用:
  - Type A: `.claude/references/templates/artifact-graph-templates/type-a.yaml`
  - Type B: `.claude/references/templates/artifact-graph-templates/type-b.yaml`
  - Type C: `.claude/references/templates/artifact-graph-templates/type-c.yaml`
- `project_id` を PJ略称で置換
- 各ノードの `doc_id` を `{PJ略称}-{番号}` 形式で設定

---

### Step 8: 検証

1. **フォルダ構造の確認**: 全フォルダが存在すること
2. **成果物ファイルの確認**: 全ファイルが存在し空でないこと
3. **pj-config.yaml の検証**: スキーマに準拠していること
4. **artifact-graph.yaml の整合性チェック**:
   ```
   python .claude/scripts/validate_artifact_graph.py {PJフォルダパス}
   ```
5. エラーがあれば修正して再検証

---

### Phase: report

### Step 9: 報告

ユーザーに以下を報告:

1. **生成されたフォルダ構造**（ツリー表示）
2. **生成された成果物一覧**（ファイルパス + ステータス）
3. **pj-config.yaml の概要**（PJ基本情報、ロール数、フェーズ数、ゲート数）
4. **artifact-graph.yaml の概要**（ノード数、エッジ数）
5. **検証結果**

**次のアクション案内**:
- WBS CSV にタスクを記入して導出パイプラインを実行:
  - `python .claude/scripts/derive_wbs_role_days.py {PJフォルダパス}` でロール人日配分（prior_weights × budget_role_days キャリブレーション）
  - `python .claude/scripts/derive_wbs_schedule.py {PJフォルダパス}` で日程計算
  - `python .claude/scripts/derive_resources.py {PJフォルダパス}` でリソース定義の費用テーブル導出
  - `python .claude/scripts/derive_estimate.py {PJフォルダパス}` で見積書の金額テーブル導出
  - `python .claude/scripts/derive_fte.py {PJフォルダパス}` でFTE計画導出
- `/push` でコミット・プッシュ・PR作成

報告は日本語でお願いします。

$ARGUMENTS

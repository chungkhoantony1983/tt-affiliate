---

name: change-impact
description: 前提条件変更の影響分析（依存グラフBFS走査→DR起票→成果物更新→変更管理記録）
tier: "1"
runtime: Claude Code / Codex
---

前提条件が変更された際に、artifact-graph.yaml の依存グラフを走査して
影響先を機械的に特定し、成果物を更新するスキル。

---

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3b. コンテキスト解決 | `change-impact → project-mgmt`（確定）: ドメイン project-mgmt で固定 |

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
| propose | approve（DR起票・承認） |
| implement | implement + report |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

---

### Phase: requirements

### Step 1: 変更内容の特定

#### 1. artifact-graph.yaml の読み込み
- `{PJフォルダ}/artifact-graph.yaml` を読み込む
- ファイルが存在しない場合はエラーメッセージを表示して終了

#### 2. 変更カテゴリの選択
`$ARGUMENTS` に変更内容が含まれていない場合、ユーザーに以下から選択を求める:

| カテゴリ | 説明 | 起点ノード |
|---|---|---|
| **スコープ変更** | 機能追加/削除/変更 | 機能要件定義 |
| **スケジュール変更** | マイルストーン変更、期間変更 | WBS |
| **SLA変更** | SLA条件変更、性能要件変更 | 非機能要件 |
| **コスト変更** | 単価変更、体制変更 | リソース定義 |
| **体制変更** | ロール追加/削除、人員変更 | FTE計画 |
| **モデル/分析変更** | 分析手法変更、モデル変更 | 分析レポート |
| **カスタム** | 上記に該当しない場合 | ユーザー指定 |

#### 3. 変更詳細の収集
- 変更の具体的な内容を確認
- 変更の起因（課題番号、ステークホルダー要望、等）
- 変更の影響範囲の初期推定

---

### Phase: plan

### Step 2: 影響分析（BFS走査）

#### 1. 起点ノードの特定
- 選択されたカテゴリの `entry_points` から起点ノードを取得
- カスタムの場合はユーザーが指定したノードIDを使用

#### 2. BFS（幅優先探索）で依存方向に走査
```
起点ノード → derives/references/constrains → 影響先ノード → ...
```

走査ルール:
- `derives`: 最も強い依存。必ず走査を続行
- `references`: 確認が必要。走査を続行
- `constrains`: 制約チェック用。走査を続行するが対応は確認レベル

#### 3. 影響先リストの生成
各影響先について以下を記録:
- **深さ**: 起点からの距離（BFS階層）
- **成果物**: ノードID + タイトル
- **影響種別**: derives / references / constrains
- **対応**: 手動更新 / 自動導出（`derived_by` が設定されている場合）
- **ステータス**: active / draft / archived

---

### Step 3: 影響レポート表示

以下のフォーマットで影響レポートを表示:

```markdown
## 変更影響分析レポート

### 変更内容
- カテゴリ: {選択したカテゴリ}
- 内容: {変更の詳細}
- 起因: {課題番号等}

### 影響先一覧（深さ順）
| # | 深さ | 成果物 | doc_id | 影響種別 | 対応 | 現在のステータス |
|---|------|--------|--------|---------|------|----------------|
| 1 | 0 | 機能要件定義 | {PJ}-201 | derives | 手動 | active |
| 2 | 1 | WBS | {PJ}-002 | derives | 手動 | active |
| 3 | 2 | リソース定義 | {PJ}-004 | derives | 自動(derive_resources) | active |
| 4 | 2 | 見積書 | {PJ}-005 | derives | 自動(derive_estimate) | active |
| ... | | | | | | |

### 自動導出可能な成果物
- {PJ}-004 リソース定義 → `python .claude/scripts/derive_resources.py {PJフォルダ}`
- {PJ}-005 見積書 → `python .claude/scripts/derive_estimate.py {PJフォルダ}`

### 手動更新が必要な成果物
- {PJ}-201 機能要件定義
- {PJ}-002 WBS
```

---

### Phase: implement

### Step 4: DR起票 → ユーザー承認

1. **制約プリフライトチェック（必須出力）**:

   | # | Rule ID | 要約 | enforcement | 今回の関連度 |
   |---|---------|------|-------------|------------|
   | 1 | GN-001  | 通貨¥のみ | hook_strict | 関連あり/N/A |

2. **DR（作業計画型）を起票**: テンプレートは `.claude/references/templates/dr-workplan-template.md`
   - **コンテキスト**: 変更内容、起因、影響分析結果
   - **決定事項**: 変更を受け入れるか、代替案はあるか
   - **構造変更**: 影響先の変更内容
   - **作業計画**: 影響レポートの影響先テーブルを展開
     - 深さ0（直接変更）→ 深さ1 → 深さ2（自動導出）の順に作業
   - **リスク・前提条件**
   - **完了基準（DoD）**: 全影響先が更新済み + 不変条件検証PASS

3. **ユーザーにDRのレビューを依頼し、承認を得るまで次のフェーズに進まない**

> **重要**: Step 4 完了時点で作業を停止し、DRの内容をユーザーに提示して承認を求めて下さい。

---

### Step 5: 成果物更新

DRの作業計画に従い、影響先を深さ順に更新する。

#### 手動更新（depth 0, 1）
- ユーザーと対話しながら成果物を更新
- 変更内容をDRの「実績」セクションに記録

#### 自動導出（depth 2+、`derived_by` あり）
- 手動更新が完了した後、自動導出スクリプトを実行:
  ```bash
  python .claude/scripts/{derived_by}.py {PJフォルダパス}
  ```
- 導出結果をユーザーに確認してもらう
- 不変条件の検証結果を報告

#### 横展開チェック（GP-002 / RV-006）
- 各変更について、同一パターンが他箇所にないか確認
- 横展開完了を確認してから次のタスクに進む

---

### Step 6: 変更管理記録

#### 1. 課題管理CSV の更新
- 変更に関連する課題がある場合、課題管理CSV（`{PJ}-003-課題管理.csv`）の「反映先ドキュメント」列を更新
- 反映先は doc_id で正規化して記載（バージョン番号は含めない）
- 例: `IDM-201, IDM-002, IDM-004, IDM-005`

#### 2. バージョン番号の更新
- 更新した成果物の artifact-graph.yaml 内の `version` を更新:
  - 軽微な変更: パッチ（0.1.0 → 0.1.1）
  - 内容追加: マイナー（0.1.0 → 0.2.0）
  - 大幅変更: メジャー（0.1.0 → 1.0.0）

#### 3. artifact-graph.yaml の整合性チェック
```bash
python .claude/scripts/validate_artifact_graph.py {PJフォルダパス}
```

---

### Step 7: 検証

#### Phase 2→3 制約検証ゲート

プリフライトで「関連あり」とした各制約について PASS/FAIL を報告:

| Rule ID | 検証方法 | 結果 | 根拠 |
|---------|---------|------|------|
| GN-001 | 出力確認 | PASS | 通貨は全て¥表記 |
| GP-002 | grep 確認 | PASS | 同一パターン全箇所確認済み |

#### 不変条件検証
- pj-config.yaml の invariants が設定されている場合:
  ```bash
  python .claude/scripts/derive_resources.py {PJフォルダパス}
  ```
  の不変条件検証結果を確認

#### artifact-graph 整合性
- `validate_artifact_graph.py` の結果を確認

---

### Phase: report

### Step 8: 報告

ユーザーに以下を報告:

1. **変更サマリ**
   - 変更カテゴリ、変更内容
   - 影響先の数（手動/自動）

2. **更新済み成果物一覧**
   | # | 成果物 | 更新方法 | バージョン変更 |
   |---|--------|---------|-------------|
   | 1 | 機能要件定義 | 手動 | 0.2.0 → 0.3.0 |
   | 2 | WBS | 手動 | 0.1.0 → 0.2.0 |
   | 3 | リソース定義 | 自動導出 | 0.1.0 → 0.2.0 |

3. **検証結果**
   - 制約検証: PASS/FAIL
   - 不変条件: PASS/FAIL/SKIP
   - artifact-graph整合性: OK/NG

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

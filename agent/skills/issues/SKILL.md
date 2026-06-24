---

name: issues
description: レビュー指摘・DR・ユーザー指示から GitHub Issue を起票（テンプレート準拠・対話的確認）
tier: "1"
runtime: Claude Code / Codex
---

作業やコンテキストが大きくなることによって精度が落ちないように、作業を分解して、適切な順番で実行して下さい。

### Step 0: 初期化

CLAUDE.md 共通初期化プロトコル（1-8）を実行。以下のカスタマイズを適用:

| ステップ | カスタマイズ |
|---------|------------|
| 3a. PJ固有設定 | DR_PATH パターン自動判定を適用（後述） |
| 3b. コンテキスト解決 | `issues → project-mgmt`（確定）: ドメイン project-mgmt で固定 |

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
| propose | （なし — Issue起票スキルのため省略） |
| implement | implement + report |

- `{state_file}`: init の出力 `state_file` キーから取得。セッション終了時に削除（C-IMP071-4）
- `{result.json}`: Phase の成果サマリ（`{"summary": "..."}` 最低限）。空結果はエラー
- advance の返却値に `work_log_update` があれば work-log に反映する

**DR_PATH パターン自動判定**（`DR配置方式` フィールド不要。`{DR_PATH}` の形式とファイルシステムを組み合わせて自動判定）: **(A) パス埋め込み型** — `{DR_PATH}` に `{PR番号}` を含む → 展開 / **(B) PJサブフォルダ型** — `{PJフォルダ}` を含む → 推論展開（不可時はユーザーに確認）/ **(C) サブフォルダ検出型** — `pr-{数字}-*` サブフォルダあり＋直置きDRなし → サブフォルダ特定 / **(C') 混在** — サブフォルダ＋直置き共存 → 両方検索、新規はサブフォルダ側 / **(D) フラット** — 上記以外 → そのまま使用

---

### Phase: requirements

### Step 1: ソース特定 + Issue 候補抽出

`$ARGUMENTS` と現在のコンテキストから Issue のソースを特定する。

#### ソース判定

| ソース | 判定条件 | 抽出方法 |
|--------|---------|---------|
| レビューログ | `{REVIEW_LOG_PATH}` に未処理ログが存在 | day2 / 推奨タグの指摘を抽出 |
| ユーザー指示 | `$ARGUMENTS` に明示的な内容 | そのまま使用 |
| DR | DR に制約事項 / TODO がある | 制約一覧から未対応を抽出 |

#### 出力

Issue 候補一覧をユーザーに提示する:

```
Issue 候補:
1. [Tech Debt] Dockerfile の design-system ビルドブロック重複を統合 (F-001)
2. [Enhancement] design-system: sizes 型統一 (CC-001)
3. [Task] design-system: README に使い分けガイド追加 (CC-002)

上記の Issue を作成しますか？追加・削除・変更があれば指示してください。
```

ユーザー承認後に Step 2 に進む。

---

### Phase: plan

### Step 2: テンプレート読み込み + フィールド充填

#### 2a. テンプレート一覧取得

`{repo}/.github/ISSUE_TEMPLATE/` のテンプレート YML ファイルを全件読み込む。各テンプレートの:
- `name`: テンプレート名
- `type`: Issue Type（Bug / Feature / Enhancement / Tech Debt / Task）
- `body[].id`: フィールド ID
- `body[].attributes.label`: フィールド表示名
- `body[].attributes.options`: 選択肢（dropdown の場合）
- `body[].validations.required`: 必須フラグ

#### 2b. テンプレート自動選定

各 Issue 候補に最適なテンプレートを割り当てる。**マッピングは参考値**。Step 2a で読み込んだ実際のテンプレート一覧から、`name` / `description` を参照して最適なものを選定する:

| レビュー指摘カテゴリ | テンプレート（参考） | type |
|---------------------|------------|------|
| structure, idiom, duplication | tech-debt.yml | Tech Debt |
| type-safety, docs, style, improvement | enhancement.yml | Enhancement |
| test, documentation task | task.yml | Task |
| bug, regression, data loss | bug.yml | Bug |
| feature proposal, new capability | feature.yml | Feature |

**フォールバック**: 上記に該当しない場合、Step 2a で取得したテンプレート一覧から最も適切なものを選び、AskUserQuestion で確認する。テンプレートが追加・名称変更されても、YML を毎回読み込むため自動追従する。

#### 2c. フィールド自動充填

テンプレートの全フィールドを走査し、可能な限り自動充填する:

| フィールド | 自動充填ソース | 確信度 |
|-----------|--------------|--------|
| Product | PR のラベル (`product:*`) or PR 対象モジュールから推定 | 中〜高 |
| Priority | day2 → P3、修正必須 → P2、blocking → P1 | 高 |
| Client | PR のラベル (`client:*`) or `(internal)` | 高 |
| Description / Current Problem | レビュー指摘文から生成 | 高 |
| Impact | レビュー指摘の重大度・影響範囲から生成 | 中 |
| Definition of Done / Acceptance Criteria | レビュー指摘の推奨アクションから生成 | 中 |
| Proposed Approach / Scope | レビュー指摘の提案から生成 | 中 |

**確信度「中」以下のフィールド**: Step 3 で対話的に確認する。

---

### Step 3: 対話的確認（AskUserQuestion）

**Issue ごとに、テンプレートの全フィールドを順に確認する。**

#### 共通フィールド（初回のみ確認、以降は引き継ぎ）

全 Issue で共通のフィールドは最初の Issue でのみ確認し、残りの Issue に引き継ぐ:

```
Q1: [Product] この Issue 群のプロダクトは？
    → Platform (推奨) / Analytics / Smart Assistant / Cash Manager / Payment / Link

Q2: [Client] クライアント起因？
    → (internal) (推奨) / Kyoto Bank / Hokkaido Bank / ...

Q3: [Milestone] Milestone に紐付ける？
    → {PR の Milestone} (推奨) / なし / {他の Milestone}

Q4: [Parent Issue] 親 Issue はある？（Sub-issues として紐付ける場合）
    → なし (推奨) / #{issue_number} を指定
```

#### Issue 個別フィールド

各 Issue について、テンプレート固有の必須フィールドを確認:

```
--- Issue 1: Dockerfile の design-system ビルドブロック重複を統合 ---

Q: [テンプレート] Tech Debt で作成しますか？
   → Tech Debt (推奨) / Enhancement / Task

Q: [Priority] 優先度は？
   → P3 (推奨 — day2) / P2 / P1

Q: [Size] 見積もりサイズは？
   → S (推奨) / XS / M / L

Q: [Description] 以下の内容でよいですか？（編集可能）
   > PR #6806 のレビュー (F-001) で検出。7つの Dockerfile に...

Q: [Impact] 以下の内容でよいですか？（編集可能）
   > Dockerfile を変更するたびに7ファイルの同期が必要。変更漏れによる...
```

**AskUserQuestion の制約**: 1回の呼び出しで最大4問。フィールド数が多い場合は複数回に分けて確認する。
**確信度「高」のフィールド**: 推奨値を明示し、ユーザーが「Other」で上書きしない限りそのまま使用。

---

### Phase: implement

### Step 4: Issue 作成

#### 4a. body フォーマット

**テンプレート形式の body を生成する**（`issue-labeler.yml` 互換）。
GitHub がフォームテンプレートから生成する Markdown と同一形式:

```markdown
### Product

Platform

### Priority

P3

### Client (if applicable)

(internal)

### Description

PR #6806 のレビュー (F-001) で検出。...

### Impact

Dockerfile を変更するたびに...

### Proposed Approach

Docker multi-stage build で...
```

**フォーマットルール**:
- dropdown フィールド: `### {label}\n\n{selected_option}` — 選択肢のテキストをそのまま記載
- textarea フィールド: `### {label}\n\n{content}` — 複数行可
- フィールド順: テンプレート YML の定義順に従う
- 全フィールド（required + optional）を body に含める。未入力の optional は `### {label}\n\n_No response_`

#### 4b. Issue 作成コマンド

```bash
gh issue create \
  --title "{タイトル}" \
  --body "$(cat <<'EOF'
{Step 4a で生成した body}
EOF
)" \
  --milestone "{Milestone名}" \
  --label "{product:xxx},{priority:Px}"
```

- `--label`: `issue-labeler.yml` が body パースで付与するが、念のため明示的にも設定（冪等）
- `--milestone`: Step 3 で確認した Milestone を設定
- **ラベル値の導出**: テンプレートの dropdown 選択値からラベル名に変換（例: "Analytics" → `product:analytics`、"P3" → `priority:P3`）

#### 4c. 親子関係の設定（Sub-issues）

Step 3 で親 Issue が指定された場合、または複数の Issue が同一機能の分割である場合:

```bash
# 子 Issue を親 Issue の Sub-issue として追加
gh issue develop {child_issue_number} --issue-repo org/{repo}
# または GitHub API で Sub-issue 追加
gh api graphql -f query='
  mutation {
    addSubIssue(input: {
      issueId: "{parent_issue_node_id}"
      subIssueId: "{child_issue_node_id}"
    }) { issue { id } }
  }
'
```

**親 Issue の Node ID 取得**:
```bash
gh api graphql -f query='
  query {
    repository(owner: "org", name: "{repo}") {
      issue(number: {parent_number}) { id }
    }
  }
' --jq '.data.repository.issue.id'
```

#### 4d. Project Board フィールド設定

Issue 作成後、`project-sync.yml` が Project Board に自動追加する。
追加完了後（数秒待機）、Priority と Size を GraphQL で設定する。

**ID はハードコードしない。毎回 GraphQL でフィールド名から動的に解決する。**

```bash
# 0. Organization の Project を番号で取得（Project ID を動的解決）
PROJECT_ID=$(gh api graphql -f query='
  query {
    organization(login: "org") {
      projectV2(number: 36) { id }
    }
  }
' --jq '.data.organization.projectV2.id')

# 1. Issue の Project Item ID を取得
ITEM_ID=$(gh api graphql -f query='
  query {
    repository(owner: "org", name: "{repo}") {
      issue(number: {issue_number}) {
        projectItems(first: 5) {
          nodes { id project { number } }
        }
      }
    }
  }
' --jq '[.data.repository.issue.projectItems.nodes[] | select(.project.number == 36)][0].id')

# 2. フィールド一覧を取得し、名前で Priority / Size のフィールド ID + Option ID を解決
FIELDS_JSON=$(gh api graphql -f query='
  query($pid: ID!) {
    node(id: $pid) {
      ... on ProjectV2 {
        fields(first: 30) {
          nodes {
            ... on ProjectV2SingleSelectField {
              id name
              options { id name }
            }
          }
        }
      }
    }
  }
' -f pid="$PROJECT_ID")

# Python で名前→ID を解決（jq でも可）
python3 -c "
import json, sys
fields = json.loads('''$FIELDS_JSON''')
for node in fields['data']['node']['fields']['nodes']:
    if node.get('name') == 'Priority':
        print(f\"PRIORITY_FIELD={node['id']}\")
        for opt in node['options']:
            print(f\"PRIORITY_{opt['name']}={opt['id']}\")
    elif node.get('name') == 'Size':
        print(f\"SIZE_FIELD={node['id']}\")
        for opt in node['options']:
            print(f\"SIZE_{opt['name']}={opt['id']}\")
"
# → 出力例: PRIORITY_FIELD=PVTSSF_..., PRIORITY_P3=c73ff9c1, SIZE_S=142d3374

# 3. Priority を設定（eval で変数展開）
gh api graphql -f query='
  mutation {
    updateProjectV2ItemFieldValue(input: {
      projectId: "'$PROJECT_ID'"
      itemId: "'$ITEM_ID'"
      fieldId: "'$PRIORITY_FIELD'"
      value: { singleSelectOptionId: "'$PRIORITY_{selected_priority}'" }
    }) { projectV2Item { id } }
  }
'

# 4. Size を設定
gh api graphql -f query='
  mutation {
    updateProjectV2ItemFieldValue(input: {
      projectId: "'$PROJECT_ID'"
      itemId: "'$ITEM_ID'"
      fieldId: "'$SIZE_FIELD'"
      value: { singleSelectOptionId: "'$SIZE_{selected_size}'" }
    }) { projectV2Item { id } }
  }
'
```

**動的解決のポイント**:
- Project 番号 (`36`) のみ固定。Project ID・フィールド ID・Option ID は全て名前から動的解決
- フィールドや選択肢が追加・変更されても、名前が一致すれば自動追従
- Project Board を再作成しても番号が変わらなければ動作する

---

### Phase: report

### Step 5: 報告（必須）

各 Issue について **全フィールド内容** を報告する。URL だけでは不十分。

```
## 作成した Issue

### #{number} — {タイトル}
- **URL**: {url}
- **テンプレート**: {template_name}
- **Product**: {product} | **Priority**: {priority} | **Size**: {size}
- **Milestone**: {milestone}
- **親 Issue**: #{parent} (Sub-issue として追加済み) ← 親子関係がある場合
- **refs**: #{PR番号}
- **Project**: Project Board — 自動追加済み、Priority/Size 設定済み

#### フィールド内容
| フィールド | 内容 |
|-----------|------|
| Description | {全文} |
| Impact | {全文} |
| Proposed Approach | {全文} |
| Definition of Done | {全文} |
```

---

### フィードバック自動検出

スキル完了時、セッション中にユーザーが修正指示・禁止事項・再発防止・フラストレーション等の指摘を行っていた場合:

1. 指摘パターンを抽出し一覧表示（修正指示 / 禁止事項 / 再発防止 / 品質問題）
2. `improvement-backlog.yaml` に類似の改善計画がないかチェック
3. ユーザーに報告し、`/ai-learn` の実行を提案

検出なしの場合は「学習候補: なし」と報告してスキップ。

$ARGUMENTS

# ペルソナベースワークフローガイド（v2.0）

## 目的

- 各スキルのワークフローで使用するペルソナの責務と承認フローを定義する
- `teams.yaml` の `personas` レジストリ・`persona_refs`・`phase_affinity` による自動導出モデルを説明する

## ペルソナ統一モデル（v2.0）

v2.0 では旧4ロール（Planner/Implementer/Reviewer/Tester）をペルソナとして統一した。全15名のペルソナが `teams.yaml` の `personas` レジストリに定義されている。

### 開発系ペルソナ（旧4ロール）

| ペルソナ | phase_affinity | 責務 | 主な成果物 |
|----------|---------------|------|-----------|
| **dev-planner**（設計者） | resolve, plan, report, export | 仕様理解、タスク分解、リスク洗い出し、DR起票、完了報告 | DR（作業計画型） |
| **dev-implementer**（実装者） | implement, execute | 計画に沿った変更の実施、構造変更の記録 | コード・ドキュメントの変更 |
| **dev-reviewer**（レビュアー） | review, verify | 設計逸脱・リスク・境界条件・保守性の確認 | レビュー指摘・DRへの記録 |
| **dev-tester**（テスター） | test | テスト設計、失敗ケース想定、検証実行 | テスト結果・E2E検証チェックリスト |

### アクター自動導出

各フェーズの担当ペルソナは `resolve_actors(domain, phase)` で自動導出される:

```
resolve_actors(domain, phase) = domain.persona_refs ∩ {p | phase ∈ p.phase_affinity}
```

例（fix ドメイン）:
- resolve → dev-planner
- plan → dev-planner
- approve → (ユーザー承認 — AI アクターなし)
- implement → dev-implementer
- review → dev-reviewer
- test → dev-tester
- report → dev-planner

### ドメイン別ペルソナ構成

| ドメイン | persona_refs | ワークフロー |
|---------|-------------|------------|
| fix, spec | dev-planner, dev-implementer, dev-reviewer, dev-tester | resolve→plan→approve→implement→review→test→report |
| code-review | bank-cto, sre, automation-cto, sa, ux, domain-expert, security（7名） | resolve→scan→lateral→discuss→report |
| research | dev-planner, researcher | resolve→search→analyze→report |
| slides | slides-planner, slides-designer, slides-artist | resolve→plan→design→generate→qa→export→report |
| pm-planning | dev-planner, dev-reviewer | resolve→plan→review→report |
| ops | dev-planner, dev-implementer, dev-reviewer | resolve→verify→execute→report |

全ペルソナの完全な定義（name, perspective, expertise, phase_affinity, domains）は `teams.yaml` の `personas` セクションを参照。

## 承認フロー

```
dev-planner（resolve → plan フェーズ）
  │
  ├── 0. ★ CONSTRAINTS.md を最初に読む（既存制約の把握）
  ├── 1. 依頼内容を分析（既存制約への抵触確認）
  │     ├── API定義（OpenAPI等）がある場合、テーブル定義との型整合性も確認
  │     └── ★ 要確認事項はスコープ外にしない（調査してからスコープを確定する）
  ├── 2. タスク分解・リスク洗い出し
  ├── 3. DR起票（作業計画型テンプレート使用）
  │     ├── コンテキスト（根本原因）
  │     ├── 決定（修正方針）
  │     ├── 構造変更（データ定義・フロー）
  │     ├── ★ 制約事項（新規制約の宣言 / supersedes）
  │     ├── デシジョンテーブル（期待結果の事前定義）
  │     └── 完了基準（DoD）
  │
  │  ※ マージ済みDRの改変が必要な場合:
  │     既存DRは改変せず、新規DRを起票（supersedes参照）
  │
  └── 4. ★ ユーザーにDRレビュー依頼 → 承認待ち（approve フェーズ）
              │
              ▼ 承認
dev-implementer（implement フェーズ）
  │
  ├── 5. DRの作業計画に沿って実装
  ├── 6. 構造変更をDRに記録
  └── 7. 各タスク完了時に報告
              │
              ▼
dev-reviewer（review フェーズ）
  │
  ├── 8. 設計逸脱・リスク確認
  ├── 9. ★ CONSTRAINTS.md との整合性確認
  ├── 10. 横展開チェック
  └── 11. 指摘があればDR記録 → dev-implementer に差し戻し
              │
              ▼
dev-tester（test フェーズ）
  │
  ├── 12. デシジョンテーブルに基づくテスト実行
  │       ★ AI生成テストコードの品質検証（必須）:
  │       (a) テスト対象クラスの初期化シグネチャを Read で確認
  │       (b) 同一specファイル内の既存テストパターンと照合
  │       (c) ランタイム実行（rspec/pytest/npm test等）で検証
  │           静的確認のみでの「品質良好」判定は禁止
  ├── 13. E2E検証チェックリストの検証
  └── 14. 失敗があれば dev-implementer に差し戻し
              │
              ▼
dev-planner（report フェーズ）
  │
  ├── 15. DRの実績セクションを更新
  └── 16. ユーザーに完了報告

              │  （ /push 時）
              ▼
★ 制約転記
  ├── DRの「制約事項」→ CONSTRAINTS.md に追記
  └── superseded制約 → 「解除済み」に移動
```

## 合意形成プロトコル（全レビュープロセス必須）

> **根本原因**: 単一モデルの独断レビューでは観点漏れ・表記揺れ・論理矛盾を検出できない。
> 複数視点の相互批評を収束するまで繰り返すことで、レビュー品質を担保する。
> **これがなければゼロベースレビューを繰り返す意味がない**（同一モデルの同一盲点が残存する）。

### 適用対象

| プロセス | スコープ |
|---------|---------|
| `/review`, `/re-review` | スキル全体 |
| `/task`, `/fix`, `/spec-update` Phase 3 (Reviewer) | ワークフロー内のレビューフェーズ |
| `/ai-review` Step 3 | マルチモデルコンセンサス |

### プロトコル（4フェーズ）

```
Phase 1: 独立分析（並列）
├── エージェントA: 観点①（構造・整合性）
├── エージェントB: 観点②（表記・用語統一）
└── エージェントC: 観点③（業務正確性・コード一致）
    ※ 3エージェントは互いの出力を参照しない

Phase 2: 相互レビュー（並列）
├── A の出力 → B, C がレビュー（観点漏れ・誤りを指摘）
├── B の出力 → A, C がレビュー
└── C の出力 → A, B がレビュー

Phase 3: 反論解決（繰り返し）
├── 不一致点を抽出
├── 各エージェントに反論/補足を求める
└── 反論が出なくなるまで繰り返し

Phase 4: 収束判定
├── 全エージェントの指摘が完全一致 → 合意成立
└── 不一致が残存 → Phase 2 に戻る
```

### Tier 別の実装方法

| Tier | 3モデル構成 | 方法 |
|------|-----------|------|
| Tier 2（`/ai-review`） | GPT + Gemini + Claude Code | platform CLI で2モデルAPI実行 → Claude Code が3番目として直接参加 |
| Tier 1（`/review`, `/re-review`, Phase 3） | Claude Task × 3（異なる観点） | 3並列 Task エージェント → 出力交換 → 再レビュー Task → 収束まで繰り返し |

### 禁止事項

- 単一エージェントのレビュー結果を無条件で採用しない
- 最初のラウンドで「PASS」判定を出さない（最低1回の相互レビューを経ること）
- 収束前に作業を完了としない

## レビュー収束基準

| ルール | 内容 | スコープ |
|--------|------|---------|
| **3連続全軸Pass** | 0ベースレビューの収束基準は最低3連続全軸Pass。2連続では不十分 | `/ai-review` のみ（マルチモデル） |
| **0ベース必須** | 修正後は必ず前回結果非参照で全体再検証。変更セット全体（全変更ファイル全文）が対象。狭域レビュー禁止 | 全環境共通 |
| **非単調性前提** | 指摘件数の増減は正常。減少トレンドを収束の根拠にしない | `/ai-review` のみ（マルチモデル） |
| **技術的整合性** | 最終収束軸として最後まで0ベースレビューを省略しない | `/ai-review` のみ（マルチモデル） |
| **横展開必須** | 防御的チェック追加時は同一パターン全箇所に横展開してからコミット | 全環境共通 |

## テスト駆動アプローチ

Phase 1（Planning）で**実装前に期待結果を定義**する。これはコード変更だけでなくドキュメント変更にも適用する。

### コード変更

デシジョンテーブルに入力パターン（正常系・異常系・境界値・既存機能への影響）ごとの期待結果を記載。Phase 4でこのテーブルに基づいて検証する。

### ドキュメント変更

ドキュメントのデシジョンテーブルに変更対象・変更パターン・変更後の期待状態を記載。Phase 3のレビューで整合性を確認する。

## DR不変ルールと制約管理

### DR不変ルール

- **mainにマージされたDRは改変不可**（内容の修正・追記・削除すべて禁止）
- 既存DRの対象範囲を変更する場合は、**新規DRを起票**し `supersedes` で旧DRを参照する
- これにより、過去の意思決定が改ざんされるリスクを排除する

### 制約管理（CONSTRAINTS.md）

各PJの `{CONSTRAINTS_PATH}`（デフォルト: `{DR_PATH}/CONSTRAINTS.md`）で現在有効な制約を一元管理する。

**制約の宣言（事前宣言方式）**:
- DR起票時（plan フェーズ）に、dev-planner が「制約事項」セクションで制約を宣言する
- **リトマステスト**: 「これに反する変更が将来行われたら、バグ/リグレッションか？」→ Yes なら制約
- ユーザーがDRを承認する際に、制約の妥当性も承認される

**制約の転記（/push時）**:
- DRの「制約事項」に記載があれば、CONSTRAINTS.mdの適切なカテゴリに追記
- `supersedes` があれば、旧制約を「解除済み」に移動
- テンプレートは `.claude/references/constraints-template.md` を参照

**制約の参照（Phase 1 開始時）**:
- `/task`, `/fix`, `/spec-update` のPhase 1で、CONSTRAINTS.mdを最初に読む
- 既存制約に抵触する変更がある場合は、明示的に `supersedes` で解除する新規DRが必要

## スキル別の適用範囲（v2.0 ワークフロー）

| スキル | plan | implement | review | test | report |
|--------|------|-----------|--------|------|--------|
| `/task`, `/fix` | ✅ dev-planner | ✅ dev-implementer | ✅ dev-reviewer | ✅ dev-tester | ✅ dev-planner |
| `/spec-update` | ✅ dev-planner | ✅ dev-implementer | ✅ dev-reviewer | — | ✅ dev-planner |
| `/ai-fix`, `/ai-spec-update` | 同上（platform CLI で実行） | | | | |
| `/pm-planning`, `/ai-pm-planning` | ✅ dev-planner | — | ✅ dev-reviewer | — | ✅ dev-planner |

> **注**: 各フェーズの担当ペルソナは `teams.yaml` の `persona_refs × phase_affinity` から自動導出される。T1/T2 ペアは同一ドメインの同一ワークフローを使用し、オーケストレーション方式のみ異なる。

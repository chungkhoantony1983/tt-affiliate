# Work Log: {作業名}

> Master DR: `../{kebab-title}.md`
> Issue: #NNN
> Goal slug: `{kebab-slug-of-goal}`

## 要求構造化

### 統合目的 (Unified Purpose)

{全要求を一文に統合した上位目的}

### 分解目的 (Decomposed Goals)

<!-- resolve は「何を / なぜ」のみ。「どうやるか」は structure_define phase で合意する -->

1. {sub-goal-1}: {説明}
2. {sub-goal-2}: {説明}

### 前提条件

- {条件}

### スコープ外

- {除外事項}

### SSoT 変更判定

ssot_impact: {none | [変更対象 SSoT ファイルリスト]}

## 制約追加履歴

| 日付 | 制約 ID | 内容 | トリガー |
|---|---|---|---|
| 2026-MM-DD | C-{N}-1 | ... | user 「...」 |

## 構造定義 (合意済)

### {sub-goal} の構造定義

(フローチャート / データ定義 / 実装方針 — structure_define phase で合意)

## 作業進捗

| 日付 | 作業 | 結果 |
|---|---|---|
| 2026-MM-DD | (作業内容) | 完了 / 進行中 / blocked / deferred |

## Phase 完了検証

> Phase 分け作業の場合のみ。`design-process-guide.md §2.8 Phase 完了プロトコル GL-009` 参照。

### sub-goal ステータス

| sub-goal | 状態 | 検証方法 |
|---|---|---|
| ... | done | ... |

### 3 層エビデンス

- **Layer 1 (存在確認)**: ...
- **Layer 2 (値検証)**: ...
- **Layer 3 (ソース突合)**: ...

### 制約 → テスト対応表

| 制約 ID | 制約内容 | 検証テスト | 結果 |
|---|---|---|---|
| C-{N}-1 | ... | ... | PASS |

## デシジョンテーブル

> `design-process-guide.md §2.8 デシジョンテーブル駆動テスト GL-010` 参照。

| ID | 前提条件 | 入力 | 期待値 | 実測値 | 判定 | 種別 |
|---|---|---|---|---|---|---|
| DT-001 | ... | ... | ... | ... | PASS / FAIL | CALC / PASS-THRU |

---
id: {kebab-title}                      # 必須、ファイル名 (.md なし) と一致、prefix 不要
title: 短い title (1 行、日本語可)        # 必須
status: proposed                       # proposed → accepted | superseded | deprecated | rejected | legacy_accepted
date: 2026-MM-DD                       # 起票日
accepted_date: null                    # accepted 遷移日 (任意)
issue: NNN                             # Issue 番号 (or null)
pr: null                               # PR 番号 (or null、両方ある場合は issue 優先)
scope: framework | project             # 必須、適用範囲
supersedes: []                         # 任意 [{old-kebab-title}, ...]
superseded_by: null                    # 任意、後続 DR の kebab-title
related_issues: []                     # 任意 [#NNN, ...]
related_specs: []                      # 任意 [docs/specs/..., ...]
last_reviewed: 2026-MM-DD              # accepted 以降必須、180 日経過で soft warning
owners: []                             # 任意 [@username, ...]
tags: []                               # 任意、検索性向上 [governance, ...]
legacy_path: null                      # 任意、legacy_accepted のみ必須 (旧 flat path)
external_review: []                    # AI 多角諮問結果 (詳細は本ファイル §External Review)
aliases: []                            # 任意、legacy DR の retrofit 後の旧 id 維持
---

# {DR title}

## Context (背景)

{なぜこの判断が必要になったか、トリガーとなった issue / 制約 / 既存負債}

## Decision (決定内容)

{採用した方針、1-2 段落で簡潔に}

## Rationale (採用根拠)

{比較分析、評価軸}

## Alternatives Considered (検討した選択肢)

| 選択肢 | 利点 | 欠点 | 採否 |
|---|---|---|---|
| A. ... | ... | ... | 採用 / 棄却 |
| B. ... | ... | ... | ... |

## Impact Analysis (影響範囲洗い出し)

- **影響を受ける spec**: `docs/specs/...` (反映 PR: #...)
- **影響を受けるコード**: `src/...` (修正範囲明示)
- **影響を受ける他 DR**: {kebab-title} (supersedes / 関連)
- **無影響確認箇所**: ... (明示的に無影響と記載)

## Consequences (影響・トレードオフ)

- 受け入れる影響: ...
- 想定リスク: ...

## External Review (AI 多角諮問)

| Round | Model | Date | Verdict | 補強事項 |
|---|---|---|---|---|
| 1 | gemini-2.5-pro | 2026-MM-DD | APPROVE | ... |
| 1 | gpt-5 | 2026-MM-DD | APPROVE | ... |

詳細レビューログ: `docs/decision-records/{N}/review/{round}-{model}.md`

## Human Justification (なぜ AI 推奨を採用 / 修正 / 棄却したか)

{監査における説明責任の核。「AI がそう言ったから」は理由にならない}

## Adoption Comparison Table (高影響領域のみ)

> 高影響領域 (セキュリティ / 法令影響 / 資産不可逆変更 / 跨 PJ breaking change) の場合に必須。

| 評価軸 | AI 案 1 | AI 案 2 | 採用案 | 採否理由 |
|---|---|---|---|---|
| 実装コスト | ... | ... | ... | ... |
| リスク | ... | ... | ... | ... |
| 保守性 | ... | ... | ... | ... |
| パフォーマンス | ... | ... | ... | ... |

## 制約事項 (DR 局所制約)

| ID | 制約内容 | 根拠 | 由来 |
|---|---|---|---|
| C-{N}-1 | ... | ... | user 指示 / GPT 諮問 / etc. |

## Related

- supersedes: {kebab-title} (or なし)
- related_specs: docs/specs/...
- related_issues: #...
- task: `task/plan.md` + `task/work-log.md` + `task/state.json`

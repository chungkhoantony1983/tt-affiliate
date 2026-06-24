# Task Plan: {作業名}

> Master DR: `../{kebab-title}.md`
> Issue: #NNN

## タスク分解

| # | sub-goal | 担当 | Input | Output | 格納先 |
|:-:|---|:-:|---|---|---|
| 1 | (sub-goal 内容) | Implementer | ... | ... | ... |
| 2 | ... | ... | ... | ... | ... |

## DoD (Definition of Done) 各 sub-goal 共通

各 sub-goal で以下を全件満たす:

- [ ] 仕様 (`docs/specs/`) 反映
- [ ] テスト (e2e / integration / unit、変更カテゴリ別必須層) 反映
- [ ] 実装完了
- [ ] 制約 → テスト対応表 完備
- [ ] PR 作成 → multi-model review → approve
- [ ] merge

### Phase 分け 3 条件 (DPG §2.9.2 R2 で declared、Issue #338 PR-E2)

各 phase は以下 3 条件 **AND** を満たすこと (無計画な phase 分けは禁止):

- [ ] **デグレなし**: 当該 phase 完了時点で本番ユーザー機能に regression なし (中間状態で deploy 可能な完成度)
- [ ] **体験完結**: 当該 phase で完結する value delivery (途中で機能不全にならない)
- [ ] **検証可能**: e2e test でデグレ確認 + 修正 bug 残存確認 + NFT 実施 が当該 phase 内で実施可能 (詳細は DPG §2.9.3 R3 NFT)

### artifact-only change 例外 (3 判定基準全 satisfied 時のみ適用可)

artifact-only change (doc-only refactor / SSoT 規範改訂 / placement 修正等) の判定基準:

- [ ] `git diff --name-only` で `src/` / `tests/` パスが 0 件
- [ ] CI runtime に影響しない (`docs/`、`README.md`、`CHANGELOG.md` 等の non-executable change のみ)
- [ ] existing test suite に impact しない (test code 変更なし、test 実行対象 (`pytest --collect-only`) の change なし)

3 条件全 satisfied なら以下に置換:

- [ ] **APG path regex lint + DPG/PPG 命名規則 lint 100% pass** (e2e 代替)
- [ ] **declared regex grep**: 旧 drift pattern 0 hit + 新 declared ≥ 1 hit (bug 残存確認 代替)
- [ ] (NFT 置換不要、artifact-only change は性能影響 0)

## デシジョンテーブル

| ID | 前提条件 | 入力 | 期待値 | 実測値 | 判定 | 種別 |
|---|---|---|---|---|---|---|
| DT-001 | ... | ... | ... | ... | TBD | CALC / PASS-THRU |

## E2E 検証チェックリスト

| ID | 検証内容 | 期待値 | 実測値 | 判定 |
|---|---|---|---|---|
| V-1 | (e2e シナリオ) | ... | ... | TBD |

## Verification Checklist

### e2e
- [ ] シナリオ + Given/When/Then 記述
- [ ] 契約境界 (input/output) 疑似 Assert

### integration
- [ ] 対象 IF / 契約 + Fixture 雛形
- [ ] 主要 success/failure ケースの test 関数 declared

### unit
- [ ] 主要 module の 失敗 + 成功 ケース test 関数 declared

## リスク・前提条件

| リスク | 対策 |
|---|---|
| (例) 既存実装の破壊的変更 | 段階的 enforcement (declared → 実装 → 強制) |

| 前提 | 確認 |
|---|---|
| (例) PR 順序が守られる | task/work-log.md で順序記録 |

## 制約事項 (Constraints)

| ID | 制約内容 | 根拠 |
|---|---|---|
| C-{N}-1 | ... | ... |

## 影響を受ける SSoT ドキュメント

| path | 変更概要 |
|---|---|
| `docs/specs/...` | ... |
| `docs/manual/...` | ... |

## 関連

- Issue: #NNN
- DR: `../{kebab-title}.md`
- 関連 PR: PR#NNN

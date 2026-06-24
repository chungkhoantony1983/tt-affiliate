# 成果物配置ガイド

> **SSoT (単一参照点)**: 本ファイル (`ai_team_v2/docs/manual/artifact-placement-guide.md`) = `docs/` + `src/` + `tests/` **全成果物の配置ルール SSoT**。Platform 全 PJ 共通の成果物配置 + DR 物理配置 規範 (DR governance の中身 = design-process-guide §2.7 を参照)。
>
> **4 ガイド責務分離**:
>
> | ガイド | scope |
> |---|---|
> | **本ファイル (artifact-placement-guide)** | 配置 path tree のみ + DR 物理配置 |
> | `design-process-guide` | L1〜L5 設計プロセス + `docs/` + `src/` 配下成果物一覧 + 命名規則 + 記載ルール |
> | `pj-process-guide` | G0 PJ管理 + `docs/deliverables/` 配下成果物 + PM artifacts生成プロセス |
> | `development-guide` | GitHub機能運用 + リポ運用 + コーディング規範 |
>
> 本ファイルは「どこに置くか」の単一参照点。命名規則 / 詳細規範 / layer mapping は他文書を参照。

## 目次

- [成果物配置ガイド](#成果物配置ガイド)
  - [目次](#目次)
  - [本ガイドの目的](#本ガイドの目的)
  - [配置決定木 (8 step decision)](#配置決定木-8-step-decision)
  - [配置先 一覧表 (SSoT)](#配置先-一覧表-ssot)
    - [Layer 別 1 dir 構造](#layer-別-1-dir-構造)
    - [Layer 外 (参考 / 派生)](#layer-外-参考--派生)
    - [上記 13 種別への分類例 (境界が曖昧になりやすい文書)](#上記-13-種別への分類例-境界が曖昧になりやすい文書)
  - [既存ガイドとの参照関係](#既存ガイドとの参照関係)

## 本ガイドの目的

新規 `.md` / `.d2` / `.yaml` 等の成果物を **どこに配置するか** + **どう命名するか** を declared する。AI agent / 人間の自己流配置を防ぐ単一参照点。

CLAUDE.md SSoT 索引 (関心ごと → ファイルパス) を本ガイドが運用面で具体化する。design-process-guide §2.7 (DR scope + TDD 反映フロー) と組合せて DR 運用の完結セット。

## 配置決定木 (8 step decision)

新規成果物作成時に以下を順に問う:

![成果物配置決定木](diagrams/artifact-placement-decision.drawio.svg)

> D2ソース: `docs/manual/diagrams/artifact-placement-decision.d2`

## 配置先 一覧表 (SSoT)

| 文書性質 | 適用範囲 | lifecycle | 配置先 path | 命名 | 例 |
|---|---|---|---|---|---|
| **規範 / ガイド** | framework-generic | 変動 | `docs/manual/{name}-guide.md` | kebab-case + `-guide` suffix | `design-process-guide.md`, `development-guide.md`, `artifact-placement-guide.md` |
| **L1 Strategy** (§0 前提 / §1 関連組織・アクター・システム / §2 UN / §3 SC / §4 SP / §5 UL / §6 Reference Index / §7 SLO + CRC + reference/。DPG §2 #1〜#2 参照) | framework or PJ | 不変 (大改訂時は新版) | `docs/specs/strategy/{strategy.md, crc.md, reference/{name}}` | 固定 filename (strategy.md / crc.md) / reference/ 配下は元ファイル名維持 (= 英語変換禁止) | `strategy.md` (§4 SP に永続的 PJ 制約も含む)、`crc.md` (Change Request Catalog、L1→L2)、`reference/{元ファイル名}` (= 旧 groundwork 統合先、 業務ソース抜粋 / 競合サーチ / 既存実装ソース / 調査エビデンス) |
| **L2 Requirements** (Cap一覧 + capability-landscape + BPM + 画面 coverage 台帳 + 画面 UI 参考。DPG §2 #3〜#6 参照) | PJ-specific | 変動 | `docs/specs/requirements/{capabilities.md, capability-landscape.{d2,drawio.svg}, bpm/{scenario}.{d2,drawio.svg}, bpm/{scenario}-actor-derivation.md, screen-coverage-matrix.md, reference/{name}}` | 固定 filename (capabilities/capability-landscape/screen-coverage-matrix) / kebab-case (bpm シナリオ) / reference/ 配下は元ファイル名維持 (= 英語変換禁止) | `capabilities.md`、`capability-landscape.d2`、`bpm/case-onboarding.d2`、`screen-coverage-matrix.md`、`reference/{元ファイル名}` (= L2 画面モックの UI デザイン参考、 strategy/reference の L2 版) |
| **L3 Architecture** (Cap 定義 + cross-Cap 横軸 + API + UI + modeling + STRIDE 等。capability-landscape / BPM は L2 配下) | PJ-specific | 変動 | `docs/specs/architecture/{...}` (テーマ別 sub-dir + cross-Cap singles 直下) | snake_case (Cap関連) / kebab-case (図) | `capabilities.md`, `api/`, `openapi/`, `ui/`, `modeling/`, `test-strategy/`, `system-flow/`, `dfd/`, `component-diagrams/`, `security/`, **`capabilities/{cap}.md` (Cap 個別 L3 詳細の canonical、DPG #6)**, `component-landscape.d2`, `container-diagram.d2`, `db-er-diagram.d2`, `parnas-evaluation-matrix.md`, `threat-model.md` |
| **L4 Implementation** (横串 9 観点 + per-Cap 任意) | PJ-specific | 変動 | `docs/specs/implementation/{name}.md` | kebab-case | `component-design.md`, `design-tokens.md`, `routing.md`, `observability-design.md`, `{cap}.md` (per-Cap) |
| **L2 画面モック (web)** (体験検証・顧客レビュー、navigable flow prototype) | PJ-specific | 変動 (**本番実装の前身** = データ層差し替えで本番化、何も捨てない) | 本体 = **`web-spa/`**（standalone-capable な web area = mock の SPA がそのまま本番 web 画面の正本。React + Vite + react-router + design-system。技術選定基準 = DPG §5 §mock 技術選定基準が SSoT）。台帳 = `docs/specs/requirements/screen-coverage-matrix.md` | — (code は web-spa/ 配下命名規則、 matrix は固定 filename) | `web-spa/`（リポ root 直下）、`screen-coverage-matrix.md`。環境/デプロイ手順は `docs/manual/mock-prototype-guide.md` |
| **L2 画面モック (mobile)** (スマホ native、 ネイティブ機能 plugin (= 外部 SDK 統合等) 統合) | PJ-specific | 変動 | 本体 = `mobile/`（リポ root 直下、 Capacitor wrap、 `@project/design-system` を npm 参照で共有、 native SDK を Capacitor plugin として組込み） | — (code は mobile/ 配下命名規則) | `mobile/`（リポ root 直下）。web 実装と同 codebase を build target 切替で利用 (= 二重実装禁止)。 ネイティブ UX は公式 Capacitor plugin 経由 |
| **共有 npm packages** (npm publish 配信) | framework or PJ | 変動 | `design-system/`（共有部品の単一正本 = tokens + components。既存 repo では既存配置を維持可） + 条件付きでマルチ channel ラッパー（**切り出し最小原則** = native app wrap / 他社埋込 widget / SDK packaging のみ。ラッパーが各アプリのデプロイ単位に依存する場合はデプロイ単位別に分割） | kebab-case dir + `@platform/{name}` npm scope | `design-system/` (= `@project/design-system`、 デザイントークン + 共有 component)、`mobile/` (= Capacitor wrap ラッパー)。テナント切替は runtime 設定 API (= npm package による静的 config 配布はしない) |
| **PM デリバリー** | PJ-specific | リリースサイクル active 管理 | `docs/deliverables/{release-cycle}/{PJ-PREFIX}-{NNN}-{name}.{md,csv}` | `{PJ-PREFIX}-{NNN}-{name}` 形式 (4 件: PJ-003/006/007/009 + 任意 099。PJ-001 は Issue #316 で削除) | `docs/deliverables/v1.0.0/IDM-006-WBS.csv`, `IDM-007-見積書_Stage1.md` |
| **DR (Decision Record)** | framework or PJ | **不変** (accepted 後改変禁止) | `docs/decision-records/{N}/{kebab-title}.md` (N = Issue or PR 番号、prefix 不要) | kebab-case (subfolder で context 明確) | `252/framework-refactor-master-plan.md` |
| **DR 補助文書** (draft / review / task) | 同上 | 変動 (task/ は accepted 後も継続更新) | `docs/decision-records/{N}/{draft, review}/{name}.md`、`docs/decision-records/{N}/task/{plan.md, work-log.md, state.json}` | kebab-case (task/ は固定 filename) | `252/draft/initial-design.md`, `252/task/plan.md` |
| **規範添付図** (D2 source、framework manual 内) | framework-generic | 変動 | `docs/manual/diagrams/{name}.d2` | kebab-case | `artifact-concretization-map.d2`, `artifact-placement-decision.d2`, `pj-deliverables-map.d2` |
| **規範添付図** (publish) | 同上 | **派生** (D2 → tool で自動生成) | `docs/manual/diagrams/{name}.drawio.svg` | source と同名 + `.drawio.svg` | (同上) |
| **L2/L3 設計図** (D2 source + drawio.svg pair、テーマ別 sub-dir) | PJ-specific | 変動 | `docs/specs/{requirements,architecture}/{theme}/{name}.{d2,drawio.svg}` (テーマ別) または `docs/specs/{requirements,architecture}/{name}.{d2,drawio.svg}` (single file 全体俯瞰) | kebab-case | (L2 requirements): `capability-landscape.{d2,drawio.svg}` (直下、single)、`bpm/{scenario}.{d2,drawio.svg}` (テーマ別) — (L3 architecture): `component-landscape.{d2,drawio.svg}` / `container-diagram.{d2,drawio.svg}` / `db-er-diagram.{d2,drawio.svg}` (直下、single)、`system-flow/{scenario}.{d2,drawio.svg}` / `dfd/{scenario}.{d2,drawio.svg}` / `component-diagrams/{cap}.{d2,drawio.svg}` (テーマ別) |
| **template (汎用、direct-use)** | framework-generic | 変動 | `docs/manual/templates/{name}.{md,csv,yaml}` | kebab-case + 用途 (中点 `.` 許容) | `dr-template.md`, `plan.template.md`, `wbs.template.csv` |
| **template (architecture scaffold)** | framework-generic | 変動 | `docs/manual/templates/architecture/{name}.{d2,md,csv,yaml}.template` | kebab-case + `.{ext}.template` suffix (実 file 拡張子を 2 段で明示) | `component-diagram-cap.d2.template`、`cap-api.v1.yaml.template`、`ui-screen.md.template` |
| **template (strategy section scaffold)** | framework-generic | 変動 | `docs/manual/templates/strategy/{name}.{md,yaml}.template` | kebab-case + `.{ext}.template` suffix | `strategy-actors-section.md.template`、`strategy.md.template`、`crc.md.template` |
| **template (requirements section scaffold)** | framework-generic | 変動 | `docs/manual/templates/requirements/{name}.{md,yaml}.template` | kebab-case + `.{ext}.template` suffix | `capabilities.md.template` / `capability-landscape.d2.template` / `bpm-scenario.d2.template` (Issue #355 PR-2) |
| **運用 (PJ 固有)** | PJ-specific | 変動 | `docs/operations/{name}.md` | kebab-case | `vercel-deploy-guide.md`, `development.md` |
| **export 成果物** | PJ-specific | **派生** | `docs/exports/{YYYY-MM-DD}-{name}.{pdf,xlsx,pptx}` | 日付 prefix | `2026-05-04-design-summary.pdf` |
| **business source** (外部入力、 raw データ全量) | PJ-specific | 不変 | `docs/specs/reference/{name}` または `docs/deliverables/{release-cycle}/reference/{name}` | (元ファイル名維持、 英語変換禁止) | `reference/competitor-ui.png` |
| **L1 strategy 抜粋 reference** (= 旧 groundwork 統合先、 業務ソース抜粋 + web 競合サーチ + 既存実装ソース + その他調査エビデンス。 strategy.md §6 Reference Index から index 化) | PJ-specific | 不変 | `docs/specs/strategy/reference/{name}` | (元ファイル名維持、 **英語変換禁止**) | `strategy/reference/{tenant}_{業務}_業務手順書.xlsx`, `strategy/reference/競合A_画面キャプチャ.png` |
| **L2 requirements 画面 UI reference** (= L2 画面モックの UI デザイン参考、 業界 SaaS の画面パターン / UI キャプチャ / デザイン調査エビデンス。 strategy/reference の L2 版、 dir 内 README.md で index 化) | PJ-specific | 不変 | `docs/specs/requirements/reference/{name}` | (元ファイル名維持、 **英語変換禁止**) | `requirements/reference/README.md`, `requirements/reference/画面デザイン参考-業界ケーススタディ.md` |

### Layer 別 1 dir 構造

`docs/specs/` 配下は **layer 単位 1 dir** で構成する。**dir 名 = layer 名** で完全一致。設計プロセス (L1〜L4) と物理配置を 1:1 対応、AI agent / 人間が path だけで「どの layer の何 spec か」を即座に判別。

| layer | dir | 含む成果物 (主要) |
|---|---|---|
| **L1 Strategy** | `docs/specs/strategy/` | strategy.md (§0〜§7 構成、single) + crc.md (Change Request Catalog、L1→L2 ブリッジ) + **reference/{name} (= 旧 groundwork 統合先、 業務ソース抜粋 / 競合サーチ / 既存実装ソース / 調査エビデンス、 元ファイル名維持・英語変換禁止)** |
| **L2 Requirements** | `docs/specs/requirements/` | capabilities.md (Cap一覧+5軸概要) + **capability-landscape.{d2,drawio.svg} (Cap 全体俯瞰、L2 canonical)** + **bpm/ (BPM+システムフロー、L2 canonical、`{scenario}.d2` + `{scenario}-actor-derivation.md`)** + screen-coverage-matrix.md (全画面 過不足台帳) + **reference/{name} (= L2 画面モックの UI デザイン参考、 業界 SaaS 画面パターン / UI キャプチャ / デザイン調査、 dir 内 README.md で index・元ファイル名維持・英語変換禁止)** ／ 画面モック本体は `web-spa/` (standalone-capable、React + Vite + react-router + design-system。mock は本番実装の前身 = データ層差し替えで本番化)。共有部品は `@project/design-system` を npm 参照 |
| **L3 Architecture** | `docs/specs/architecture/` | capabilities.md (L2 紐付き Cap 一覧 = 同 L2 capabilities.md と同期) + api/ + openapi/ + ui/ + modeling/ + test-strategy/ + system-flow/ + dfd/ + component-diagrams/ + security/ + **capabilities/{cap}.md (Cap 個別 L3 詳細の canonical、DPG #6)** + 直下 single (component-landscape / container-diagram / db-er-diagram / parnas-evaluation-matrix / threat-model) |
| **L4 Implementation** | `docs/specs/implementation/` | 横串 9 観点 + per-Cap 任意 |

### Layer 外 (参考 / 派生)

| dir | 内容 |
|---|---|
| `docs/specs/external-api/{vendor}/` | 外部ベンダー仕様書 (PDF / 仕様書原本、設計に影響しない参考資料) |
| `docs/specs/reference/` | 参考資料 (= raw business source / converted-sources / 業務ソース変換結果等、 PJ 全体共通 reference) |
| `docs/specs/strategy/reference/` | L1 strategy.md §6 Reference Index 参照先 (= 旧 groundwork 統合先、 業務ソース抜粋 / web 競合サーチ / 既存実装ソース / 調査エビデンス、 元ファイル名維持・英語変換禁止) |
| `docs/specs/requirements/reference/` | L2 画面モックの UI デザイン参考 (= 業界 SaaS の画面パターン / UI キャプチャ / デザイン調査エビデンス、 画面モック作成時に参照。 strategy/reference の L2 版、 dir 内 README.md で index・元ファイル名維持・英語変換禁止) |
| `docs/specs/archive/` | 廃止された設計資料 (legacy 保護) |

> **L5 は specs/ 配下不要**: L5 = 実装、`src/{cap}/` + `tests/` が SSoT。spec ではなくコード自体が canonical。

> **テーマ別配置原則**: 各 layer 配下で複数 file が出る場合は **テーマ別 sub-dir** で分類 (bpm/, system-flow/, dfd/, component-diagrams/, security/, api/, ui/ 等)。`diagrams/` のような catch-all dir は禁止。

### 上記 13 種別への分類例 (境界が曖昧になりやすい文書)

| 文書 | 分類 | 配置先 |
|---|---|---|
| **test 戦略 / QA 計画** (per-Cap unit / cross-Cap integration / e2e の方針) | L3 architecture spec (Cap §⑤' Quality 連動) | `docs/specs/architecture/test-strategy/{scope}-strategy.md` (例: `per-Cap-unit-strategy.md` / `cross-Cap-integration-strategy.md` / `e2e-strategy.md`) |
| **migration plan** (DB schema 変更 / breaking change の移行手順) | 運用 (PJ-specific) | `docs/operations/migration-{name}.md` |
| **API 文書 (OpenAPI / AsyncAPI / GraphQL)** | L3 architecture spec | `docs/specs/architecture/api/cap/{adapter}.v{N}.yaml` (AsyncAPI) + `docs/specs/architecture/openapi/cap/{adapter}.v{N}.yaml` (OpenAPI)。DPG #11 整合、`cap-` prefix なし |
| **API 契約・物語的説明** | architecture spec | `docs/specs/architecture/capabilities/{cap}.md` (Cap §② の延長、DPG #6) |
| **CHANGELOG** | **規範対象外** | repo root `/CHANGELOG.md` (慣習) |
| **リリースノート** | 運用 (PJ-specific) | `docs/operations/release-notes/{version}.md` |

## 既存ガイドとの参照関係

- **design-process-guide.md §2.7**: DR scope / template / TDD 反映フロー / lifecycle 遷移 / レビュープロセス / 起票粒度 (DR 本文の中身) を SSoT
- **artifact-placement-guide.md (本ガイド)**: DR 物理配置、および全成果物の配置決定木 (命名規則は DPG / PPG、DR 本文構造・lifecycle・レビュープロセスは design-process-guide §2.7 を参照。本ガイドは path tree のみ declared)
- **design-process-guide.md §1.6 F**: src/ 配下のソースコード配置 (本ガイドは docs/ 配下、src/ は §1.6 F + PR-1B-1)

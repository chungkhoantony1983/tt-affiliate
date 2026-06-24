# 設計プロセスガイド

## 目次

| § | セクション | 概要 |
|:---:|---|---|
| 1 | [本書の目的](#1-本書の目的) | scope・4ガイド責務分離 |
| 2 | [成果物マップ](#2-成果物マップ) | 成果物一覧・Input/Outputチェーン・正本レジストリ・粒度基準・レイヤー禁止事項 |
| 3 | [設計原則と理論的基盤](#3-設計原則と理論的基盤) | 採用概念・独自概念・プロセス原則・PO対話原則 |
| 4 | [境界設計原則](#4-境界設計原則) | §4.1 Cap境界(A〜E) + §4.2 Component境界(IC-1〜8) |
| 5 | [設計プロセス（Layer別）](#5-設計プロセスlayer別) | L1→L2→L3→L4→L5 |
| 6 | [ガバナンス (= 意思決定 + 未決管理)](#6-ガバナンス--意思決定--未決管理) | 意思決定 (= DR で選択肢 / 調査 / 議論を記録) + 未決管理 3 系統 (= DR / Issue / OQ) + DR scope・template・lifecycle・AI諮問 |
| 7 | [設計→実装連動](#7-設計実装連動) | Phase完了プロトコル・TDD・テスト規範 |
| 8 | [成果物生成プロセス](#8-成果物生成プロセスハルシネーション防止) | ハルシネーション防止・input source規範 |
| 9 | [品質ゲート（CP-1〜4）](#9-品質ゲートcp-14) | チェックポイント定義 |
| 10 | [テンプレートとプロセスツール](#10-テンプレートとプロセスツール) | テンプレート参照 + プロセスツール |
| 11 | [PJ規模別スケーラビリティ](#11-pj規模別スケーラビリティ) | Large/Medium/Small/Micro |

---

## §1: 本書の目的

ケイパビリティ駆動のソフトウェア設計プロセスを定義する汎用フレームワーク。マルチクライアントSaaSを主要ユースケースとするが、他PJにも適用可能。**「何を決めたら次に何を決めるか」** を定義する。

### scope

| ガイド | scope |
|---|---|
| **本ファイル (design-process-guide)** | L1〜L5 設計プロセス + `docs/` + `src/` 配下成果物一覧 + 命名規則 + 記載ルール |
| `pj-process-guide` | G0 PJ管理 + `docs/deliverables/` 配下成果物 + PM artifacts生成プロセス |
| `development-guide` | GitHub機能運用 + リポ運用 + コーディング規範 |
| `artifact-placement-guide` | 配置path treeのみ + DR物理配置 |

---

## §2: 成果物マップ

> 全体像は下図の通り。D2ソースは `docs/manual/diagrams/artifact-concretization-map.d2`。

![成果物マップ](diagrams/artifact-concretization-map.drawio.svg)

### 成果物一覧

| # | Layer | 成果物 | ファイル | 書く内容 | Input | Output |
|:---:|:---:|---|---|---|---|---|
| 1 | L1 | 戦略定義 | `strategy/strategy.md` | §0 前提, §1 関連組織・アクター・システム, §2 UN(ユーザー要求+業務フロー骨格), §3 SC(成功条件), §4 SP(戦略原則・制約), §5 UL(用語集), §6 Reference Index, §7 SLO | 業務ソース | → 2,3,5 |
| 2 | L1→L2 | 変更要求カタログ | `strategy/crc.md` | 行ごとに1シナリオ。`ID / 変更内容(What) / 変動軸`形式。Cap未定義の段階でHowを含めず業務変化のみ記述 | 1,20 | → 3,7 |
| 3 | L2 | Cap定義 | `requirements/capabilities.md` | 全Capを1ファイルに定義。各Cap: 責務/境界/データ(Aggregate+**データ項目 table (= 論理名 + 属性 + 制約)**+ライフサイクル表+権限マトリクス)/出すもの(画面・帳票・通知・外部出力)/ルール/設定/品質。末尾にアウトプット一覧付録。**物理名 (= DB 列名 / API field 名) は L2 では declared 禁止** (= L3/L4 で具体化)。 ただし既存 Business Application の実装について論じる場合は **「論理名 (物理名)」 併記表記推奨** (= 例: `案件番号 (case_number)`、 ハルシネーション防止) | 1,2,5,20 | → 4,7,12 |
| 4 | L2 | Capランドスケープ | `requirements/capability-landscape.d2` | CapをD2ノードとし、連携方式（Event/Read-Only）をエッジラベルで表す俯瞰図 | 3 | → 8,10 |
| 5 | L2 | BPM | `requirements/bpm/{scenario}.d2` | 業務プロセス swim lane。Lane=人間アクター+外部システム+システム自動。activity注記: 入力/出力(業務用語)/外部連携先/出典/[Cap名](後追い) | 業務ソース,1,20 | → 3,12 |
| 6 | L2 | 画面モック | 本体 = **standalone-capable な web area** (= `web-spa/`、React 18 + Vite + react-router + design-system。Vercel 等で顧客レビュー配信) | 全画面 breadth-first（低fi）→ navigable flow prototype（ページ間遷移・stateful）。**mock は本番実装の前身であり、別実装ではない** = view-model seam (= DPG §5) に MSW / @mswjs/data でモックデータを束縛し、本番化はデータ層の差し替えのみ（screen component / route tree / view model / UI 構造は変えない = 何も捨てない）。共有部品は `@project/design-system`（デザイントークン + 共有 component の単一 package）を基盤に組み再発明しない。画面 component には環境分岐を入れない。体験で「定義そのものの機能不足」を発見し顧客レビュー往復。**standalone-capable** な構成 (= 自前 root mount + client router) により Web 埋込・スマホアプリ (Capacitor wrap)・SDK / widget へ持ち越せる (= マルチ channel portability)。詳細は §5 L2 §画面モック、環境/デプロイ手順は `mock-prototype-guide.md` | 1,3,5,20 | → 1,3,5(消化), 12 |
| 7 | L3 | Parnas評価 | `architecture/parnas-evaluation-matrix.md` | CRC×Cap S/N判定マトリクス。S合計最小化 | 2,3 | → 3(FB) |
| 8 | L3 | Component俯瞰 | `architecture/component-landscape.d2` | 全Capの公開Adapterを`Cap::Adapter名`形式のノードで列挙し、Adapter間の呼び出しを有向エッジで示すD2グラフ | 4,3 | → 9,14,16 |
| 9 | L3 | Component詳細 | `architecture/component-diagrams/{cap}.d2` | Cap単位のD2図。Adapter/Internal/Contracts/Scriptsの4層に展開 | 3,8 | → 15,16 |
| 10 | L3 | Container図 | `architecture/container-diagram.d2` | デプロイ単位（プロセス/DB/キュー）を技術ラベル付きD2ノードとし、通信プロトコルをエッジで表す | 4,3 | → 13,17 |
| 11 | L3 | API定義 | `architecture/api/cap/{adapter}.v{N}.yaml` + `architecture/openapi/cap/{adapter}.v{N}.yaml` | OpenAPI/AsyncAPI | 3 | → 13,15 |
| 12 | L3 | UI画面仕様 | `architecture/ui/{screen}.md` | 各画面1ファイル。情報定義(Cap/Aggregate紐付き+表示/更新区別) → 主要操作 → モック検証記録 → 画面項目定義 → 画面遷移 → 受入基準 | 3,5,6,20 | → 14 |
| 13 | L4 | セキュリティ・監視設計 | `implementation/security-and-observability-design.md` | STRIDE対策実装, PII, 認可+権限マトリクス, 監視・ログ・SLI | 3,10,11,20 | → L5 |
| 14 | L4 | UI実装設計 | `implementation/ui-implementation-design.md` | 画面遷移 + Cap↔UI対応表 + Atomic Designコンポーネント設計（共有 `@project/design-system` 基盤、現状トークン層） | 3,6,8,9,12 | → L5 |
| 15 | L4 | Repository IF設計 | `implementation/repository-if-design.md` | 設計原則, テーブル一覧・定義, Repository IF一覧, データ整合性監査 | 3,9,11,20 | → L5 |
| 16 | L4 | ディレクトリ構造 | `implementation/directory-structure.md` | フロント+バックエンド+BFFのsrc/物理構造。IC-1〜IC-8準拠 | 8,9 | → L5 |
| 17 | L4 | インフラ設計 | `implementation/infrastructure-design.md` | デプロイ, 環境分離, CI/CD, スケーリング, DB運用, 障害復旧 | 10,3,20 | → L5 |
| 19 | L5 | 実装 | 新規 web 画面 = **standalone-capable な web area** (`web-spa/`、react-router)。バックエンド/非 web cap = `src/{cap}/` + `tests/`。配置 SSoT = artifact-placement-guide。既存プロダクトの legacy 資産は現位置維持 | 本番品質コード + TDD駆動テスト。L2 画面モックの screen component を view-model seam 越しに昇格（MSW/@mswjs/data → 実 Repository 差し替え。screen / route / view model / UI は不変） | 13-17 | — |

> **削除**: #20 「設計補助資料 / `groundwork/{topic}.md`」 (= 旧 横断成果物) は **廃止** (= `docs/specs/strategy/reference/` に統合、 業務ソース抜粋 + 競合サーチ + 既存実装ソース + その他調査エビデンスを strategy.md §6 Reference Index から参照する形に一本化)。

### Layer配置ルール

| Layer | ディレクトリ | 粒度ルール |
|---|---|---|
| L1 | `strategy/` | single |
| L2 | `requirements/` | capabilities.md=single、BPM=シナリオ毎。画面モック本体は `web-spa/` (standalone-capable、React + Vite + react-router + design-system。体験検証用、Vercel 等で配信) |
| L3 | `architecture/` | 画面毎、シナリオ毎 |
| L4 | `implementation/` | single（横串設計文書） |
| L5 | 新規 web 画面 = `web-spa/`（standalone-capable）+ バックエンド/非 web = `src/{cap}/` + `tests/`（legacy 資産は現位置維持） | — |

**禁止**: Layer間をまたぐ粒度の成果物（例: L2+L3を1ファイルで扱う）。

### 導出成果物

| 導出成果物 | 導出元 | 用途 | 作成タイミング |
|---|---|---|---|
| `requirements/bpm/{scenario}-actor-derivation.md` | BPM(#5) + 業務ソース | 各BPM Laneのアクター割り当て根拠 | BPM作成時 |
| `requirements/screen-coverage-matrix.md` | Cap §出すもの(#3) + BPM(#5) | 全画面の過不足台帳（cap output↔screen のトレーサビリティ。L2 coverage gate で ok/ng） | Cap確定後（画面モック着手前） |
| `architecture/threat-model.md` | Container図(#10) + 全Cap §品質 | STRIDE脅威識別マトリクス | L3 cross-Cap横軸作成時 |
| `architecture/test-strategy/{scope}-strategy.md` | 全Cap §品質 + §7テスト規範 | PJ全体のテスト戦略 | L3完了後 |

### 成果物の作成順序（timing）

| Layer | 成果物 | 作成タイミング | 更新トリガー |
|---|---|---|---|
| L1 | strategy.md | PJ開始時 | 事業方針変更 |
| L1 | crc.md | strategy確定後 | 新変更シナリオ発見 |
| L1→L2 | bpm/*.d2 | 業務ソース+strategy確定後 | 業務フロー変更 |
| L2 | capabilities.md | BPM+CRC確定後 | Cap再編 |
| L2 | capability-landscape.d2 | capabilities確定後 | Cap追加/統合 |
| L2 | screen-coverage-matrix.md | capabilities確定後 | 画面追加/cap output 変更 |
| L2 | 画面モック (`web-spa/`) | coverage-matrix確定後 | 体験で不足発見/cap変更 |
| L3 | parnas-evaluation-matrix.md | Phase C（整合性確認） | Cap再編時 |
| L3 | ui/{screen}.md 情報定義 | capabilities確定後 | 画面変更時 |
| L3 | component-landscape.d2 | capabilities L3確定後 | Cap追加時 |
| L3 | component-diagrams/{cap}.d2 | component-landscape確定後 | Component変更時 |
| L3 | container-diagram.d2 | component-landscape確定後 | デプロイ方式変更 |
| L3 | api/cap/{adapter}.v{N}.yaml | capabilities L3確定後 | API変更時 |
| L3 | ui/{screen}.md 詳細 | 情報定義+モック検証後 | 画面変更時 |
| L4 | 実装設計文書群 | L3確定後 | L3変更時 |
| L5 | web-spa/ (新規 web) + src/{cap}/ + tests/ (非 web) | L4確定後（画面モックの component は view-model seam 越しに昇格） | 設計変更時 |

**逆順禁止**: L3成果物をL2未確定で作成しない。L4をL3未確定で作成しない。違反は上流制約原則違反。（画面モックは L2 の体験検証 instrument であり、L3/L4 未確定でも着手可。ただし L5 本番昇格は L3/L4 の gate 通過が必須）

**BPMの作成順序**: BPMは業務ソースから先に書く。Cap紐付け（activity注記の[Cap名]）はCap導出後に追記する。BPMをCap導出の入力とするため、capabilities.mdより先に作成する。

### PJ固有成果物の追加ルール

L1〜L4全てにおいて、以下の3条件を満たせばPJ固有成果物を追加可能:

1. **責務分離**: 既存成果物との情報重複がないこと
2. **消化先明示**: この成果物をInputとする下流成果物が存在すること（消化先なし禁止）
3. **Layer配置**: APGのLayer=ディレクトリルールに従うこと

### §2a: 正本レジストリ

各概念の正本（Single Source of Truth）と、他レイヤーからの参照方法を定義する。**コピー禁止・再定義禁止**。正本変更時、参照側は要約/リンクのみ更新する。

| 概念 | 正本 | 参照方法 |
|---|---|---|
| 業務フロー骨格 | L1 §2 BF | L2 BPMが詳細化。コピー禁止 |
| 業務フロー詳細 | L2 BPM | L3/L4は参照のみ |
| アクター・組織・システム | L1 §1 関連組織・アクター・システム | BPM Pool / Lane で参照のみ。再定義禁止 |
| データ正本 | L2 Cap §データ | BPMは業務オブジェクト名で要約。L3 uiは画面用途の抜粋 |
| ライフサイクル | L2 Cap §データ（状態遷移表） | L3は関係する遷移のみ参照。図は表から導出（ビュー） |
| 権限 | L2 Cap §データ（権限マトリクス） | L3はUI可否に反映 |
| 画面一覧 | L2 Cap §出すもの | L3 uiが詳細化 |
| 画面項目 | L3 ui/{screen}.md | L2へ逆流禁止 |
| 帳票/通知 | L2 Cap §出すもの | L3/L4で必要時詳細化 |
| 用語 | L1 §5 UL | 全レイヤーで参照のみ。再定義禁止 |
| 設計補助資料 (= 業務ソース抜粋 / 競合サーチ / 既存実装ソース / 調査エビデンス) | `docs/specs/strategy/reference/{name}` (= 元ファイル名維持、 英語変換禁止) | L1 §6 Reference Index から index 化、 全レイヤーから参照。 成果物へのコピー禁止 (= 参照 + 出典明記)。 **旧 `groundwork/{topic}.md` は廃止 (= 本 path に統合)** |
| 画面 UI デザイン参考 (= 業界 SaaS の画面パターン / UI キャプチャ / デザイン調査エビデンス) | `docs/specs/requirements/reference/{name}` (= 元ファイル名維持、 英語変換禁止) | L2 画面モック (web-spa) 作成時の UI 参考。 strategy/reference の L2 版、 dir 内 README.md で index 化。 成果物へのコピー禁止 (= 参照 + 出典明記) |

### §2b: レイヤー粒度基準

各概念を各レイヤーでどの粒度で記述するかを定義する。上位レイヤーの粒度を下位レイヤーに持ち込まない。下位レイヤーの粒度を上位レイヤーに持ち込まない。

| 概念 | L1 | L2 BPM | L2 Cap | L3 ui 情報定義 | L3 ui 項目定義 |
|---|---|---|---|---|---|
| 業務フロー | 主要フェーズ(4-6) | 1成果物/1状態変化/1判断 | — | — | — |
| データ | **UN §情報定義 (= 業務フローの step 単位 declared = 入力 step に該当する UN で入力情報を、 出力 step に該当する UN で出力情報を declared。 UN と情報定義は 1:1 ではない = 入力系 / 出力系 / 入出力混在 / 情報定義なし いずれも自然発生。 format 自由 = 表 / bullet / 自由 declared、 grounded source で declared できる項目のみ、 §5 L1 §1 例外条項参照)** | 業務オブジェクト名 | **Aggregate + データ項目 table (= 論理名 + 属性 + 状態 + 権限)、 物理名禁止** | 画面の情報グループ | 画面部品レベル (= L1 UN §情報定義 引用必須) |
| 画面 | — | — | 画面名(1責務) | 1画面1ファイル | — |

### §2c: レイヤー禁止事項

各レイヤーで書いてはいけないものを定義する。違反は上流制約原則違反またはレイヤー越境。

| L1禁止 | L2禁止 | L3禁止 | L4禁止 |
|---|---|---|---|
| 人間が理解できない勝手な英語 ID（ハルシネーションの温床） | CSS | 実装コード | UN/SC/SP追加 |
| 業務概念併記なき物理名（業務理解を阻害） | Atomic Design | インフラ構成 | Cap境界変更 |
| ID のみの記載（業務概念なき純粋 ID） | コンポーネント名 | デプロイ手順 | 画面責務追加 |
| **snake_case / kebab-case 等の英語 ID 全般** (= **すべての ID は日本語必須**、 actor / system / activity / UN / SC / SP / BF 全て対象。 例外 = プロダクト固有名詞 (= freee / マネーフォワード / 弥生 / 勘定奉行 / TKC / Platform service 名 等、 Platform 全構造 = 各 PJ strategy.md §1 で declared SSoT) + 物理名 (= §2c L1 許容の DB 列名 / API field 等、 業務概念併記必須) のみ) | ライブラリ名 | 本番secret | 業務ルール追加 |
| **§1 未 declared の actor / 組織 / system 使用禁止** (= §1 declared list 内のみ参照可、 prose / table / BF タイトル / UN 全てに適用) | SQL | Cap境界再定義 | — |
| **§5 UL 二重記載禁止** (= §1 declared 済の組織 / 人間アクター / system は §5 UL で再記載しない、 §5 UL = 業務領域別用語 (= 請求書 / 与信 / 案件 等の業務概念) のみ) | HTML input type | — | — |
| **「PO 確認候補」 / TBD / 推測 / hedge declared 全面禁止** (= ハルシネーション扱い、 §6 未決管理 3 系統 (= DR / Issue / オープンイシュー) で管理、 §8 段階的制約 + R-DPG-6 整合) | 同左 | 同左 | 同左 |
| **決定経緯 / 改訂経緯 meta コメント全面禁止** (= 「2026-06-XX user 指示」 「同 UN 内整合」 「PR #N 改訂時」 等、 経緯は DR / commit message / PR description、 spec は確定値のみ) | 同左 | 同左 | 同左 |
| **顧客露出 NG な内部 jargon (= AI agent / framework / 開発プロセス 用語) 全面禁止** (= spec は **顧客 (PO / 業務担当 / 監査者 / 委託先) が読んで違和感ない平易な業務日本語** で記述。 §2c-bis 自然語 mapping 参照。 適用範囲は **spec 配下** (= `docs/specs/strategy/` / `docs/specs/requirements/` / `docs/specs/architecture/` / `docs/specs/ux/` 配下の全文書)、 **framework guide (= `docs/manual/` 配下)** は内部設計者向けで本規範対象外 = jargon 使用可) | 同左 | 同左 | 同左 |

**L1 許容 (ハルシネーション防止 + 業務 grain に必要)**:
- 既存システムの物理名（業務概念併記、例: `mt_transactions（銀行明細）` / `customer_documents（書類実体）` / `billings（旧 請求管理）` / `payments（旧 支払管理）` 等、ハルシネーション防止のために必要）
- **業務 grain の情報定義 (= 業務フローの step 単位 declared = 入力 step に該当する UN で入力情報を、 出力 step に該当する UN で出力情報を declared。 UN と情報定義は 1:1 ではない = 入力系 UN / 出力系 UN / 入出力混在 UN / 情報定義なし UN いずれも自然発生、 §5 L1 §1 例外条項参照)**: **format 自由** (= 表 / bullet / 自由記述 / 列挙 いずれも OK、 grounded source で declared できる形式で記述、 表形式を強制しない)。 各項目の属性 (= 必須 / 桁数 / 文字種別 / デフォルト / 規則 / 根拠) は grounded source で明示できる場合のみ記入 (= 推測・捏造禁止)。 logical 項目のみ OK、 **物理項目** (= DB 列名 / API field 名 / VARCHAR 型) は L2 Cap §データ aggregate / L3 / L4 で具体化
- 画面項目型（YYYY-MM-DD 等、業務日付の意味伝達に必要）
- UI 操作（タブ / ボタン / ローディング / 複数選択モード 等、PJ 特殊許容、PJ memo feedback grounded）

### §2c-bis: spec 顧客露出時の自然語 mapping (= 内部 jargon 全面禁止)

**規範**: spec (= `docs/specs/` 配下) は **顧客 (PO / 業務担当者 / 監査者 / 委託先) が読んで違和感ない平易な業務日本語** で記述する。 AI agent / framework / 開発プロセス 用語 (= 内部 jargon) は spec 本文に書かない。 framework guide (= `docs/manual/` 配下、 内部設計者向け) は本規範の対象外で jargon 使用可。

**禁止対象 (= spec 配下で grep 検出時は自然語に置換)**:

| 区分 | 禁止語 (例) | 顧客露出時の不可解度 |
|---|---|---|
| AI agent 規範 ID | `R-DPG-N` / `C-N` / `IC-N` / `SP-N` / `DR-N` / `[[feedback-XXX]]` / `[[feedback_XXX]]` | ★★★ 完全に意味不明 |
| 設計プロセス jargon | `declared` / `grounded` / `SoT` / `SSoT` / `Cap` / `Capability` / `OQ` / `hedge` / `cascade` / `override` / `inline` / `defer` / `scope` / `follow-up` / `TBD` | ★★ 業務文書として違和感 |
| 改訂経緯 meta | `2026-06-XX user 指示` / `PR #N 改訂時` / `commit {hash}` / `同 UN 内整合` | ★★ §2c で既禁止 (= 本節で再確認) |
| AI 内部用語 | `ハルシネーション` / `hallucination` / `推測・捏造` (= 評価語) | ★ spec 本文には書かない (= 評価は別管理) |

**自然語 mapping table (= 置換案、 顧客露出時に使う日本語)**:

| 内部 jargon | 自然語 (= 業務日本語) | 補足 |
|---|---|---|
| declared / declare | 定義 / 記載 / 規定 / 明記 | 動詞・名詞両対応、 文脈で選択 |
| grounded / grounded source | 根拠あり / 出典あり / 裏付けあり / 根拠資料 | 「grounded source 3 区分」 → 「根拠資料 3 区分」 |
| 内部決定記述 | 業務ヒアリング記録 / 業務確認記録 | 既に user 提示語 |
| PO 確認候補 / PO 確認待ち / PO 判断待ち | 業務確認中 / 業務確認待ち / 未確定事項 (業務確認中) | §2c で既禁止 (= hedge declared 全面禁止) |
| hedge declared | 暫定記載 / 保留記載 | §2c で既禁止 (= 言及時のみ自然語化) |
| OQ (Open Questions) | 未確定事項 / 検討中事項 | section 名: 「§未確定事項」 / 「§検討中事項」 |
| SoT / SSoT | 正本 / 単一参照点 | |
| Cap / Capability | 機能領域 / 機能 | L2 spec 文脈では「機能領域」 |
| TBD | 未確定 | |
| cascade | 横展開 / 反映 | |
| override | 上書き定義 | |
| inline | 直接記載 | |
| defer | 先送り / 後続対応 | |
| scope | 適用範囲 / 対象範囲 | |
| follow-up | 追加対応事項 / 後続課題 | |
| ハルシネーション / hallucination | (spec 本文には書かない) | 評価語、 §2a (= 上流制約原則) / §6 (= 未決管理) / DR で言及 |

**例外 (= 自然語化対象外)**:

- プロダクト固有名詞: `freee` / `マネーフォワード` / `弥生` / `勘定奉行` / `TKC` / `Platform` 等
- 技術固有名詞: `API` / `DB` / `entity` / `schema` / `VARCHAR` / `YYYY-MM-DD` / `enum` / `CSV` / `UI` / `PCI DSS` 等
- 略語 (業務役職 / 階層名): `PJ` / `PO` / `L1` / `L2` / `L3` / `L4` / `L5`
- PJ 内部 ID prefix (= trace 用): `UN-` / `SP-` / `BF-` / `SC-` 等 (= 各 PJ strategy.md で declared)

**運用**:

- 新規 spec 起票時 + 改訂時に grep audit (= 禁止語が混入していないか確認、 自然語に置換)
- 既存 spec の audit は別 PR で順次実施 (= 大規模 PJ spec は段階的に自然語化)
- 内部規範 ID / feedback memory ID / PR # / commit hash の trace は **DR / commit message / PR description / framework guide** で管理 (= spec 本文には書かない)

### §2d: 用語定義（曖昧さ回避）

成果物の粒度を揃えるため、以下の用語をDPG全体で統一する。

#### 画面単位の定義

- **screen**: 単一の業務責務を持つUI単位。L3 `ui/{screen}.md` の1ファイルに対応する。SPAではルート単位、MPAではURL単位
- **tab**: 同一screen内の情報グループ切替。別screenではない
- **modal / drawer / popup**: 同一screen上の補助操作。別screenではない
- **wizard**: 同一目的の段階分割であれば1 screen。各段が別目的・別責務なら別screen

#### BPM activity粒度基準

- **人間activity**: 1 actorが1回の判断で完了する業務操作
- **自動activity**: 業務上意味のある状態変化、外部連携完了、承認結果確定のいずれかを1単位とする
- 内部技術処理（変換、整形、ログ出力、キュー投入）はactivityに分割しない
- 通知送信は、業務上独立した意味を持つ場合のみ別activity。単なる副作用なら親activityの出力注記に含める

#### Cap「境界」の書き方

「境界」には、主要な隣接Capとの責務の違いを記述する。各項目は「XはYCapが扱う」の形式とし、必要なら「なぜ別か」を1句で添える。

#### ルールの範囲

「ルール」には、Capの正本データに対して適用される業務判定・計算・順序制約を書く。

- 書く: 状態遷移の成立条件、金額計算、承認要否、業務バリデーション
- 書かない: 画面入力の形式チェック（文字数、必須、正規表現）→ **L1 UN §情報定義 SoT (= 論理項目、 grounded のみ) + L2 Cap §データ aggregate (= データ項目 table 論理名)**
- 書かない: API/DBの技術制約 → L3/L4

バリデーション 3 階層:

**入力バリデーション (L1 UN §情報定義 + L2 Cap §データ aggregate)**: 単一入力値の形式制約。 logical level (= 桁数 / 文字種別 / 必須 / デフォルト / 根拠) は **L1 UN §情報定義 (= 業務 grain) + L2 Cap §データ aggregate (= 論理名 + 属性)** で SoT declared (= grounded source で明示できる場合のみ記入、 推測・捏造禁止)。 例: 「案件名は 40 文字以内 (= 全銀協 振込依頼人名 C(40) declared 準拠) / 半角英数字 + 記号」

**業務バリデーション (L2 Cap §ルール)**: 他データ・他状態に依存する制約。UI の有無に関係なく成立する。 例: 「完了にするには全イベント完了済み」「請求金額は受注金額以下」

**UI 配置 reference (L3 ui)**: L1 UN §情報定義 + L2 Cap §データ aggregate の画面 component 別具体化。 桁数 / 文字種等は L1/L2 引用必須、 L3 独自定義禁止 (= ハルシネーション源)。 配置 (= modal / form / table column) のみ L3 declared OK

**物理名 (= DB 列名 / API field 名 / VARCHAR 型) declared レベル**: **L2 Cap §データ aggregate / L3 / L4 いずれでも可** (= L4 限定ではない、 L2 Cap §データ aggregate 定義時に物理名決定し L3/L4 で引用する flow も可)。 ただし L1 UN は logical 項目のみで物理名禁止。 **既存 Business Application (= legacy system 連携) について論じる場合は 「論理名 (物理名)」 併記表記推奨** (= 例: `案件番号 (case_number)`、 grounded reference として、 ハルシネーション防止)

**判定基準**: 「UI なし API 直接操作時このルールは必要?」 → Yes なら L2 業務バリデーション (= Cap §ルール)、 No なら入力バリデーション (= L1 UN §情報定義 + L2 Cap §データ aggregate)。 L3 ui は L1 / L2 を引用、 独自定義しない。

#### BPM出力注記とCap「出すもの」の違い

- BPMの出力注記は「その業務ステップで何が発生するか」を示す（発生箇所）
- Capの「出すもの」は「そのCapが責任を持って提供する画面・帳票・通知・外部出力」を示す（責務正本）
- 同じ名称が両方に現れても、前者は発生箇所、後者は責務正本であり、重複ではない

### §2e: 制約の配置

§2a〜§2dの制約は以下の3層で適用する:

| 層 | 配置先 | 役割 |
|---|---|---|
| **DPG本文** | 本ファイル §2a〜§2d | 横断原則の定義 |
| **定義カード** | 各テンプレートの先頭コメント | 成果物ごとの正本/粒度/禁止の具体化 |
| **validator** | CI / レビュー時 | 禁止用語grep、正本レジストリ違反検出、粒度逸脱検出 |

#### validatorルール例

PJ固有の技術スタックに応じて拡張する。以下は最低限のルールセット:

| 対象ファイル | 禁止語（出現したらエラー） |
|---|---|
| `strategy/strategy.md` | API path、SQL、テーブル物理名、型定義 |
| `requirements/capabilities.md` | CSS、HTMLタグ、コンポーネント名、fetchコード、`className` |
| `requirements/bpm/*.d2` | React、Next.js、Rails、`POST /`、`SELECT`、`className`、`useState` |
| `architecture/ui/*.md` | DB物理名、SQL、API実装コード、`import`、`require` |


---

## §3: 設計原則と理論的基盤

**原則**: フレームワークを「原典が言っているから」ではなく「何の失敗モードを防ぐか」で評価する。防ぎたい失敗モードがないなら不要。

### 採用概念（原典借用）

| 概念 | 定義（What） | 防ぐ失敗モード（Why） | 着想源 | 本フレームワークでの適用 |
|------|------------|-------------------|--------|---------------------|
| **上流制約原則** | 変更困難な層から順に決定。下流で矛盾が発覚した場合は上流に遡って修正 | 下流の決定が上流を侵食する暴走 | Garrett (2002) 5層モデルから導出 | L1→L2→L3→L4→L5 |
| **ケイパビリティ** | 「ビジネスが何をできるか（What）」の単位。How（プロセス）から独立 | IT投資計画が組織変更で崩壊 | TOGAF/ArchiMate | Cap = What の単位 |
| **情報隠蔽** | 「変更されそうな設計決定のリスト」を秘密として隠す | 変更波及の爆発 | Parnas (1972) | CRC → Cap境界 → Parnas評価 |
| **CRC（変更要求カタログ）** | 「将来起こりうる変更」を事前に列挙し、設計の評価軸にする | 変更に弱い設計 | Parnas (1979) | CRC → Parnas S/N評価 |

### 独自概念

| 概念 | 定義 | 防ぐ失敗モード |
|------|------|---------------|
| **正本レジストリ** | 各概念の正本（SSoT）を1箇所に定義し、他は参照のみとする（§2a） | 情報重複による矛盾・陳腐化 |
| **レイヤー粒度基準** | 各レイヤーで書いてよい粒度を定義する（§2b） | 上流への詳細混入・下流への抽象混入 |
| **レイヤー禁止事項** | 各レイヤーで書いてはいけないものを定義する（§2c） | レイヤー越境（L2 に L4 混入等） |
| **段階的記述** | 1つの成果物を2段階で埋める（BPM: 業務→Cap注記、ui: 情報定義→項目定義） | 一度に全部書こうとしてハルシネーション混入 |

### プロセス原則

1. **業務ソース先行**: 業務ソース（既存帳票・業務マニュアル・ヒアリング）から書く。技術用語やCap名から逆導出しない
2. **正本単一**: 同じ情報を2箇所に書かない。正本レジストリ（§2a）に従う
3. **前段階制約**: 各段階で「前段階にないものは追加禁止」。情報定義にないものをモックに追加しない
4. **出典必須**: 業務ソースに基づく記述には出典を明記する。出典のない記述はハルシネーション候補

### PO対話原則

1. **業務フロー紐付き**: POレビューは業務フロー順に行う。Cap単位ではなく業務フロー単位
2. **早期画面レビュー**: 情報定義段階でPOレビューを行う（CP-2.5a）。詳細化前にフィードバックを得る
3. **ID+タイトル併記**: ID単体の参照禁止。`UN-1(申込進捗確認)` のように必ずタイトルを併記する。BPM・capabilities・ui等の全成果物で適用

### AIと人間の役割

| 段階 | AIがやること | 人間がやること | ゲート |
|---|---|---|---|
| L1 §UN | 業務ソースから骨格案を生成 | 骨格の妥当性承認 | CP-1 |
| L2 BPM | 業務ソースからactivity案を生成 | 粒度・漏れ・出典確認 | CP-1.5 |
| L2 Cap | BPMからCap案を生成 | 境界・責務・ライフサイクル確認 | CP-2 |
| L3 ui 情報定義 | Cap§データから情報定義案を生成 | 画面責務・情報過不足確認 | CP-2.5a |
| L2 画面モック | cap §データ→view-model 型 + 全画面を低fiで起こし、体験で機能の過不足を検出 | 実操作で負債・嘘・定義の不足を検出 | CP-2.5b |
| L3 ui 詳細 | CP-2.5b承認後に項目定義・遷移・受入基準を生成 | 整合性確認 | CP-3 |
| L4 実装設計 | L3成果物から横断設計を生成 | 横断的一貫性確認 | CP-4 |

---

## §4: 境界設計原則

**8原則サマリ**:

1. **Cap境界はL2で先に定義する。UIの都合で変更しない。**
2. **Aggregate境界はライフサイクル・整合性・変更ドライバーで決める。**
3. **Write操作は1画面1主Cap・1主Aggregate更新を原則とする。**
4. **複数Aggregate更新は例外であり、UI都合ではなく業務不可分性でのみ許容する。**
5. **横断表示はRead Modelで実現し、責任境界はWrite Modelで守る。**
6. **事後チェックで違反を必ず検出し、例外は明示管理する。**
7. **Adapter→Internal一方向依存。Internal は Pure。**
8. **Shared にビジネスロジックが入ったらCapに昇格。**

### §4.1 Cap境界原則

#### A. Aggregate境界の原則（L2段階）

| ID | 原則名 | 記述 |
|----|--------|------|
| A-1 | ライフサイクル同一性 | 同じ業務ライフサイクルで生成・更新・完了・失効する情報は同一Aggregateに保持 |
| A-2 | 整合性境界一致 | 同時に整合していなければ業務事故になる情報は同一トランザクションで守る |
| A-3 | 入力・更新・出力単位一致 | 業務上ひとまとまりに入力・検証・確定・監査される情報は原則1 Aggregate |
| A-4 | 変更ドライバー優先 | Aggregate分割の判断は画面構成ではなく変更ドライバーの差異に基づく |
| A-5 | 参照従属と更新責任の分離 | 頻繁に参照される情報でも、更新責任が別なら同一Aggregateに取り込まない |
| A-6 | Aggregate肥大抑制 | 「一緒に見たい」だけの情報を追加して肥大化させない |

#### B. Cap境界からUIへの制約伝搬（L2→L4）

| ID | 原則名 | 記述 |
|----|--------|------|
| B-1 | Cap先行原則 | Cap境界はL2で先に定義。UIの都合でCap境界を変更しない |
| B-2 | 1画面1主Cap | 画面のWrite操作は1つのCapのCommandのみ呼び出す |
| B-3 | 1画面1主Aggregate更新 | 画面のWrite操作は原則1つのAggregateのみ更新。複数Aggregate更新はD-1〜D-5の不可分性要件を満たす場合のみ例外許容 |
| B-4 | Read Model自由参照 | 表示目的では任意のCapのQuery操作を呼び出せる |
| B-5 | Cap-scoped状態管理 | UIの状態管理はCap単位でscope。cross-Cap stateは明示的Adapter経由 |
| B-6 | 画面遷移 = Cap IF遷移 | 画面遷移はCap §外部とのやりとりで定義されたフローに従う |
| B-7 | UI起点の境界変更禁止 | 「この画面で一緒に表示したい」はCap境界変更の根拠にならない |

#### C. 読み取りモデルと書き込みモデル

| ID | 原則名 | 記述 |
|----|--------|------|
| C-1 | Write Model = Cap境界 | データの書き込み責任はCap境界に従う |
| C-2 | Read Model = 自由合成 | 読み取りは複数Capのデータを自由に合成できる |
| C-3 | CQRS推奨 | Write ModelとRead Modelを分離 |
| C-4 | Read Model更新 = Event駆動 | Read ModelはDomain Eventをトリガーに更新 |
| C-5 | Read Model = 導出データ | 正本はWrite Model（Cap §データ）のみ |

#### D. 業務的不可分操作

| ID | 原則名 | 記述 |
|----|--------|------|
| D-1 | 不可分性の定義 | 「片方だけ成功した状態が業務上許されない」操作のみが不可分 |
| D-2 | 不可分性の検証 | 「片方だけ成功したら業務はどうなるか？」を具体的に検証 |
| D-3 | 不可分操作のCap配置 | 可能な限り1 Cap内に閉じ込める。Cap跨ぎは例外管理台帳(E-6)に登録 |
| D-4 | Saga/補償トランザクション | Cap跨ぎの不可分操作はSagaまたは補償トランザクションで実装 |
| D-5 | UI都合の不可分化禁止 | 「1画面で完結させたい」はD-1を満たさない |

#### E. 事後チェック（L4実装後）

| ID | 原則名 | 記述 |
|----|--------|------|
| E-1 | 各保存操作が何Cap・何Aggregateを更新するか一覧化 | ui/{screen}.md の情報定義と突合 |
| E-2 | B-2/B-3違反の検出 | 1画面で複数CapのWrite操作を呼んでいないか |
| E-3 | D-1〜D-5違反の検出 | 不可分性の根拠なく複数Aggregate更新していないか |
| E-4 | C-1違反の検出 | Write操作がCap境界を越えていないか |
| E-5 | A-5違反の検出 | 参照のみのデータをAggregate内に取り込んでいないか |
| E-6 | 例外管理台帳 | D-3例外（Cap跨ぎ不可分操作）を登録・管理 |

### §4.2 Component境界原則（L3段階）

#### 用語と判定3基準

| 種別 | 定義 |
|------|------|
| **Adapter** | Capの公開境界。外部との接点。Cap §外部とのやりとりの物理的な現れ |
| **Internal** | Capの内部実装。Adapter経由でのみアクセス。Domain Aggregate / Pure function / Strategy |
| **Shared** | 複数Cap共有ユーティリティ。ビジネスロジックを含まない（含む場合はCapに昇格） |

**判定3基準**: (1) §外部とのやりとりに列挙されるか? (2) 外部起点から直接起動可能か? (3) 安定契約を持つか?

#### IC-1〜IC-8

| ID | 原則名 | 記述 | 違反時の症状 |
|----|--------|------|------------|
| IC-1 | Adapter→Internal 一方向依存 | Adapterは Internal を呼べるが、Internal は Adapter を知らない | Internal が技術詳細に依存しテスト困難 |
| IC-2 | Adapter→Adapter 直接結合禁止 | 同一Cap内でもAdapter同士は直接呼び合わない。必ずInternal経由 | 変更連鎖、テスト不能 |
| IC-3 | Internal Pure 原則 | Internal module は外部依存 (HTTP/DB/FS/Clock) を持たない | Mock地獄、環境依存バグ |
| IC-4 | Contracts 層の義務 | Adapter-Internal 間の型定義は contracts/ に集約 | 型定義散在、変更波及 |
| IC-5 | Shared 昇格基準 | shared/ にビジネスロジックが入ったらCapに昇格 | shared/ 肥大化 |
| IC-6 | Cap-scoped状態管理 | UI state はCap単位でscope。cross-Cap state は明示的Adapter経由 | グローバルstate汚染 |
| IC-7 | Semantic Delta Test | テストは「何が変わったか」を検証。実装詳細に依存しない | リファクタリングでテスト全壊 |
| IC-8 | 可観測性の境界 | トレース/メトリクス/正規化エラーはAdapter境界で実施。Internalはpure | 監視コードがビジネスロジックに混入 |
| IC-9 | Adapter Registry pattern | native view 層から別 stack の component を呼び出す際は、 view 層に直接 component を埋めず、 mount 用 Adapter を 1 段挟む。 mount 点は registry (= runtime 設定 API 等の接続点) 経由で解決し、 view 層と component の責務を分離する | view 層と component が直結し、 stack 置換時に既存 view 層を改変せざるを得なくなる |

> **IC-9 アクセシビリティ規範 (= フォーカス管理 + ARIA、 動的 mount 時必須)**: 動的 mount は DOM 差替を伴うため screen reader / キーボード操作の文脈が壊れやすい。 mount Adapter は以下を必ず実装する:
>
> 1. **フォーカス遷移**: route 遷移後に新規 mount された component が主要操作対象 (= 主タイトル / 主要 form 先頭 input 等) を含む場合、 mount 完了時に該当要素へ `element.focus({ preventScroll: false })` で明示遷移する (= screen reader が新画面の文脈を読み上げる起点を確保)。 fallback UI (= ErrorFallback / LoadingFallback) 表示時も同様に focus を fallback root に当てる。
> 2. **ARIA live region**: 非同期で内容差替が発生する component (= Suspense fallback → 本体) は親要素に `aria-live="polite"` (= 通常更新) or `aria-live="assertive"` (= エラー等の緊急通知) を declared、 screen reader に動的変化を通知する。 LoadingFallback は `role="status"` + `aria-live="polite"` 既定。 ErrorFallback は `role="alert"` + `aria-live="assertive"` 既定 (= `@project/design-system` の components 層で named export として固定)。
> 3. **キーボード trap 回避**: modal / dialog 化された mount component は focus trap を実装 (= Tab / Shift+Tab で modal 内のみ循環 + Esc で閉じる)、 他要素に focus が逃げる事故を防ぐ。 trap 実装は `@project/design-system` の `FocusTrap` 共通 component に集約。
> 4. **disconnect 時の focus 復元**: unmount 時に focus が消失すると screen reader が文脈を失うため、 mount 直前に `document.activeElement` を保存し、 unmount 時に該当要素が DOM に残存していれば focus を戻す (= 残存しない場合は `document.body` に戻す)。

#### 物理配置（言語非依存パターン）

```
{cap_dir}/
├── adapters/          # Adapter: 外部接点
│   ├── inbound/       # 外部 → Cap
│   └── outbound/      # Cap → 外部
├── internal/          # Internal: ビジネスロジック
│   ├── domain/        # Aggregate / Entity / VO / Domain Event
│   ├── strategies/    # Strategy パターン（可変ルール）
│   └── policies/      # Policy パターン（共通ルール）
├── contracts/         # Adapter-Internal 間の型定義
└── scripts/           # Saga / Workflow
```

---

## §5: 設計プロセス（Layer別）

### L1: Strategy — 何を達成するか

**成果物**: `strategy/strategy.md`

**構成**:

```
§0 前提コンテキスト（5-15行。何の上に乗るか、既存正本、Phase境界、スコープ外）

§1 関連組織・アクター・システム（2階層 = 組織 → 配下の人間アクター + システム個別、業務ソース全網羅、Platform 全構造 = 各 PJ strategy.md §1 で declared、PJ scope 内の関連 service のみ subset 列挙 OK、全 ID 日本語化）

§2 ユーザー要求（UN）
  - BF（業務フロー）が親、UNが子の階層構造
  - BFごとのセクション（###）
    - BFタイトル = 「`actor_id` が〜する」形式（1アクター1アクション）
    - UNサブセクション（####）。1:1でも1:Nでもよい
      - **要求本文**（複数行。業務ルール・権限・任意/必須を具体的に記述）
      - **情報定義 (= コンテンツ要求)**: actor が扱う情報項目の構造化 declared (= **業務フローの step 単位 declared** = 入力 step に該当する UN で入力情報を、 出力 step に該当する UN で出力情報を declared、 **UN と情報定義は 1:1 ではない** = 入力系 / 出力系 / 入出力混在 / 情報定義なし いずれも自然発生、 §5 L1 §1 例外条項参照)。 **format 自由** (= 表 / bullet / 自由記述 / 列挙 いずれも OK、 grounded source で declared できる形式で記述、 表形式を強制しない)
        - **入力情報** (= 入力 step に該当する UN のみ): 入力形式 (= 画面 form / API / CSV import 等、 複数形式併記可) + **情報項目 (= grounded source で declared できる項目のみ)** + 属性 (= 必須/桁数/文字種別/デフォルト/規則/根拠、 **grounded source で明示できる場合のみ記入**、 不明 case は空欄 or **オープンイシュー化** (= §6 未決管理 3 系統 = DR §OQ / 計画文書 §OQ / GitHub Issue。 「PO 確認候補」 等の hedge declared は spec 本文に書かない = ハルシネーション扱い))
        - **出力情報** (= 出力 step に該当する UN のみ): 出力形式 (= 画面表示 (= list/detail) / 帳票 (PDF) / 通知 (= メール/SMS) / 連携データ (CSV/API レスポンス) 等、 複数形式併記可) + **情報項目 (= grounded source で declared できる項目のみ)** + 属性 (= 同上、 grounded のみ)
      - **責務境界**（このUNが扱うこと / 扱わないこと）
      - **出典**（任意。ただし出典の存在は確からしさを保証しない）

§3 成功条件（SC）
  - SCごとのセクション
    - 成功状態
    - 測定方法
    - 関連UN（タイトル併記）

§4 戦略原則・制約（SP）
  - SPごとのセクション
    - 原則
    - 根拠（Reference参照可）
    - 含意
    - 適用範囲
    - 反例

§5 用語集（UL。業務領域別グルーピング。§1 declared 済の組織 / 人間アクター / system は再記載禁止）

§6 Reference Index（表形式。1行要約+用途+リンク。 `docs/specs/strategy/reference/` 配下の業務ソース抜粋 / 競合サーチ / 既存実装ソース / 調査エビデンスを index 化、 元ファイル名維持・英語変換禁止）

§7 SLO（表形式）
```

**記述ルール**:
- §2はBF>UNの階層構造。BFが親（###）、UNが子（####）
- BFの粒度 = **1人のアクターが1つの業務目的を達成する単位**。複数アクターや複数目的を1つのBFに結合しない。BFが粗すぎると配下のUNの責務境界が曖昧になる。迷ったらBFを分割する
- BF:UNは1:1でも1:Nでもよい。ただしBFが適切な粒度に分解されていれば、自然と1:1に近づく
- BFタイトルは「`actor_id` が〜する」形式で1アクションを表現する。ステップセクションは不要
- UN要求本文は**複数行で業務ルールまで具体化**する。「誰ができるか」「任意か必須か」「条件・制約」を明記する
- **UN 情報定義 (= コンテンツ要求)**: **業務フローの step 単位で declared** = 入力 step に該当する UN で入力情報を、 出力 step に該当する UN で出力情報を declared (= **UN と情報定義は 1:1 ではない**、 入力系 UN / 出力系 UN / 入出力混在 UN / 情報定義なし UN いずれも自然に発生)。 **format 自由** (= 表 / bullet / 自由記述 / 列挙 いずれも OK、 grounded source で declared できる形式で記述、 表形式を強制しない)。 grounded source **3 区分** (= 法令公式 / 業界 declared (= 公開 doc 確認済) / 内部決定記述) で確実に declared できる項目のみ列挙 (= 推測・捏造禁止、 R-DPG-6 整合。 「PO 確認候補」 declared は禁止 = ハルシネーション扱い、 未決は §6 未決管理 3 系統 (= DR / Issue / オープンイシュー) で管理)。 下記 **§情報定義 declared 例外条項** 参照:
  - **入力情報** (= 入力 step に該当する UN のみ): 入力形式 (= 画面 form / API / CSV import 等、 複数形式併記可) + **情報項目 (= grounded source で declared できる項目のみ)**。 各項目の属性 (= 必須/桁数/文字種別/デフォルト/規則/根拠) は **grounded source 3 区分 (= 法令公式 / 業界 declared / 内部決定記述) で明示できる場合のみ記入**、 不明 case は空欄 or **オープンイシュー化** (= §6 未決管理 3 系統、 spec 本文に hedge declared を書かない = 推測・捏造・ハルシネーション禁止)。 L1 grain 制約遵守 = **logical 情報項目** declared OK、 **物理項目** (= DB 列名 / API field 名 / HTML input type) declared 禁止 (= L2 Cap §データ aggregate / L3 / L4 で具体化)
  - **出力情報** (= 出力 step に該当する UN のみ): 出力形式 (= 画面表示 (= list/detail) / 帳票 (PDF) / 通知 (= メール/SMS) / 連携データ (CSV/API レスポンス) 等、 複数形式併記可) + **情報項目 (= grounded source で declared できる項目のみ)**。 list/detail の場合はソート/フィルタ列も併記。 属性 grounded ルールは入力と同じ
  - **具体例**: UN-案件作成 (= 入力 step) → 入力情報のみ declared (= form 項目列挙 + 属性) / UN-案件詳細閲覧 (= 出力 step) → 出力情報のみ declared (= 画面表示項目 list / detail + ソート / フィルタ列) / UN-案件編集 (= 入出力混在 step) → 入力 + 出力両方 declared / UN-権限設定 (= 業務出力なし) → 入力のみ declared (= 出力「該当なし」明示も省略可)
- **§情報定義 declared 例外条項**: UN の性質 (= 業務フローのどの step に該当するか) によって入力情報定義 / 出力情報定義 の片方 or 両方が **該当しない** ことがある (= 例: 純粋な参照 / 閲覧系 UN は入力なし、 純粋な通知 / 出力主体 UN は入力なし、 設定変更などで業務出力を持たない UN は出力なし)。 **step 単位で該当する情報のみ declared** = 「該当なし」 / 「入力のみ」 / 「出力のみ」 / 「両方」 いずれも自然発生 (= UN と情報定義は 1:1 ではない)。 **無理やり情報項目を列挙してハルシネーション混入するくらいなら declared 省略 (= 「該当なし」 と明示、 明示自体も省略可) + 未決論点はオープンイシュー化 (= §6 未決管理 3 系統)** する。 §2c 概念対比表 / §2c L1 許容 / §5 strategy.md 構造 template / §5 記述ルール / §8 段階的制約 横断整合 = UN 性質次第で 入力 / 出力 / 両方 / なし 自然発生、 IN or OUT が業務上存在しない UN への強制ではない。 **表形式 ≠ 必須** (= 表 / bullet / 自由記述 / 列挙 いずれも OK、 grounded source で declared できる形式で記述)。 判定基準 = **grounded source 3 区分 (= 法令公式 / 業界 declared / 内部決定記述) で確実に declared できる項目があるか**、 なければ「該当なし」明示が正解 (= 推測・捏造禁止、 §8 段階的制約 + R-DPG-6 grounded fact only 整合)。 **PO 判断待ち項目は spec 本文に hedge declared (= 「PO 確認候補」 / TBD / 推測) せず、 §6 未決管理 3 系統 (= DR §OQ / 計画文書 §OQ / GitHub Issue) で別管理**
- UN責務境界は「扱うこと / 扱わないこと」を明記し、他UNとの重複を防止する
- 出典は記載してよい。ただし出典の存在は要求の確からしさを保証しない（旧設計資料等は構想段階の仮説にすぎない場合がある）
- L2 BPMはBFの詳細化。BFを逸脱してはならない
- **§1 関連組織・アクター・システム**: 2 階層構造で declared (= 階層 1 = 組織 / 階層 2 = 組織配下の人間アクター + システム個別)。 業務ソース・調査・既存 declared を **全網羅** (= 漏れ禁止、 grep audit 対象)。 **platform system は個別明記必須** (= Platform 全構造 = 各 PJ strategy.md §1 で declared SSoT 参照、 一括「プラットフォームシステム」表記禁止、 各 PJ scope 内の関連 service のみ subset 列挙 OK = **PJ scope 外 service は省略 OK** = 全 service 列挙不要 = reference block は完全 catalog だが L1 §1 は PJ 関連 service のみ抽出、 関係ない service を機械的に全列挙 = ハルシネーション源 candidate)。 **全 ID 日本語化必須** (= プロダクト固有名詞 = freee / マネーフォワード / 弥生 / 勘定奉行 / TKC / Platform service 名 等のみ例外)。 標準 format = `### §1-A 顧客企業` / `### §1-B 取引先組織` / `### §1-C 顧客金融機関 (上位 tenant)` / `### §1-D プラットフォーム` / `### §1-E 外部システム提供企業`、 配下に bullet で人間アクター (= 営業担当 / 購買担当 / 経理担当 / 案件責任者 / 案件担当者 等、 人間明示) + システム個別 (= ModuleB (system) / EL (system) 等、 system 明示)

**参考: Platform 全構造 (= 全 PJ L1 §1 コピペ用 reference block)**

全 PJ L1 §1 のなかのプラットフォームのシステム で記載、 **各 PJ scope 内の関連 service のみ抽出して subset 列挙** (= **PJ scope 外 service は省略 OK** = 全 service 列挙不要、 関係ない service を機械的に全列挙 = scope 外 service の責務記述で grounded source なし状態が発生 = ハルシネーション源 candidate)。 下記 reference block は全 service catalog reference (= コピペ用)、 各 PJ で関連 service のみ pick して L1 §1-D に記載する

### Platform（参考例）

#### 共通基盤

| # | サービス | 略称 | 責務 |
|:-:|---------|:----:|------|
| 1 | 設定管理 | config | プロジェクト設定・環境変数管理。 |
| 2 | ワークフロー基盤 | n8n | N8Nによるワークフロー定義・実行・スケジューリング。 |
| 3 | 外部API連携 | integrations | 外部サービスAPI中継（TikTok API / Shopee API等）。 |
| 4 | 通知基盤 | notifications | Telegram通知・エラーアラート配信。 |

#### コンテンツ生成

| # | サービス | 略称 | 責務 |
|:-:|---------|:----:|------|
| 1 | スクリプト生成 | script-gen | AI（Groq/Gemini）によるビデオスクリプト生成。 |
| 2 | 動画レンダリング | video-render | FFmpeg + edge-ttsによるショート動画生成。 |
| 3 | コンテンツ投稿 | publish | TikTok Content Posting API v2による自動投稿。 |

#### データ管理

| # | サービス | 略称 | 責務 |
|:-:|---------|:----:|------|
| 1 | 商品同期 | shopee-sync | Shopee Affiliate商品情報の定期同期・優先度付け。 |
| 2 | パフォーマンス分析 | analytics | 投稿パフォーマンス追跡・レポート生成。 |
| 3 | ダッシュボード | dashboard | Streamlitによる可視化・運用管理UI。 |

### 機能制御モデル（参考例）

| 層 | 制御内容 | 管理主体 |
|---|---|---|
| 第1層 | サービス on/off | Platform（N8N workflow有効/無効） |
| 第2層 | 機能単位 on/off | 各サービス（config） |
| 第3層 | 外部連携 on/off | 各サービス（API key有無） |

- §2 BF / UN で参照する actor / 組織 / system は §1 declared list 内のみ。 未 declared の actor 使用禁止 (= §2c L1 禁止)
- §5 UL は業務領域別用語のみ (= 請求書 / 与信 / 案件 等の業務概念)。 §1 declared 済の組織 / 人間アクター / system は §5 UL に再記載しない (= §2c L1 禁止、 SSoT 違反)
- SP/SCは1件1セクション形式。表は索引・一覧性が必要なもの（§1/§6 Ref/§7 SLO）のみ
- ID参照は「ID + タイトル」併記必須。`UN-1(申込進捗確認)` 形式
- SPのIDプレフィックス（SPI/SPD/SPC）は使わない。「適用範囲」で区別する
- L1禁止事項（§2c）を遵守すること

**品質ゲート**: → CP-1 承認

### L2: Requirements — 何ができるか

**成果物**: `crc.md` / `bpm/{scenario}.d2` / `capabilities.md` / `capability-landscape.d2`

#### Phase A: 業務フロー構造化

1. 業務ソースからBPMを書く（Cap名なし）
2. activity注記に入力/出力/外部連携先/出典を記入
3. CRC再点検

**BPMの構造規範**:
- **Pool = 1 組織** (= L1 §1 階層 1 = 組織 を参照): 1 Pool は 1 組織を表す。組織種別ごとに別 Pool に分離する
  - 顧客企業 Pool（= §1-A 顧客企業、配下の人間アクター = Lane）
  - 取引先組織 Pool（= §1-B 取引先組織、配下の人間アクター = Lane）
  - 顧客金融機関 Pool（= §1-C 顧客金融機関、上位 tenant）
  - プラットフォーム Pool（= §1-D プラットフォーム、配下の system 個別 = Lane = Platform 全構造から **PJ scope 内の関連 service のみ個別 Lane で明示**、一括「プラットフォームシステム」 Lane 禁止、 各 PJ strategy.md §1 で declared SSoT 参照）
  - 外部システム提供企業 Pool（= §1-E 外部システム提供企業、配下の system 個別 = Lane = freee / マネーフォワード / 弥生 / 勘定奉行 / TKC 等を個別 Lane で明示）
- **Lane = 組織内 role / system 個別** (= L1 §1 階層 2 = 組織配下の人間アクター + システム個別 を参照): 同 Pool 内の lane は組織内の role / 部門 (= 営業担当 / 経理担当 / 案件責任者 等、 日本語表記) で分離。 プラットフォーム Pool 内は Platform 全構造から PJ scope 内の関連 service を個別 Lane で明示 (= 各 PJ strategy.md §1 で declared SSoT 参照)
- **Cap-process Lane は使わない**: Cap は §② IF で表現、Lane では表現しない

**activity 規範 (BPMN 標準準拠)**:

activity は task（atomic action）/ event（業務的節目）/ gateway（分岐）の 3 種に分類する。

**task (= atomic activity、 1 actor 1 action)**:
- user task = 1 人間 actor の 1 atomic action（1 入力 / 1 ボタン押下 / 1 確認 / 1 判断）
- system task = 1 システムの 1 atomic 処理（1 保存 / 1 通知 / 1 外部連携 / 1 自動算出）
- L1 §UN「Step N」 declared = 各 Step = 別 task
- 「入力」 と「送信ボタン押下」 = 別 task（= 異なる atomic action）
- system「保存」 と「通知」 = 別 task（= 通知は業務独立意味あり）
- 内部技術処理（変換 / 整形 / ログ出力 / キュー投入）= task 化禁止（親 task 内包）

**event (= 業務的節目、 BPMN 標準厳密)**:
- start event（shape: oval）= scenario の最初の trigger（通常 user 操作開始）
- end event（shape: oval）= scenario の最終結果（通常 外部連携完了 / 完了通知）
- intermediate event = 外部 trigger 専用（timer / message / error / signal）
- **「中間節目」（= 承認結果確定 / 全員承認完了 等）は system task で表現**、 event 化禁止

**gateway (= decision、 入れる/省くルール)**:
1. L1 §UN 内に判断マーカー declared がある場合のみ gateway 化
2. 判断マーカー = 「判断」「分岐」「条件」「path」「~の場合」「~なら」「~時」「~or~」 等の語句
3. マーカー個数 = gateway 個数（1 マーカー = 1 gateway、 連鎖マーカー = 連鎖 gateway）
4. L1 declared 外 = gateway 化禁止（= hallucination 防止）

**hallucination vs L1→L2 詳細化の判定基準**:

L1 §UN を L2 BPM に詳細化する際、 activity / gateway 追加が「詳細化」 か「hallucination」 かを判定する:

- **詳細化 OK**: L1 declared 語句から自然導出可能 = 業務理解上明白
  - 例: L1「業務承認実行」 → L2「承認 / 差戻し 判断 (gateway)」=「承認」 という業務概念に「承認する / しない」 の二択は自明
  - 例: L1「自動消込ルール一致時、 候補表示 / 完全自動 mode」 → L2「ルール一致判定 → mode 判定」= L1 で順序明示
- **hallucination NG**: L1 declared なし + 業務理解上自明でない = AI 想像
  - 例: L1「業務作成」 のみ → L2「業務種別の頻度判定」= L1 declared なし、 業務理解上自明でない

判定方法: 「これは L1 のどの語句から導出した?」 に答えられる = 詳細化、 答えられない = hallucination。

**activity 種別 class**:
- `start_end`（start / end event）/ `decision`（gateway）/ `parallel`（並列 gateway）/ 通常 rectangle（task）

**activity 注記（D2 source 内 tooltip inline で記録）**:
- 入力（業務オブジェクト名）/ 出力（業務オブジェクト名）/ 外部連携先 / 出典 / [Cap名]（Cap 導出後に追記）

**L2 禁止事項（§2c）を遵守**: CSS、 Atomic Design、 コンポーネント名、 ライブラリ名、 SQL、 HTML input type は書かない。

**edge 規範 (BPMN 標準準拠)**:
- **sequence flow** = Pool 内 edge（solid line、 normal flow）
- **message flow** = Pool 跨ぎ edge（dashed line + 矢印 styling 強制、 組織間通信）
- **backward edge** = sequence flow + feedback label（= cycle / 差戻し loop）
- edge label = 操作意図（例: 「次」「承認必須」「差戻し (feedback)」「送付 (message flow)」「ACL 連携 (message flow)」）

**配置規範（描画品質）**:
- 全 Pool 統一 width: 全 Pool が同じ width を持つ（最大 content width に揃える）
- Pool 縦 stack 間隔 = 0: Pool は密着して縦に並ぶ（隙間なし）
- 全 Pool 横断 column 整列: 同 phase（time level）の activity は Pool を横断して縦軸で揃う
- **全 activity X 軸 unique (= scenario 全体、 v15 scope 明示)**: 同 phase + 同 Pool + 同 lane 関係なく、 scenario 内全 activity が異なる X 座標を持つ (= **全 lane / 全 Pool 横断 staircase pattern**、 line 重複防止)

**粒度規範 (= L1→L2 BPM 変換、 task / event / gateway 統一規範、 v15 訂正)**:

| Rule | 内容 |
|---|---|
| **R1 task 原子性** | 1 actor 1 atomic action (= L1 §UN 各 Step を別 task 化) |
| **R2 event** | start/end のみ (= 中間節目 = system task で表現、 intermediate event は外部 trigger 専用) |
| **R3 gateway** | L1 declared 「判断/分岐/path/条件」 マーカー **1:1** (= L1 declared 外の gateway 化禁止)、 **System 自動判定は task + OK/NG 分岐** (= 人間判断のみ Gateway) |
| **R4 hallucination 防止** | L1 declared から自然導出可能か判定 (= 「L1 のどの語句から?」 に答えられる/答えられない) |
| ~~R5~~ | **欠番** (= Rule ID の reuse 禁止) |
| **R6 状態遷移明示** | L1 状態語彙 (= 確認中/確認済/差戻し 等) を system task で必ず明示 |
| **R7 通知 task 必須** | L1 「通知/依頼」 declared → system→user 通知 task で明示 |
| **R8 画面 open 明示** | user task 「起動/遷移/モーダル」 → 直後 system「open/render」 task |
| **R9 NG 終端 user 可視化** | System 判定 NG outgoing → user 可視 node (= 通知/戻る path) で終端 |
| **R10 全組織 Pool + 全 Lane 網羅 (v15.1 新規、§1 cascade)** | **strategy §1 declared の全組織 (= 顧客企業 / 取引先組織 / 顧客金融機関 / プラットフォーム / 外部システム提供企業) を BPM 内 Pool として網羅必須 + 各 Pool 配下の全 Lane (= §1 階層 2 = 人間アクター + system 個別) を網羅必須**。 組織 / Lane 漏れがあれば BPM 不完全 = 規範違反。 プラットフォーム Pool 配下は Platform 全構造から PJ scope 内の関連 service を Lane で個別明示 (= 一括「プラットフォームシステム」 Lane 禁止、 各 PJ strategy.md §1 で declared SSoT 参照)。 Pool / Lane mapping = §1 階層 1 / 階層 2 を参照 |

**配線規範 (v15.21 最終版、 drawio 純正仕様完全準拠)**:

| Rule | 内容 |
|---|---|
| **POR 出入口極性** | src/tgt の lane 関係で line 出入辺を一意決定: **同 lane 横並び → src 右辺 / tgt 左辺** / **lane 跨ぎ src 上 lane → src 下辺 / tgt 上辺** / **lane 跨ぎ src 下 lane → src 上辺 / tgt 下辺** / **backward = 上 rail (= src 上辺 / tgt 下辺、 全 shape 共通)** |
| **FAN 分岐分散** | 辺あたりの出辺+入辺 合計 N → **1/(N+1), 2/(N+1), ..., N/(N+1) 位置で配置** + 順序 = src/tgt 相手方位置に近い順 sort。 **shape 種別 (= 矩形 / 菱形 / 円 / 等) に関わらず 常に 外周の長方形 (= bounding box) base で計算** (= 全 shape 同 logic) |
| **drawio edgeStyle 規範 (v15.21)** | drawio 純正 `elbowEdgeStyle` を face 種別で適用: **lane 内 (= 左右 face) → 「垂直」 = `edgeStyle=elbowEdgeStyle`** (= 中央 vertical segment) / **lane 跨ぎ (= 上下 face) → 「水平」 = `edgeStyle=elbowEdgeStyle;elbow=vertical`** (= 中央 horizontal segment) / **mixed face fallback → `edgeStyle=orthogonalEdgeStyle`** |
| **接点直角必須** | shape 種別関わらず 常に **外周の長方形 (= bounding box) に対して直角接続** (= 90 度入射、 src/tgt 辺と並行な segment 撲滅) |
| **perimeter snap 無効化** | edge 個別: `exitPerimeter=0;entryPerimeter=0;` declared / shape 個別: `perimeter=rectanglePerimeter` (= 菱形/円でも bbox edge 扱い) |
| **「途中点」 mode 排除** | mxfile に `<Array as="points">` declared **禁止** (= drawio「途中点」 mode 強制で edgeStyle 設定が override される)。 path 中間は drawio に **完全委譲** = user 編集時も自動 routing |
| **backward 規範** | scenario 上 rail 経由 (= src 上辺 / tgt 下辺)、 矩形 / 菱形 共通 (= shape 種別特殊扱いなし) |

**drawio 純正 Pool/Lane 規範 (v15.19+)**:

drawio 純正「Add/Remove/Reorder Lane」 menu 機能を有効化するため Pool/Lane mxfile XML 構造遵守:
- **Pool style**: `swimlane;childLayout=stackLayout;horizontalStack=0;resizeParent=1;resizeParentMax=0;horizontal=0;startSize=20;collapsible=0;`
- **Lane style**: `swimlane;horizontal=0;startSize=20;` (= `childLayout` なし、 Pool 側で stack 制御)
- **parent 関係**: Pool `parent="1"` (= root) / Lane `parent="<Pool ID>"` (= 純正 nested) / activity `parent="<Lane ID>"`

**手動描画でも再現可能**: 本規範は drawio / diagrams.net 等の手動配置でも遵守する。`d2-swimlane-to-drawio` Adapter（Cap-Tooling）は本規範 (= R1-R4 + R6-R10 粒度規範 + POR/FAN/edgeStyle/接点直角/perimeter snap 無効化/「途中点」排除/Pool/Lane 純正 配線規範) を **自動適用する tool 実装** (`d2_swimlane_routing.py` + `d2_swimlane_post_process.py` + `d2_parse_emit.py` Internal Modules、 v15.21 最終版)。 tool 不在環境では手動で本規範を適用する（template `requirements/bpm-scenario.d2.template` 参照）。

**BPMと§2 BFの整合**: BPMの主要ステップ変更は§2 BF業務フロー骨格の再承認（CP-1差し戻し）を必須とする。BPMは§2 BFの詳細化であり、骨格を逸脱してはならない。BPMシナリオとBFの対応関係を明示すること。

**品質ゲート**: → CP-1.5 業務フロー承認

#### Phase B: Cap導出と定義

1. BPMの入力/出力からデータ正本を識別
2. 変更理由でグルーピング → Cap候補
3. capabilities.md作成（1ファイル全Cap）
4. BPMにCap名を追記
5. capability-landscape作成

**capabilities.mdの構造**:

各Capを以下の構造で記述する。1ファイルに全Cap。索引は置かない。末尾にアウトプット一覧付録。

```
## {Cap名}

### 責務
（1行。このCapが何をするか）

### 境界
（隣のCapとの違い。何をしないか）

### データ
（Aggregate名は業務用語が正本。英語名はL5実装時に§ULから導出）

#### 主要Aggregate
**{Aggregate名}**
- 属性: ...
- 出典: ...

#### ライフサイクル（状態遷移表。正本）
| 状態 | 遷移条件 | 遷移先 | 出典 |
|---|---|---|---|

（図は表から導出するビュー。表が正本）

#### 権限（権限マトリクス。正本）
| 操作 | {アクター1} | {アクター2} | ... | 出典 |
|---|---|---|---|---|

### 出すもの
- 画面: ...
- 帳票: ...
- 通知: ...
- 外部出力: ...

### ルール
（業務判定・計算ロジック。共通/可変の区別）

### 設定
（Config駆動で切り替えるパラメータ）

### 品質
（品質特性。SLO参照）
```

**Aggregate命名**: 業務用語が正本。capabilities.mdには日本語名のみ。英語名はL5実装時に§ULから導出する。出典必須。

**ライフサイクル**: 状態遷移表が正本。図（d2/mermaid）は表から導出するビュー。表は漏れ検出・出典記載に強い。

**コンテンツ要求の流れ**: BPM activity注記（一次情報）→ Cap §データ（正本として消化）→ L3 ui/{screen}.md（画面用途に具体化）

**3成果物の問いの分担**:

| 問い | 答える成果物 |
|---|---|
| いつ・誰が・何をするか・どんなデータが動くか・どのCapか | BPM |
| なぜそのCap境界か・正本データ・ライフサイクル・権限 | capabilities.md |
| Cap間の連携方式 | capability-landscape.d2 |

**品質ゲート**: → CP-2 承認

#### Phase C: 整合性確認

1. ランドスケープ整合チェック
2. CRC全件 × 全Cap Parnas再評価
3. CP-2 承認

**Cap粒度検出基準（SUSPECT判定）**:
1. §データが他Capの§データと重複 → 正本所有権の疑義
2. §設定が0件 → 変更吸収点なし、Cap分割の意味が薄い
3. Parnas評価でS率が50%超 → 境界が変更を隠蔽できていない
4. BPMで単独activityにしか登場しない → 他Capに統合可能

#### Phase D: 画面モック（体験検証・顧客レビュー）

**目的**: 文字（L1/L2）だけでは、体験全般に対する**機能の不足（定義そのものの欠落）**を人間が想像しきれない。全画面を動く形にして体験・顧客レビューし、cap/bpm/strategy に欠落を feedback する。L2 の確からしさを上げる instrument であり、本番 UI の種でもある。

**原典**: Google Design Sprint（実装投資の前にプロトタイプで検証）/ Lean UX・Design Thinking（学ぶための prototype）/ Atomic Design, Brad Frost（共有部品を atoms から組む方法論）/ Walking Skeleton（薄い end-to-end を先に）/ Presentation Model, Fowler（view-model seam）。

**Input**: L1 strategy / L2 bpm・capabilities（§データ→view-model 型、§出すもの→全画面 inventory）/ `strategy/reference/` 配下 (= 業務ソース抜粋 / 競合サーチ / 既存実装ソース / 調査エビデンス、 旧 groundwork) / `requirements/reference/` 配下 (= L2 画面モックの UI デザイン参考、 業界 SaaS の画面パターン / UI キャプチャ / デザイン調査エビデンス、 dir 内 README.md で index 化)。
**Output（消化先）**: → L1/L2（発見した機能不足を strategy/cap/bpm に反映）+ seed → L3 ui/{screen}.md。

##### 2 種類の「過不足」を別の道具で見る

| 種類 | 何を見るか | 道具 | 性質 |
|---|---|---|---|
| A. 定義内の不整合 | cap output に画面があるか／孤児画面がないか | `screen-coverage-matrix.md`（紙） | 検証（closed-world）。pixel 不要 |
| B. 定義そのものの不足 | 体験して初めて気づく「これが要る」 | **全画面の画面モック** | 反証（open-world）。文字には天井がある |

coverage の ok/ng（全画面の過不足）は **matrix** が出す。**mock は B を炙り出して matrix/cap に書き足す**。matrix=台帳・checklist、mock=それを顧客と歩いて反証。

##### coverage は full、fidelity は段階（量産負荷の制御軸）

「画面を減らす」のではなく「最初は低 fidelity で全画面 → 検証済みだけ高 fidelity」。低 fi の breadth で B を出し、検証済み画面だけ高 fi 化して本番に育てる。捨てるのは**モックデータ層だけ**。

##### Mock → Demo → Real（同一 UI 資産を seam で繋ぐ）

| | データ | 接続 | UI | Route |
|---|---|---|---|---|
| **Mock** | fixture | なし（単画面） | 本実装 | 本実装 |
| **Demo（flow prototype）** | fixture + in-memory（@mswjs/data 等） | route 接続（ページ間遷移・stateful） | そのまま | そのまま |
| **Real（L5）** | 本 API/DB | そのまま | そのまま | そのまま |

- **画面コンポーネントに環境分岐を入れない。差し替えてよいのは Data Provider と Persistence のみ**（seam = view-model。cap Aggregate 由来で L2 で確定、adapter 粒度=L3 に依存しないので早期に安定）。接続点 (= seam) 一覧: (1) テナント・機能切替の接続点 = runtime 設定 API、(2) 共通 component の接続点 = `@project/design-system`、(3) mount Adapter = native view → 別 stack component の接続点 (IC-9)。
- **Route tree は Mock 段階から固定**。Demo で route 接続すれば「画面単体の動き → ページ間遷移」が L2 のまま繋がる（別層は不要）。
- **共有 `@project/design-system`（デザイントークン + 共有 component の単一 package、npm publish 配信）を基盤に組む**。mock で bottom-up 抽出した部品も同 package の components 層へ集約し PJ 毎の再発明を避ける（B の発見で増えた画面も共有トークンで組む）。マルチ channel 適用（native app wrap / 他社埋込 widget / SDK packaging）はラッパーとして既存構成から分離して追加する（**切り出し最小原則**。ラッパーが各アプリのデプロイ単位に依存する場合はデプロイ単位別に分割。widget 実装方式は PoC で確定、wrapper 候補 = `@lit/react` 等）。
- **mock 技術選定基準 (= 将来の要件適用をすべて満たすこと)**: mock で作った画面が **Web / スマホアプリ (Capacitor wrap) / スマホネイティブ / SDK / widget** の将来適用にそのまま繋がる技術でなければならない。仕様:
  1. **画面は `@project/design-system` の component (pure React 18 + Tailwind + tokens) のみで組む** (= 不足部品は先に design-system へ追加してから使う。mock 内に部品を直書きしない)
  2. **tokens は platform 中立 (数値ベース)** — スマホネイティブ採用時も tokens + view-model を持ち越せる
  3. **データは view-model seam の背後で MSW / @mswjs/data** (画面 component に環境分岐を入れない)
  4. **mock = standalone-capable な web area で作る** (= `web-spa/`、自前 root mount + client router (react-router) + 自前 build (Vite))。host app の routing/mount に溶接しない (= 溶接すると Capacitor / SDK への切り出しが重くなる)。**本番化 = データ層の差し替えのみで、何も捨てない** (screen component / route tree / view model / UI 構造 / build 設定を変えない)
- **view-model seam の実装 = 3 層分離 (Pure / データ取得 / ビュー)**: 画面が data source (fixture / 実 API) を直接掴まないため、画面と data の間に **データ取得層**を 1 枚挟む。これが seam の実体で、本番差し替え時に触るのはこの層だけ:

  | 層 | 配置 | 中身 | 本番差し替え |
  |---|---|---|---|
  | **Pure** | `models/{domain}/` | 型 / 検証 / 計算 / 状態マッピング (framework 非依存の純関数) | 変えない |
  | **データ取得** | `hooks/{domain}/` | `useXxx()` server-state hook。**返り値 `{ data, isLoading, error }` は全段階で不変** | **★ここだけ** (Mock = fixture / Demo = `@mswjs/data` / 本番 = 実 API) |
  | **ビュー** | screen component | 共有部品で組む。data 取得 hook を呼ぶだけ (data source を直接 import しない) | 変えない |

  - **画面の data source 直接 import は禁止** (= カプセル化の漏れ。差し替え点が画面に散ると本番化で全画面改変が必要になる)。fixture / axios 直叩きは必ず hook の内側に隠す
  - **hook の粒度 = 1 file = 1 hook = 1 concern (= 一貫した 1 つの読み取り or 書き込みの塊)**。粒度ルールは下記:
    - **画面単位ではない** (= 「1 画面 1 hook」は誤り)。1 つの画面が複数 concern hook を使ってよい (例: 一覧取得 / 選択状態 / 検索 / 並べ替え は別 concern = 別 hook)
    - **DB テーブル単位でもない**。hook は entity でなく concern (取得 / 更新 / 検証 / 選択状態 等) で切る
    - **1 hook に複数 concern を詰めない** (取得 + 更新 + 別 entity 取得 を 1 hook に持たせる god-hook は禁止 = 単一責任違反で依存配列の整合性確保が困難になる)
    - file は `use{Concern}.ts` で 1 hook を 1:1 で包み、`hooks/{domain}/` 配下に集約。共通返り値型 (`{ data, isLoading, error }`) は `hooks/{domain}/types.ts` 等に切り出す
  - **hook は mount cleanup を持つ** (`mountedRef` 等で unmount 後の setState を防ぐ。将来 async fetch 化時の race / leak を構造的に排除)
  5. **スマホ適用**: マルチ channel への適用はラッパー層 (mobile/ = Capacitor wrap 設定のみ) で行う (= mock を別置きにする理由にしない)
  6. **SDK / widget 適用性**: component が副作用のない pure React であることを Storybook + publint で保証
- 本番 bundle への mock 層 (MSW / fixtures) 混入は CI hard block (L5 昇格 gate)。配置の単一参照点 = artifact-placement-guide。
- **変えないもの**: screen component / route tree / view model shape / UI構造。

##### ハルシネーション防止（3層）

1. **型で防ぐ**: cap §データ → view-model 型を生成。型にない項目はコンパイルエラー。fixture も型付き。
2. **テストで防ぐ**: 情報定義の全項目がモックに存在するか／情報定義にない要素が無いかの自動テスト。
3. **diff で防ぐ**: モック更新 PR で「情報定義にない要素の追加」を CI 検出。

##### 顧客レビュー

Vercel デプロイ（push→固有 URL）で**レビュー往復**。顧客も B は全体を触らないと言えないため、demo は全画面 navigable で踏ませる。環境構築・デプロイ手順は **`mock-prototype-guide.md`**（設計 how-to ではなく環境/起動/デプロイのみ）。

**品質ゲート**: → CP-2.5b 画面モックレビュー（PO/顧客が操作して業務成立・機能過不足を確認）。**L5 昇格 gate**: 本番 bundle にモックデータ層が混入していないこと（CI hard block）。

### L3: Architecture — どう構造化するか

**成果物**: ui/{screen}.md / capabilities.md §L3具体仕様 / component-landscape.d2 / component-diagrams/{cap}.d2 / container-diagram.d2 / api/cap/{adapter}.v{N}.yaml / parnas-evaluation-matrix.md

#### 画面設計（ui/{screen}.md）

**2段階で埋める**（成果物は1ファイル。書く順番が2段階）:

**第1段階（情報定義）**:
```
## 画面の責務（1行）

## 情報定義
（情報グループは画面上の表示順に並べる。この並び順がモックのレイアウト骨格になる）

**{情報グループ名}**（{Cap名} / {Aggregate名}）
- {属性名} — 表示/編集/遷移操作
- [操作] {操作名}

## 主要操作
- {操作1}
- {操作2}
```

情報グループの並び順は、画面上の配置の骨格を示す。詳細なレイアウト（カラム分割、タブ構成等）はモック段階で決定する。

**品質ゲート**: → CP-2.5a 情報定義レビュー（POが確認: 必要な情報は揃っているか、不要な情報はないか、情報のまとまりが業務に合っているか）

**順序**: CP-2.5a承認 → モック作成 → CP-2.5b承認 → 第2段階（詳細化）

**第2段階（詳細化。CP-2.5b承認後に埋める）**:
```
## モック検証記録
- [ ] 情報定義の全情報グループが表示できる
- [ ] 主要操作が成立する
- [ ] ライフサイクル遷移が再現できる
- [ ] 権限制御が再現できる
- [ ] 情報定義にない要素を追加していない

## 画面項目定義
| 項目 | 型 | 必須 | バリデーション | 出典 |
|---|---|---|---|---|

## 画面遷移
（前画面 → 本画面 → 次画面）

## 受入基準
（Gherkin形式）
```

**品質ゲート**: → CP-2.5b モックレビュー（POがモックを操作して確認）

**Atomic DesignはL3では使わない**。Organism/Molecule/Atomの分類はL4 UI実装設計で行う（実体は L2 画面モックで共有トークンを基盤に bottom-up 抽出し、`@project/design-system` へ集約していく）。

#### Cap L3具体仕様

capabilities.md内の各Capセクションに、L3具体仕様を追記する。L2抽象レベルの記述と同一セクション内で抽象→具体を一気通貫で記述する。

**cross-Cap横軸成果物の作成手順**（全Cap L3が出揃って初めて作成可能）:

| 横軸成果物 | Input | Output | 整合確認 |
|---|---|---|---|
| Component Landscape | 全Cap §外部とのやりとり | Adapter粒度の全体図 | 全Cap Adapterが漏れなく配置されているか |
| Container図 | Component Landscape + Cap §品質 | デプロイ単位図 | スケーリング要件とプロセス分割が整合するか |
| API定義 | Cap §外部とのやりとり | OpenAPI/AsyncAPI | Cap間のAPI/Event名・型・バージョンが一致するか |

**品質ゲート**: → CP-3 承認

### L4: Implementation Design — どう実装するか

**成果物**: セキュリティ・監視設計 / UI実装設計 / Repository IF設計 / ディレクトリ構造 / インフラ設計

L3の成果物を入力とし、実装方針を横断的に定義する。個別画面・個別APIの実装は書かない（それはL5）。

**UI実装設計にAtomic Designを適用**: L3 ui/{screen}.mdの情報定義をOrganism/Molecule/Atomに分解する。L2 画面モックで bottom-up 抽出した component を **共有 `@project/design-system`（現状トークン層、component 層は集約構築中）** へ集約し、PJ 毎の再発明を避ける（原典: Atomic Design, Brad Frost）。

### L5: Implementation — 本番品質コード

L2 画面モックの screen component を view-model seam 越しに昇格する（**本番 web 画面の正本 = `web-spa/`** = mock の SPA がそのまま本番。data 層だけ差し替え）。MSW/@mswjs/data（モックデータ層）→ 本 Repository / 実 API に差し替え。**変えないもの**: screen component / route tree / view model shape / UI構造。**昇格 gate**: 本番 bundle にモックデータ層（MSW / @mswjs/data / fixtures）が混入していないことを CI で hard block。

---

## §6: ガバナンス (= 意思決定 + 未決管理)

### 本 § の責務 (= 意思決定 + 未決管理 の 2 軸)

ガバナンスは **2 軸** で構成する。 **後回し課題 (= 業務協議待ち / 外部依存 / 長期 backlog) は DR ではなく Issue / オープンイシュー (= OQ) で管理する** (= DR の役割と混同しない):

- **意思決定** = DR (= 選択肢 / 調査結果 / 議論記録 → 確定後の決定根拠) で記録 (= 下記 §DR scope / §DR template / §DR ガバナンス)
- **未決管理** = DR (意思決定後) / Issue (後回し課題追跡) / オープンイシュー (設計途上の OQ) の 3 系統で管理 (= 下記 §未決管理 3 系統)

### 未決管理 3 系統 (= 全層 L1〜L5 横断)

設計プロセス全層 (L1〜L5) で発生する **未決論点** (= grounded source で declared できない情報、 PO 判断待ち、 業務協議待ち、 設計分岐) は以下 3 系統で管理する。 **spec 本文に hedge declared (= 「PO 確認候補」 / TBD / 推測 / 「declared なし」 / 「Phase 1 で grounded 化」) を残すことは禁止 = ハルシネーション扱い**:

| 系統 | 用途 | location | trigger |
|---|---|---|---|
| **DR (Decision Record)** | **意思決定プロセスの SSoT** (= 選択肢 / 調査結果 / 議論 / trade-off 比較 → 確定後の決定根拠記録) | `docs/decision-records/{N}/` | 意思決定 (= 選択肢検討 / 議論 / 確定) 時 |
| **GitHub Issue** | **後回し課題 / 課題追跡** (= 業務協議待ち / 外部依存 / 長期 backlog、 **DR ではない**) | GitHub Issues | 後回し課題発見時 |
| **オープンイシュー (= Open Questions / OQ)** | 設計途上 / DR / 計画内の未決論点 (= **DR ではない**) | DR `§ Open Questions` / 計画文書 `§ OQ` | 設計中に未決論点発生時 |

### 全層共通原則 (L1〜L5)

1. **未決論点はハルシネーション禁止** = 推測値 / 「PO 確認候補」 declared / 「declared なし」 defer / 「Phase 1 で grounded 化」 defer は **R-DPG-6 違反** (撤回対象)
2. **未決論点発生時** = 3 系統いずれかで管理:
   - **意思決定 (= 選択肢検討 / 議論 / 確定)** → DR 起票 (= 選択肢 / 調査 / 議論 / 確定根拠を記録)
   - **後回し課題 / 課題追跡** → GitHub Issue 起票 (= **DR ではない**)
   - **設計途上の未決論点** → オープンイシュー化 (= 直近 DR / 計画文書の §OQ section、 **DR ではない**)
3. **意思決定後** = SSoT (= 該当層 spec) に **確定値のみ declared**、 経緯は DR / commit message / PR description で trace
4. **spec 本文内に決定経緯を非記載** = 改訂経緯 meta コメント (= 「2026-06-XX user 指示」 「同 UN 内整合」 「PR #N 改訂時」 等) 禁止、 経緯は DR
5. **PO 確認は対話型優先** = offline 質問票 (= CSV / 質問書) を作る前に chat で direct ヒアリング

### grounded source 3 区分 (= §8 規範統一、 spec 記入可)

- **法令公式** (= 公式 doc URL)
- **業界 declared** (= 公開 doc 確認済)
- **内部決定記述** (= 業務ヒアリング / PJ 内部 declared 記録、 `strategy/reference/` 配下。 顧客露出 NG な内部記述として明示分離)

> 「PO 確認候補」 declared は**禁止** (= ハルシネーション扱い、 spec 本文への hedge 混入温床)。 PO 判断待ち項目は **§6 未決管理 3 系統** で別管理。

### DR scope

| 判断の種類 | 必要モデル数 | 例 |
|---|---|---|
| Cap境界変更 | 3モデル | Cap統合・分割 |
| Aggregate再編 | 2モデル | 正本所有権の移動 |
| L4実装設計 | 2モデル | セキュリティ設計 |
| PJ固有成果物追加 | 1モデル（PO判断） | field-mapping追加 |

**独立性の定義**: 各モデルは他モデルの出力を見ずに独立して回答。同一promptで並列実行が原則。

**記録フォーマット**: `docs/decision-records/{N}/review/{round}-{model}.md` に配置。必須項目: model名/version、prompt要約、verdict（approve/revise/reject）、主要concerns、推奨事項。

### DR template §Open Questions section 必須化

DR template (`docs/manual/templates/`) には **§Open Questions section を必須化**:
- 各 OQ に **ID / 論点 / 候補案 / 決定依存関係 / resolve trigger (= PO 対話 / 業界 declared 調査 / 別 DR 採択)** を declared
- proposed → accepted 移行前に **全 OQ resolve 必須** (defer は理由 + follow-up link 必須)

計画文書 template にも **§OQ section 必須化**。

---

## §7: 設計→実装連動

### Phase完了プロトコル

各Phase完了時に3層エビデンスで検証:
- **Layer 1（存在確認）**: 成果物が物理的に存在するか
- **Layer 2（値検証）**: 成果物の内容が上流と整合するか
- **Layer 3（ソース突合）**: 業務ソースとの突合

### TDD駆動

- 制約 → テスト対応表を必ず作成
- テストが先、実装が後
- デシジョンテーブル駆動テスト: Cap §ルール のデシジョンテーブルからテストケースを導出

**制約→テスト対応表フォーマット**:

| 制約ID | 制約内容 | テスト層 | テストファイル | 検証内容 |
|--------|---------|---------|-------------|---------|
| A-2 | 整合性境界一致 | unit | `{cap}/internal/domain/*.test.ts` | Aggregate不変条件 |
| IC-2 | Adapter直接結合禁止 | lint | `.eslintrc` import制約 | Adapter間import検出 |
| D-1 | 不可分性の定義 | integration | `{cap}/adapters/*.integration.test.ts` | Saga/補償トランザクション |

### テスト規範

| 層 | 対象 | 基準 | 戦略の導出元 |
|----|------|------|-------------|
| **unit** | Cap内Internal（Aggregate不変条件、Strategy/Policy） | C2 coverage 100% | Cap §品質 テスト方針 |
| **integration** | Cap間Adapter境界（IC-2整合） | Contract test | component-landscape.d2 |
| **e2e** | BPMシナリオ単位の画面駆動 | Mock-Reality Gap警戒 | bpm/{scenario}.d2 |
| **NFT** | 性能・可用性・セキュリティ | T1 Cap必須、T2/T3はPJ判断 | Cap §品質 |

### Phase分け規範

各Phaseは3条件ANDを満たすこと:
1. **デグレなし**: 当該Phase完了時点で本番ユーザー機能にregressionなし
2. **体験完結**: 当該Phaseで完結するvalue delivery
3. **検証可能**: e2e test + bug残存確認 + NFT実施が当該Phase内で可能

---

## §8: 成果物生成プロセス（ハルシネーション防止）

### 段階的制約（前段階にないものは追加禁止）

全レイヤー・全成果物に適用する横断原則。各段階で「前段階の成果物にないものは追加してはならない」。

| 段階 | 入力（前段階） | 追加禁止 |
|---|---|---|
| strategy §2 BF | 業務ソース + `strategy/reference/` | 業務ソース・reference にない業務ステップ |
| **strategy §2 UN §情報定義** | 業務ソース + `strategy/reference/` + §2 BF | 業務ソース・reference にない情報項目 (= **業務フローの step 単位 declared = 入力 step に該当する UN で入力情報を、 出力 step に該当する UN で出力情報を declared、 UN と情報定義は 1:1 ではない、 入力系 / 出力系 / 入出力混在 / 情報定義なし いずれも自然発生** = §5 L1 §1 例外条項参照、 **format 自由 = 表 / bullet / 自由記述、 表形式を強制しない**、 桁数 / 文字種等の属性は grounded source **3 区分** (= 法令公式 / 業界 declared / 内部決定記述) あれば記入、 なければ空欄 or **オープンイシュー化** (= §6 未決管理 3 系統)。 spec 本文に「PO 確認候補」 / TBD / 推測 / hedge declared 禁止 = ハルシネーション扱い) |
| BPM | 業務ソース + `strategy/reference/` + §2 BF | §2 BFを逸脱する業務ステップ |
| **Cap §データ aggregate** | BPM入力/出力 + L1 UN §情報定義 | BPM・UN にないデータ。 **データ項目 table (= 論理名 + 属性 + 制約) declared、 物理名禁止 (= 既存 Business App 連携時のみ 「論理名 (物理名)」 併記推奨)** |
| ui 情報定義 | Cap §データ aggregate | Cap §データにない情報グループ |
| ui 項目定義 | **L1 UN §情報定義 + L2 Cap §データ aggregate** 引用必須 + ui §情報定義 | L1/L2 にない項目 (= L3 独自定義禁止、 ハルシネーション源) |
| モック | ui/{screen}.md | 画面仕様にない要素 |
| デモ | モック | モックにない画面 |

### input source規範

| 成果物 | 許可されるinput source |
|---|---|
| `docs/specs/strategy/reference/` (= 業務ソース抜粋 / 競合サーチ / 既存実装ソース / 調査エビデンス) | 業務ソース（帳票・マニュアル・ヒアリング）, 既存システム, 外部調査（Web検索・規制文書・業界標準）, 自社判断。 元ファイル名維持 (= 英語変換禁止) |
| strategy.md | 業務ソース + `strategy/reference/` |
| BPM | 業務ソース + `strategy/reference/` + strategy.md §2 BF |
| capabilities.md | BPM + CRC + strategy.md + `strategy/reference/` |
| ui/{screen}.md | capabilities.md + BPM + 画面モック + `strategy/reference/` |
| 画面モック (L2) | capabilities.md + BPM + strategy.md + 共有 `@project/design-system`（トークン）+ `strategy/reference/` |
| L4設計文書 | L3成果物 + `strategy/reference/` |

### 出典必須ルール

業務ソースに基づく記述には出典を明記する。出典のない記述はハルシネーション候補として扱う。

出典の形式: `SRC-{NNN}` または `UN-{N}({タイトル})` または `SP-{N}({タイトル})`

**grounded source 3 区分**:

- **法令公式** (= 公式 doc URL、 例: 全銀協 / 金融庁 / 国税庁 declared)
- **業界 declared** (= 公開 doc 確認済、 例: ISO / JIS / 業界標準書)
- **内部決定記述** (= 業務ヒアリング / PJ 内部 declared 記録、 PO 直接 grounded、 `strategy/reference/` 配下。 顧客露出 NG な内部記述として明示分離)

> **「PO 確認候補」 declared は禁止** (= ハルシネーション扱い、 spec 本文へ hedge が混入する温床)。 PO 判断待ち項目は **§6 未決管理 3 系統** (= DR §OQ / 計画文書 §OQ / GitHub Issue) で別管理、 spec 本文には grounded 後の確定値のみ記入。

**未決論点の出典禁止扱い**: 未決論点は「出典なし declared」 (= 推測値 + 「declared なし」 + 「Phase 1 で grounded 化」 等の defer) でなく、 **オープンイシュー化必須** (= §6 未決管理 3 系統)。 spec 本文に未確定値を残さない。

---

## §9: 品質ゲート（CP-1〜4）

| CP | タイミング | レビュー対象 | 承認者 | 判断基準 |
|----|----------|------------|--------|---------|
| **CP-1** | L1完了 | strategy.md | PO | §2のBFが業務フローを網羅しているか。全BFに4-6ステップの骨格があるか。全UNがいずれかのBFに属しているか。§3 SC / §4 SPが業務要件を網羅しているか |
| **CP-1.5** | L2 Phase A完了 | BPM | PO | 業務フローが業務ソースと整合しているか。全アクターの操作が網羅されているか。§2のBF骨格を逸脱していないか。BPMシナリオとBFの対応が明示されているか |
| **CP-2** | L2 Phase B/C完了 | capabilities.md + landscape | PO + 設計者 | Cap境界が変更理由で切れているか。Parnas評価のS合計が最小か |
| **CP-2.5a** | L3 画面情報定義完了 | ui/{screen}.md 情報定義 | PO | 必要な情報は揃っているか。不要な情報はないか。情報のまとまりが業務に合っているか |
| **CP-2.5b** | L2 画面モック完了 | 全画面モック（navigable demo）+ coverage-matrix | PO + 顧客 | モックを操作して業務が成立するか。機能の過不足（定義の不足）はないか。情報定義にない要素が混入していないか |
| **CP-3** | L3完了 | 全L3成果物 | 設計者 | cross-Cap整合性。API/Event名・型の一致。Component境界のIC-1〜8準拠 |
| **CP-4** | L4完了 | 全L4成果物 | 設計者 | L3との整合性。実装方針の横断的一貫性 |

---

## §10: テンプレートとプロセスツール

### テンプレート一覧

| テンプレート | 対応成果物 | 配置先 |
|---|---|---|
| `templates/strategy/strategy.md.template` | #1 strategy.md | `strategy/` |
| `templates/strategy/strategy-actors-section.md.template` | #1 §1 関連組織・アクター・システム | `strategy/` |
| `templates/strategy/crc.md.template` | #2 crc.md | `strategy/` |
| `templates/requirements/capabilities.md.template` | #3 capabilities.md | `requirements/` |
| `templates/requirements/capability-landscape.d2.template` | #4 landscape | `requirements/` |
| `templates/requirements/bpm-scenario.d2.template` | #5 BPM | `requirements/bpm/` |
| `templates/architecture/ui-screen.md.template` | #12 ui/{screen}.md | `architecture/ui/` |
| `templates/architecture/component-diagram-cap.d2.template` | #9 component詳細 | `architecture/component-diagrams/` |
| `templates/architecture/cap-api.v1.yaml.template` | #11 API定義 | `architecture/api/cap/` (+ `architecture/openapi/cap/`) |
| `templates/architecture/db-er-diagram.d2.template` | ER図（導出成果物） | `architecture/` |
| `templates/architecture/stride-cap-or-area.md.template` | STRIDE（導出成果物） | `architecture/security/` |

### プロセスツール

#### CRC構造

**レベル1: 境界横断の変更（CRC）** — システム全体に対する変更シナリオ。Cap未定義の段階で記述。HowではなくWhat。

**レベル2: Cap内部の変更（§設定）** — Cap内部のConfig/Logic変更で吸収可能な変更。CRCには含めない。

#### Parnas評価手順

1. CRC全件を行、Cap全件を列に配置
2. 各セルにS（構造的変更必要）またはN（内部吸収可能）を記入
3. S合計を比較 → S合計が最小の分割案が最適
4. S合計が同等の場合、Sの分布（特定Capに集中 vs 分散）で判断

#### CRC品質チェックリスト

| Q | チェック項目 |
|---|------------|
| Q1 | 全変動軸（商品/クライアント/チャネル/規制/外部連携）をカバーしているか |
| Q2 | 「起こりそうにないが起きたら影響大」の変更を含んでいるか |
| Q3 | 各CRCが具体的な業務シナリオとして記述されているか |
| Q4 | CRC間に重複・包含関係がないか |
| Q5 | 既存システムの変更履歴から漏れている変更パターンがないか |

#### 例外管理台帳（E-6）

| ID | 画面 | 違反原則 | 例外内容 | D-2根拠 | 実装方式 | 登録日 |
|----|------|---------|---------|---------|---------|--------|
| EX-{NNN} | {画面名} | {原則ID} | {説明} | {業務的不可分性の根拠} | {方式} | YYYY-MM-DD |

登録条件: D-2基準で「片方だけ成功した状態が業務上許されない」場合のみ。UI利便性は根拠にならない。

---

## §11: PJ規模別スケーラビリティ

**省略 ≠ 不要**: 省略した成果物の責務は消えない。strategy.md内にinlineで記述する等、情報は必ず維持する。

| 規模 | Cap数 | 省略可能 | 必須維持 |
|---|---|---|---|
| **Large** | 20+ | なし | 全成果物 |
| **Medium** | 5-19 | NFT詳細計画 | #1(strategy), #2(CRC), #3(capabilities), #5(BPM), #6(画面モック), #7(Parnas), #8-12, #13-17 |
| **Small** | 1-4 | 上記 + #7(Parnas) + #8(Component Landscape) | #1, #2, #3, #5, #6(画面モック), #9-12, #13-17 |
| **Micro** | 0-1 | 上記 + #3(capabilities) + #5(BPM) | #1(strategy), #6(画面モック), #12(ui) |

<!-- #20 (groundwork) は廃止 (= `docs/specs/strategy/reference/` に統合)。 設計補助資料は strategy.md §6 Reference Index から `strategy/reference/` 配下を参照する形に一本化。 業務ソースから直接書ける場合は reference/ 配置も任意。 -->

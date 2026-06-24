# 画面モック 環境・デプロイ guide

> **本ファイルの位置づけ**: L2 画面モック (navigable flow prototype) の **環境構築・起動・デプロイ手順のみ** を扱う運用 runbook (= 設計/配置の正本は DPG §5 + artifact-placement-guide)。**設計 how-to (何を・なぜ作るか、coverage・seam・gate の規範) は `design-process-guide.md` §5 L2 §画面モック を SSoT** とする。本ファイルは「どう動かす・どう顧客に見せるか」だけを declared。**mock 本体 = standalone-capable な web area** (= `web-spa/`、React + Vite + react-router + design-system)。**mock は本番実装の前身であり別実装ではない** = 本番化はデータ層 (MSW / @mswjs/data → 実 API) の差し替えのみで、**何も捨てない** (screen component / route tree / view model / UI 構造 / build 設定を変えない)。standalone-capable なため Web 埋込・Capacitor wrap・SDK へ持ち越せる。技術選定基準 (= 将来の要件適用 = Web / スマホアプリ / スマホネイティブ / SDK / widget の全充足) は DPG §5 §mock 技術選定基準が SSoT。
>
> - **対象読者**: Claude Code / Codex AI agent + 開発者
> - **想定スタック**: **React 18 + Vite + Tailwind + shadcn/ui (限定) + 独自 atomic + react-router** の `web-spa/` (= リポ root 直下、 flat 配置 = tenant 別 dir なし。**standalone-capable = mock の SPA がそのまま本番 web 画面の正本**) + **`mobile/`** (= Capacitor wrap of web-spa + ネイティブ機能 plugin (= 外部 SDK 統合等) を Capacitor plugin として組込み) + 共有部品 = **`@project/design-system`** (= デザイントークン + 共有 component の単一 package、 npm 参照) + MSW / `@mswjs/data` + Vercel (CLI prebuilt deploy)
> - **Docker は使わない**: 画面モックは frontend のみ (実バックエンド無し)。`vite dev` の HMR で即時反映。Docker は L5 / 結合で実バックエンドが出てから。

## 目次

- [前提ツール](#前提ツール)
- [ローカル開発環境の起動](#ローカル開発環境の起動)
- [モックデータ層のセットアップ](#モックデータ層のセットアップ)
- [navigable flow の配線](#navigable-flow-の配線)
- [共有 package の参照 (design-system)](#共有-package-の参照-design-system)
- [native view 内 in-place 表示 (IC-9 mount Adapter)](#native-view-内-in-place-表示-ic-9-mount-adapter)
- [Vercel デプロイ (顧客レビュー)](#vercel-デプロイ-顧客レビュー)
- [L5 昇格時の除去手順](#l5-昇格時の除去手順)

## 前提ツール

| ツール | 用途 | 確認コマンド |
|---|---|---|
| Node.js 18+ | SPA (Vite) 実行基盤 | `node --version` |
| pnpm / npm | パッケージ管理 | `pnpm --version` |
| Vercel アカウント + CLI | デプロイ | `vercel --version` |

> Docker は不要 (frontend のみ)。version 差異の回避目的でも、画面モック段階ではホストの Node で dev server (vite) を直接動かす。

## ローカル開発環境の起動

### src/ (React + Vite)

```bash
cd src/
npm install        # or pnpm install
npm run dev        # vite。HMR で保存→即時反映
```

- 変更は **保存した瞬間に反映** (HMR)。ビルド / デプロイ不要。
- 顧客に「その場でリアルタイム反映」を見せる場合のみ画面共有でこの `vite dev` を共有する (通常は後述の Vercel デプロイ 往復で足りる)。

### mobile/ (Capacitor wrap of prototype)

```bash
cd mobile/
npm install
npx cap sync                 # web → native bridge 同期
npm run dev                  # Capacitor 経由で iOS / Android シミュレータ起動
```

- ネイティブ SDK は **Capacitor 公式 plugin として組込み** (= 各 plugin の組込手順は当該 plugin 公式 SDK doc を参照、 例 = push 通知 / native storage / biometric 認証 / 外部 SDK 統合 等)。
- mobile/ は `src/` の Capacitor wrap (= 同一 React + Vite codebase を WebView で読込む)。 build target 切替 (`vite build --mode web` / `vite build --mode mobile`) で出力先のみ変える (= 二重実装禁止)。

## モックデータ層のセットアップ

実バックエンド無しでデータを供給する。静的で足りるか、stateful (作成→反映) が要るかで選ぶ。

- **静的 (単画面・固定データ)**: MSW の static handler で fixture を返す。
- **stateful (flow prototype。作成→一覧反映→詳細で見える)**: `@mswjs/data` で in-memory の entity store を定義し、handler を自動生成。

```bash
pnpm add -D msw @mswjs/data @faker-js/faker
```

- entity は **view-model 型** (cap §データ由来) で定義する (seam を view-model に置く規範は DPG §5 参照)。
- seed は faker 等で生成。fixture も view-model 型に束縛 (型にない項目はコンパイルエラー)。
- MSW の起動配線 (browser worker / アプリへの組込み) は MSW 公式 setup に従う。

## navigable flow の配線

「画面単体の動き → ページ間遷移」は SPA の routing で繋ぐ (別層は不要)。

- 画面遷移: ルーター (react-router の `<Link>`)。route tree は最初から固定する。
- stateful な体験: `@mswjs/data` の in-memory store により、フォーム送信 → 一覧 route に遷移 → 反映、が backend 無しで成立する。
- **画面コンポーネントに環境分岐を入れない**。差し替えてよいのは Data Provider と Persistence のみ。

### 3 層分離 (Pure models / データ取得 hooks / ビュー) — view-model seam の実装

画面が data source (fixture / 実 API) を直接掴むと、本番化で全画面を改変する羽目になる。画面と data の間に **データ取得 hook** を 1 枚挟む (= 規範は DPG §5 §mock 技術選定基準):

```
web-spa/src/
├── models/{domain}/      # Pure: 型 / 検証 / 計算 / 状態マッピング (本番も不変)
│   ├── types.ts          #   view-model の形
│   └── {entity}.ts       #   純関数 (status→variant マッピング / format 等)
├── hooks/{domain}/       # ★ view-model seam = 本番差し替えはここだけ
│   ├── fixtures.ts       #   Mock 段階のデータ源 (hook だけが参照)
│   └── use{Entity}.ts    #   useXxx() = { data, isLoading, error } を返す
└── (screen component)    # hook を呼ぶだけ。data source を直接 import しない
```

- **hook の返り値の形 `{ data, isLoading, error }` は Mock / Demo / 本番で不変**。本番化はこの hook 内を `fixture 返却` → `await api(...)` に変えるだけ → 画面は無変更
- **画面の fixture / axios 直 import は禁止** (= カプセル化の漏れ。差し替え点が画面に散る)
- **粒度 = 1 file = 1 hook = 1 concern**。画面単位でも DB テーブル単位でもない (1 画面が複数 concern hook = 取得 / 選択 / 検索 / 並べ替え 等 を使ってよい)。`use{Concern}.ts` で 1:1、複数 concern を 1 hook に詰めない
- **mount cleanup を持つ** (`mountedRef` で unmount 後 setState を防止 = async 化時の race / leak を構造排除)
- 段階対応: **Mock = fixture / Demo = `@mswjs/data` (in-memory store + 永続) / 本番 = 実 API**。いずれも hook の内側で切替 (画面に分岐を持ち込まない)

## 共有 package の参照 (design-system)

共有 UI 部品の正本は **`@project/design-system` 単一 package** (= デザイントークン + 共有 component)。配信形態は npm publish (= semver + changesets による自動 changelog + version bump、 alpha/beta tag で検証配信)。PR で `pnpm build` + `pnpm test` + `pnpm publint` + `@axe-core/playwright` (a11y) + Playwright VRT (Visual Regression Test、 Storybook 全 story + 主要画面 pixel diff 閾値 0.1%) を必須 gate 化する。マルチ channel 適用 (native app wrap / 他社埋込 widget / SDK packaging) は**ラッパーとして既存構成から分離して追加**する (= 切り出し最小原則。ラッパーが各アプリのデプロイ単位に依存する場合はデプロイ単位別に分割)。

### @project/design-system (= 共有部品の単一正本)

- 提供範囲 = **デザイントークン** (`colors` / `spacing` / `typography` / `shadows` / `breakpoints` / `theme`) + **共有 component** (atoms / molecules / organisms / dialogs)。
- 配信 = npm publish (subpath exports = `./tokens` + `./components` + `./styles.css`。`./tokens` は react 非依存を publint で構造保証)。
- 参照例:
  ```typescript
  import { colors, spacing, px } from "@project/design-system/tokens";
  import { Button, Card, FormField } from "@project/design-system/components";
  ```

### テナント・機能切替の接続点 (= runtime 設定 API)

- テナント切替の接続点 = **runtime 設定 API** (= server 管理の設定をリクエスト時に取得。npm package による静的 config 配布は行わない)。 tenant 別 dir (= apps/mock-{tenant}/) は **禁止** (1 codebase + 接続点による切替)。
- mock 段階では MSW で同 API を mock する (= 本番と同じ接続点の形を保つ)。
- テナント別の差分 (= ブランディング / 機能 on/off 等) は本接続点経由で解決する。 画面 component や route tree は無変更。

### 他社埋込 widget (= 条件付きのラッパー切り出し)

- widget は**条件付き** (= 外部埋込需要の確定時にのみラッパーとして切り出す。常設の必須 package ではない)。実装方式 (Custom Element / iframe 等) は PoC で確定し、 React component の wrapper 候補 = `@lit/react` 等。
- 採用時の要件: (1) Shadow DOM **closed mode** (= 他社 CSS leak block)、 (2) Custom Element name **prefix `platform-` 固定** (= name collision 回避)、 (3) Capacitor WebView 内同一挙動 (= touch event / scroll behavior / safe-area-inset)、 (4) Shadow DOM a11y = host 側 `aria-label` 直接付与 + `<slot>` 経由 a11y tree 構築、 (5) React 子コンポーネント slot 経由配置の双方向 prop / event bridge。
- 参照例 (他社サイト埋込):
  ```html
  <script src="https://cdn.example.com/widget/platform-sample-widget.js"></script>
  <platform-sample-widget tenant-id="..."></platform-sample-widget>
  ```

## native view 内 in-place 表示 (IC-9 mount Adapter)

新規 React component を native view (= ERB / その他 server-rendered view) 内に表示する際は、 view 側を改変せず **mount Adapter を 1 段挟む** (= IC-9 Adapter Registry pattern、 DPG §1.6 参照)。 業界事例 = native view 内 SPA component の in-place mount (= GitLab の Vue in-place mount 等で長期運用実績)。

```erb
<%# native view 側 (= 改変なし) %>
<%# NB-2: props は ERB::Util.html_escape で必ず JSON escape (= XSS 対策、 @case.id 等の untrusted source 経由を想定) %>
<div data-controller="react-mount"
     data-react-mount-component-value="CaseListScreen"
     data-react-mount-props-value="<%= ERB::Util.html_escape({ caseId: @case.id }.to_json) %>">
</div>
```

> **NB-2 (XSS 対策)**: `data-react-mount-props-value` に渡す JSON は **`ERB::Util.html_escape` で必ず escape** する。 props 元 (= `@case.id` 等) が untrusted source (= URL param / form input 経由) を含む可能性があるため、 `to_json` のみだと `</script>` injection や属性脱出に脆弱。 `ERB::Util.html_escape` (= `&` / `<` / `>` / `"` / `'` を HTML entity 化) を必ず重ねる。

```typescript
// app/javascript/controllers/react_mount_controller.ts (= mount Adapter)
import { Controller } from "@hotwired/stimulus";
import { createRoot, Root } from "react-dom/client";
import { Suspense } from "react";
import { ALLOWED_COMPONENTS, getComponent, ErrorFallback, LoadingFallback } from "@project/design-system/components";

export default class extends Controller {
  static values = { component: String, props: Object };
  private root: Root | null = null;

  connect() {
    // AN-3: 二重 mount ガード (= 同一要素に createRoot を 2 回呼ぶと React が warning を出し state が壊れる、 Turbo Frames / Streams の再 connect で発生し得る)
    if (this.root) {
      console.warn(`Already mounted: ${this.componentValue}, skipping`);
      return;
    }

    // NB-3: 早期に root を作る (= 以降の fallback / loading / 正常 render を全て React 経由に統一、 innerHTML 直書きを排除して XSS risk 排除)
    this.root = createRoot(this.element);

    // 許可リスト validation (= 任意 component の動的解決を禁止、 prototype pollution 対策)
    if (!ALLOWED_COMPONENTS.includes(this.componentValue)) {
      console.error(`Unknown component: ${this.componentValue}`);
      // NB-3: innerHTML でなく React render (= XSS risk 排除、 message は React が text node 化)
      this.root.render(<ErrorFallback message="読み込みエラー: 不正な component" />);
      return;
    }

    // component 存在チェック (= 名前付き export で型安全に解決)
    const Component = getComponent(this.componentValue);
    if (!Component) {
      this.root.render(<ErrorFallback message="component 未実装" />);
      return;
    }

    // NB-4: loading UI = React Suspense で fallback (= 非同期 component / lazy 読込時に LoadingFallback 表示、 同期 component でも即時 render)
    this.root.render(
      <Suspense fallback={<LoadingFallback />}>
        <Component {...this.propsValue} />
      </Suspense>
    );
  }

  // Turbo Drive 対策 = disconnect で root.unmount() (= memory leak / 二重 mount 防止)
  disconnect() {
    if (this.root) {
      this.root.unmount();
      this.root = null;
    }
  }
}
```

> **NB-3 (innerHTML XSS 対策)**: fallback / error 表示は **必ず React render 経由** (= `this.root.render(<ErrorFallback ... />)`) で行い、 `this.element.innerHTML = '...'` の直書きは禁止。 message 文字列が将来 i18n / user input 由来になった際に script injection を許す risk を排除する。 `ErrorFallback` / `LoadingFallback` は `@project/design-system` の components 層で named export として提供 (= 一元管理 + 型安全)。
>
> **NB-4 (loading UI)**: 非同期 / lazy import される React component は **`<Suspense fallback={<LoadingFallback />}>` で wrap** する。 同期 component (= 即 mount) でも Suspense は副作用なし。 lazy 化への移行時に Adapter 側を再改修せず済む形に統一。 `LoadingFallback` は `@project/design-system` 提供 (= spinner / placeholder の共通 UI)。
>
> **LoadingFallback と Turbo Drive ローディング表現の一貫性**: Turbo Drive はページ遷移時に独自の progress bar (= 既定では画面上端の青ライン) を表示する。 React 側 `LoadingFallback` (= mount 完了までの spinner / placeholder) と Turbo Drive progress bar が同時表示されると体感上 2 重ローディングとなり UX が分断するため、 以下の規範で統一する:
>
> 1. **Turbo Drive progress bar はデザインシステム準拠の色 + thickness に上書き**: `app/javascript/application.ts` 等 entry で `Turbo.setProgressBarDelay(100)` (= 100ms 以内に完了する遷移では bar を出さない) を設定、 CSS で `.turbo-progress-bar { background-color: var(--ds-color-primary); height: 3px; }` (= `@project/design-system/tokens` の primary color と整合) を declared。
> 2. **`LoadingFallback` 表示までの delay は同 100ms**: `LoadingFallback` 内部に `setTimeout(() => setVisible(true), 100)` の delay を持たせ、 100ms 以内に mount 完了する場合は spinner を出さない (= Turbo Drive と同 threshold で挙動統一)。 `@project/design-system` 側で props でこの delay を上書き可能 (= `<LoadingFallback delay={50} />` 等)。
> 3. **配色 / アニメーション統一**: `LoadingFallback` の spinner color = Turbo progress bar と同 primary color、 アニメーション周期は `--ds-motion-loading-duration` トークン (= `@project/design-system/tokens` で 1200ms 既定) を参照、 双方が視覚的に「同一 PJ の loading」 と認識される様にする。
>
> **Error Boundary 運用方針**: API 呼出 / lazy import / その他 runtime 例外で React component が throw した場合、 throw が `createRoot` 全体に伝播すると mount root 全体が消失し native view 側の周辺要素のみが残る半壊状態になる。 これを防ぐため、 mount Adapter で render する component は **必ず Error Boundary で wrap** する:
>
> ```typescript
> // @project/design-system の components 層で named export として提供
> import { ErrorBoundary } from "@project/design-system/components";
>
> this.root.render(
>   <ErrorBoundary fallback={(error) => <ErrorFallback message={`実行時エラー: ${error.message}`} />}>
>     <Suspense fallback={<LoadingFallback />}>
>       <Component {...this.propsValue} />
>     </Suspense>
>   </ErrorBoundary>
> );
> ```
>
> - **`ErrorBoundary` の責務**: child component tree で throw された全 error を catch + 統一 `ErrorFallback` UI に切替表示 (= `componentDidCatch` で sentry 等への error log 送信も同 component に集約)。 NB-3 の許可リスト validation / component 未実装 fallback と message が同 UI で表示される (= 「読み込みエラー」 系は許可リスト由来、 「実行時エラー」 系は throw 由来、 と分類 message で区別)。
> - **網羅範囲**: lazy import 失敗 (= chunk load error) / 非同期 hook 内 throw / render 関数内 throw / event handler 以外の error が対象。 event handler 内 error は React の Error Boundary では catch されないため、 個別 component で `try-catch` + `setError(error)` state pattern を別途実装する規範 (= `@project/design-system` の components 層で `useAsyncError` hook として共通化する)。
> - **production / development 差異**: development では error stack を message に展開、 production では「申し訳ありません、 画面の表示中にエラーが発生しました」 + reload button を表示 (= `process.env.NODE_ENV` 判定で `ErrorFallback` 内部分岐)。 error log は sentry / 内製エラートラッキングへ送信。

- Stimulus controller = mount Adapter、 React component = `@project/design-system/components` から import (= 本番 mount の import 元に L2 mock 用 prototype を使わない)。
- **`ALLOWED_COMPONENTS` / `getComponent`**: design-system 側で named export の許可リスト + 型付き resolver を提供 (= 動的 key で `components[key]` を引かない)。 不正 key は console.error + fallback UI 表示。
- **Turbo Drive 互換**: Turbo Drive / Turbolinks による page transition で disconnect → connect が走るため、 `disconnect()` で `root.unmount()` 必須 (= 未 unmount は memory leak + 状態残留の原因)。
- **props 渡し**: native view 側で `data-react-mount-props-value` に JSON serialize して渡し、 Stimulus の `Object` value で受ける。

### mount Adapter の E2E / smoke test 戦略

mount Adapter 経由の React component は、 native view との配線・Turbo Drive 遷移時の lifecycle が壊れやすいため、 通し test を必須化する。

- **E2E (= Cypress または Playwright)**: native view 表示 → React component が mount される → 操作 (= form 入力 / button click) → 状態が React 側に反映される、 までを 1 シナリオで通す。
- **mock-data**: E2E では本 guide §モックデータ層 と同様に MSW handler を有効化 (= backend 起動不要)。

#### smoke test の Turbo 3 種分離

主要 native partial に対し、 Turbo の 3 系統 (= Drive / Frames / Streams) を分離して mount lifecycle を検証する (= 単一 reload テストだけだと frame / stream 経由の DOM 差替時 mount 漏れを検出できない)。

**「主要 native partial」 の対象範囲 (= 具体基準)**: 「主要」 の判定は **screen-coverage-matrix.md の React 化対象 mark (= `react_migration: yes` 列)** を SSoT とする (= L2 `docs/specs/ux/screen-coverage-matrix.md`、 DPG §5 L2 §画面 coverage matrix)。 同 matrix で React 化対象に mark された画面を覆う native partial が「主要 native partial」、 mark されていない画面は本 smoke test の対象外。 matrix 更新時に同 smoke test の対象 partial 列挙も同 PR で cascade 更新する (= DPG §2.7 SSoT 単一参照点 整合)。

1. **Turbo Drive** (= 全 page navigate、 history API + full page swap): 画面遷移 → 旧 page の React root が `disconnect` で unmount → 新 page で `connect` で mount 確認。 二重 mount / memory leak 検出。
2. **Turbo Frames** (= partial replace、 `<turbo-frame>` 内 DOM 差替): frame 内に Stimulus controller を含む React mount が在る状態で frame 更新 → frame 内のみ disconnect / connect、 outside の他 mount に影響なし確認。
3. **Turbo Streams** (= morph / append / replace / update、 server push 経由 DOM patch): stream による DOM 更新後も既存 mount が維持 (= idempotent) または正しく再 mount される確認。

各系統で最低 1 シナリオ。 React 化対象画面増加と同期で拡充。

#### E2E fallback UI 異常系シナリオ

正常系のみでなく、 fallback UI が実際に表示されることを E2E で確認する。

- **許可リスト外 component** (= `data-react-mount-component-value` に `ALLOWED_COMPONENTS` 未登録の名前): "読み込みエラー: 不正な component" の text が DOM に現れる (= `ErrorFallback` の React render 経由) ことを assert。
- **component 未実装** (= 許可リストには在るが `getComponent` が `null` 返す pattern): "component 未実装" text が表示されることを assert。
- **lazy import 失敗** (= 将来 lazy 化された component の network 失敗想定): `@project/design-system` の全 component が同期 import 配信 (= chunk 分割未導入) の段階では実行不能。 lazy 化導入時 (= src/ bundle size が 500KB を超えた段階で `React.lazy()` + `Suspense` 導入) に E2E 追加。 lazy 化導入時は `LoadingFallback` 表示後、 Error Boundary 経由で error 表示に切替確認。

#### Playwright CI 配線

リポの CI に Playwright job を追加 (= 既存 RSpec / Jest と並列実行)。 最小 1 シナリオから開始。

```yaml
# .github/workflows/playwright.yml
name: e2e
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "18" }
      - uses: ruby/setup-ruby@v1
        with: { bundler-cache: true }
      - run: npm ci
      - run: npm run build              # prototype JS bundle 生成 (= native view から import 可能化)
      - run: bundle exec rails db:setup
      - run: bundle exec rails server -d -p 3000   # server 起動 (= mount Adapter の host)
      - run: npx wait-on http://localhost:3000 --timeout 60000   # 起動完了待機 (= -d 直後は port open 前で接続失敗、 60s timeout で fail-fast)
      - run: npx playwright install --with-deps
      - run: npx playwright test        # E2E 実行 (= server 経由 mount + MSW handler 重ねがけ)
```

> **補足**: `bundle exec rails server -d` は daemon 化のみで port listening 開始までは別途数秒〜数十秒かかる。 直後に Playwright を起動すると `ECONNREFUSED` で fail する。 `wait-on http://localhost:3000` で HTTP 応答可能になるまで block する (= 60s timeout で hung 防止)。 `wait-on` は dev dependency に追加 (= `npm i -D wait-on`)。 同様の規範を local 実行 script (= `npm run e2e:rails`) にも適用。

#### MSW E2E ↔ 統合 E2E の責務境界

E2E は 2 層に分離して責務を明確化する (= mock vs 統合の混在で「動作確認したつもり」を防ぐ)。

- **frontend-only E2E** (= MSW handler 有効、 server 起動不要): `src/` 単体 component の API モック動作確認、 view-model seam の正常性検証。 Vite dev server + Playwright で完結。 高速・並列実行可。
- **統合 E2E** (= 実 BFF + 実 server + mount Adapter): server 起動 + Playwright で native view → mount Adapter → React component → API call の通し test。 上記 Playwright CI 配線はこちらに該当。
- **適用方針**: 最初は **frontend-only から start**、 React 化対象画面が一定数 (= 5 画面目安) を超えた段階で統合 E2E を追加。 統合 E2E は L5 昇格前に必須化 (= 本番昇格 gate)。 「frontend-only で通るが統合で落ちる」 case (= Turbo Drive 遷移 / CSRF / session 等) を昇格前に検出する。

#### frontend-only E2E 最小 CI 配線

frontend-only E2E (= Vite dev server + MSW + Playwright) の最小 CI 例を declared する。 配置 file = `.github/workflows/playwright-frontend.yml`、 統合 E2E (= `playwright.yml`) と並列実行する (= 2 job 構成、 frontend-only は高速で全 PR、 統合は main / release branch + nightly)。

```yaml
# .github/workflows/playwright-frontend.yml
name: e2e-frontend-only
on: [push, pull_request]
jobs:
  e2e-frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./prototype
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "18" }
      - run: npm ci
      - run: npm run build                                   # prototype bundle 生成 (= preview server 用)
      - run: npx vite preview --port 4173 &                  # 静的 preview server (= 軽量、 server 不要)
      - run: npx wait-on http://localhost:4173 --timeout 30000   # preview server 起動完了待機
      - run: npx playwright install --with-deps
      - env:
          PLAYWRIGHT_BASE_URL: http://localhost:4173
          MSW_ENABLED: "true"                                # MSW handler を有効化 (= API call を fixture で応答)
        run: npx playwright test --project=frontend-only     # frontend-only suite のみ実行
```

- **playwright.config.ts** の project 分離: `frontend-only` (= MSW 前提、 server 起動不要) / `integration` (= 実 server 前提) の 2 project を declared、 環境変数 `MSW_ENABLED` で切替。 同一 spec file 内で `test.describe.configure({ mode: "serial" })` + project tag で分岐。
- **実行コスト目安**: frontend-only = 2-3 分 / PR、 統合 = 8-12 分 / PR (= db:setup + boot 含む)。 frontend-only を全 PR、 統合を main + release で運用すると CI cost を 4-5 倍圧縮可能。

### src/ + mobile/ codebase 共有戦略

mobile/ は hybrid native shell で、 src/ と同 React codebase を再利用する前提とする。

- **採用**: **Capacitor wrap of prototype** (= 同一 React + Vite codebase を web ビルド + Capacitor の iOS / Android native build target でラップ)。
- **配置**: リポ root 直下に `src/` (= React + Vite codebase 本体) + `mobile/` (= Capacitor 設定 + native plugin のみ)。 `mobile/` の React コードは `src/` を package 参照する (= file 重複なし、 build target 切替で出力先のみ変える)。
- **mobile/ dir の責務**: `capacitor.config.ts` / `ios/` / `android/` (= native shell + Capacitor plugin 設定)、 およびネイティブ機能 plugin (= 外部 SDK 統合等) を Capacitor 公式 plugin として組込み。 React component / 画面ロジックは src/ から import (= 二重実装禁止)。 ネイティブ UX が必要な機能 (= push 通知 / native storage / biometric 認証 / 外部 SDK 統合 等) は当該機能の公式 Capacitor plugin で対応する。
- **build target 切替**: `vite build --mode web` で src/ deploy 用、 `vite build --mode mobile` で Capacitor 取込用、 mode に応じた Data Provider (= MSW / 実 API) を環境分岐ではなく **DI で切替** (= 画面 component に環境分岐を入れない規範を継承)。

#### vite build mobile outDir ↔ Capacitor webDir 整合 CI

`vite build --mode mobile` の `outDir` (= JS bundle 出力先) と `capacitor.config.ts` の `webDir` (= Capacitor が native shell に bundle するソース dir) が一致していないと、 Capacitor が古い bundle / 空 dir を取込み「local では動くが native で白画面」の silent regression が発生する。 CI で整合性を機械検証する。

```yaml
# .github/workflows/mobile-build.yml
- name: Verify mobile vite outDir matches Capacitor webDir
  run: npx tsx scripts/verify-mobile-config.ts
- name: Build + sync
  run: |
    npx vite build --mode mobile
    npx cap sync
```

```typescript
// scripts/verify-mobile-config.ts
// node -e でも CJS default の取扱いと TS の compile で不安定なため、 tsx (= TypeScript 実行ランタイム) 経由で実行する。
// tsx は dev dependency に追加 (= `npm i -D tsx`)。
import viteConfig from "../vite.config.mobile";
import capacitorConfig from "../capacitor.config";

const outDir = (typeof viteConfig === "function" ? viteConfig({ mode: "mobile" } as any) : viteConfig).build?.outDir;
const webDir = (capacitorConfig as { webDir: string }).webDir;

if (outDir !== webDir) {
  console.error(`Mismatch: vite outDir=${outDir}, Capacitor webDir=${webDir}`);
  process.exit(1);
}
console.log(`OK: vite outDir = Capacitor webDir = ${outDir}`);
```

- **補足**: 旧版 (= `node -e "import('./vite.config.mobile.ts')..."`) は (1) Node の `-e` flag は既定で CJS、 dynamic `import()` の解決で実行時 ESM 化が不安定、 (2) `.ts` ファイルを直接 import するには `tsx` / `ts-node` 等の loader 必須、 (3) `vite.config.ts` が `defineConfig(({ mode }) => ...)` 形式の関数 export だと `m.default.build` が undefined になる、 という 3 つの不安定要因を持つ。 専用 script + `tsx` 経由実行で全要因を排除する。
- 設定の SSoT は `vite.config.mobile.ts` (= `build.outDir`) と `capacitor.config.ts` (= `webDir`) の 2 箇所。 一方のみ変更しても他方に追従しないと壊れるため、 CI 必須。
- 同 check は `npm run build:mobile` 直前に local script として実行することを推奨 (= 開発者環境で先に検出)、 package.json scripts に `"verify:mobile-config": "tsx scripts/verify-mobile-config.ts"` を declared し、 `"build:mobile": "npm run verify:mobile-config && vite build --mode mobile && cap sync"` と chain。

## Vercel デプロイ (顧客レビュー)

> **Vercel deploy** は **「成功表示でも実際は失敗 / 未反映」** が起きやすい。**deploy コマンドの完了だけで成功と報告しない。必ず後述の検証を行う**。

### 方式: ローカル prebuild → `vercel deploy` (Vercel CI ビルドは使わない)

安定している方式は **Vercel 側ビルドに頼らず、ローカルでビルドした成果物を CLI でアップロード** する:

```bash
# 1. ローカルビルド (src/)
cd src/
npx vite build            # → dist/ (= 出力先はプロジェクト依存)

# 2. プロジェクトに紐付いた dir で deploy (.vercel/project.json が必要)
vercel deploy --prod --yes
```

多クライアントは「クライアント×アプリごとに別 Vercel プロジェクト (`dist-{tenant}-{app}/`、各に `.vercel/project.json` + `vercel.json`)」とし、env (例 `VITE_TENANT_ID` / `VITE_APP_TYPE`) を変えてビルド→各 dir で deploy する。 テナント切替の接続点は **runtime 設定 API** (mock 段階は MSW で mock) に集約し、 tenant 別 dir (= src/{tenant}/) は **禁止**。

### 必須: デプロイ検証 ("完了ハルシネーション" 対策)

deploy コマンドの「完了」表示は信用しない。**毎回** 実体を確認する:

```bash
vercel ls | grep Production | head -1                  # ● Ready を確認
curl -sI https://<project>.vercel.app | head -1        # HTTP/2 200 を確認
```

- **`● Ready` かつ `HTTP/2 200` が揃って初めて「成功」と報告する**。揃わなければ未完了 / 失敗。

### よくある失敗

| 症状 | 原因 | 対処 |
|---|---|---|
| `npm run build` が型エラー多数で失敗 | `tsc -b` の pre-existing 型エラー | `npx vite build` を直接実行 |
| deploy 成功なのに 404 | `vercel.json` (SPA rewrites) が無い | `{"rewrites":[{"source":"/(.*)","destination":"/index.html"}]}` を配置 |
| `vercel deploy` が "Project not found" | `.vercel/project.json` が消えた | 該当 dir で `vercel link` 再リンク |
| 成功後もサイトが古い | CDN キャッシュ | 数分待つ or hash 付き URL で確認 |
| **`scripts/deploy-vercel.sh` 等の「デプロイスクリプト」を案内** | **そのようなスクリプトは存在しない (AI のハルシネーション)** | 上記の素のコマンドを直接実行 |

### 失敗時の復旧

- 直前ビルドのバックアップ (`cp -R dist-... /tmp/...bak`) から復元して再 deploy、または `vercel alias <過去デプロイURL> <本番URL>` で過去デプロイへ alias 戻し。
- モックは frontend のみ (MSW / @mswjs/data) なのでバックエンドのホスト不要。

## L5 昇格時の除去手順

本番 (L5) 昇格時、モックデータ層を **本番 bundle から除去** する (screen component / route / view-model は無変更)。

1. Data Provider を MSW / `@mswjs/data` → 実 API / 実 Repository に DI スワップ。
2. `msw` / `@mswjs/data` / `*.fixtures.*` を本番 dependency / entry から外す。
3. **CI hard block**: 本番 build に `msw` / `@mswjs/data` / fixture が混入していないことを検査 (混入時 merge block)。

> 昇格 gate の規範 (何を満たせば L5 に進めるか) は `design-process-guide.md` §5 L2 §画面モック / L5 を SSoT とする。

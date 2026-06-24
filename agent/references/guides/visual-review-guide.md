# ビジュアルレビューガイド

## 目的

画面（View/Template/Style）の変更を含む PR をレビューする際、HTML mockup からスクリーンショットを生成し、PC/SP 両ビューポートでのレイアウトを視覚的に検証する。

## 適用条件

PR の変更ファイルに以下のいずれかが含まれる場合、ビジュアルレビューを実施する:

| ファイル種別 | 拡張子 / パターン |
|-------------|------------------|
| テンプレート | `.haml`, `.erb`, `.html`, `.slim` |
| フロントエンド | `.tsx`, `.jsx`, `.vue`, `.svelte` |
| スタイル | `.scss`, `.css`, `.less`, `.sass` |

## ワークフロー

### 1. 変更検出

```bash
git diff {BASE_BRANCH}...HEAD --name-only | grep -E '\.(haml|erb|html|slim|tsx|jsx|vue|svelte|scss|css|less|sass)$'
```

### 2. HTML mockup 作成

変更されたコンポーネントを再現する standalone HTML ファイルを作成する。

**構造規則:**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <style>
    /* 実際の SCSS/CSS から関連するスタイルを転写 */
    /* CSS カスタムプロパティで動的値を再現 */
  </style>
</head>
<body>

<!-- セクション: {viewport}-{variant}-{state} -->
<div class="mockup-section" id="pc-oem-before">
  <div class="mockup-label">ラベル <span class="badge badge--before">Before</span></div>
  <div style="width: 1280px;">
    <!-- 実際のコンポーネント HTML -->
  </div>
</div>

<!-- 他のセクションも同様 -->
</body>
</html>
```

**セクション ID 命名規則:**

```
{viewport}-{variant}-{state}
```

| 部位 | 値 | 説明 |
|------|-----|------|
| viewport | `pc`, `sp` | PC (1280px) / SP (375px) |
| variant | `oem`, `original`, `default`, ... | テナント/状態バリエーション |
| state | `before`, `after` | 変更前/変更後 |

**推奨セクション構成:**

- Before/After 比較が必要な場合: `pc-*-before`, `pc-*-after`, `sp-*-before`, `sp-*-after`
- 変更なしの確認: `pc-original`, `sp-original`

### 3. スクリーンショットキャプチャ

```bash
node .claude/scripts/visual-capture.js {mockup.html} --out {screenshots_dir}
```

**ビューポート自動判定:** セクション ID が `sp-` で始まる場合は 375px、それ以外は 1280px で撮影。

### 4. 視覚検証チェックリスト

| チェック項目 | 説明 |
|-------------|------|
| テキスト表示 | 文字切れ・はみ出し・折り返し位置 |
| レイアウト | flex/grid の配置方向、スタッキング順序 |
| スペーシング | margin/padding の過不足 |
| レスポンシブ | PC→SP でのレイアウト変化の適切さ |
| 既存ページ影響 | 変更なしパターン（Original等）で表示崩れなし |

### 5. DR への記録

スクリーンショットは DR の `screenshots/` サブディレクトリに配置し、DR 本文から参照する。

```markdown
#### PC表示 — After
![PC After](screenshots/pc-oem-after.png)

#### SP表示 — After
![SP After](screenshots/sp-oem-after.png)
```

## リポジトリ別の注意事項

| リポ | テンプレート | スタイル | 備考 |
|------|------------|---------|------|
| module-a | Haml (`.haml`) | SCSS (BEM: `.c-Component-element`) | CSS カスタムプロパティで OEM テーマ切替 |
| module-b | 要確認 | 要確認 | DR パス: `docs/github/{PR番号}/` |
| module-d | ERB/Haml | SCSS | DR パス: フラット |
| module-c | 要確認 | 要確認 | DR パス: フラット |

## mockup 作成のコツ

1. **実際の CSS を転写**: SCSS のプロパティ値を CSS に変換して `<style>` に記載。`a-px2rem()` は `(px / 1.6) / 10 * 1rem` で手動計算
2. **CSS カスタムプロパティ**: `--footer-bg-color` 等の動的値は `style` 属性で注入
3. **SP レイアウト**: `@media (max-width: 576px)` の代わりに、SP セクションの親に `style="width: 375px"` + インラインスタイルでレスポンシブ状態を再現
4. **変更箇所のハイライト**: `.highlight-box { outline: 3px solid #ef4444; }` で追加箇所を視覚的に強調
5. **最小限のHTML**: フッターだけの変更ならフッター部分のみ。ページ全体を再現する必要はない

## 前提条件

- `playwright` がインストール済み（`npm install playwright`）
- Chromium ブラウザが利用可能（Playwright が自動管理）

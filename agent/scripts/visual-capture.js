#!/usr/bin/env node
/**
 * visual-capture.js — ビジュアルレビュー用スクリーンショットキャプチャ
 *
 * HTML mockup ファイルの各セクションを PC/SP ビューポートでキャプチャする。
 * /review, /ai-review で画面変更をビジュアル検証する際に使用。
 *
 * Usage:
 *   node .claude/scripts/visual-capture.js <mockup.html> [--out <dir>] [--sections id1,id2,...]
 *
 * Options:
 *   <mockup.html>     キャプチャ対象の HTML mockup ファイルパス（必須）
 *   --out <dir>        スクリーンショット出力先（デフォルト: mockup と同じディレクトリ）
 *   --sections <ids>   カンマ区切りのセクション ID（デフォルト: 全 .mockup-section を自動検出）
 *   --pc-width <px>    PC ビューポート幅（デフォルト: 1280）
 *   --sp-width <px>    SP ビューポート幅（デフォルト: 375）
 *
 * セクション ID の命名規則:
 *   {viewport}-{variant}-{state}
 *   例: pc-oem-before, sp-oem-after, pc-original
 *
 * 出力: 各セクション ID と同名の PNG ファイル
 *
 * 前提:
 *   - playwright がインストール済み（npm install playwright）
 *   - Chromium ブラウザが利用可能
 *
 * mockup HTML の構造:
 *   <div class="mockup-section" id="pc-oem-after">
 *     <div class="mockup-label">ラベルテキスト</div>
 *     <div style="width: 1280px;">  ← ビューポート幅を明示
 *       <!-- 実際のコンポーネント HTML -->
 *     </div>
 *   </div>
 */

const { chromium } = require('playwright');
const path = require('path');

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === '--help') {
    console.log('Usage: node visual-capture.js <mockup.html> [--out <dir>] [--sections id1,id2,...]');
    process.exit(args[0] === '--help' ? 0 : 1);
  }

  const mockupPath = path.resolve(args[0]);
  let outDir = path.dirname(mockupPath);
  let sectionFilter = null;
  let pcWidth = 1280;
  let spWidth = 375;

  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--out' && args[i + 1]) {
      outDir = path.resolve(args[++i]);
    } else if (args[i] === '--sections' && args[i + 1]) {
      sectionFilter = args[++i].split(',').map(s => s.trim());
    } else if (args[i] === '--pc-width' && args[i + 1]) {
      pcWidth = parseInt(args[++i], 10);
    } else if (args[i] === '--sp-width' && args[i + 1]) {
      spWidth = parseInt(args[++i], 10);
    }
  }

  const browser = await chromium.launch();

  try {
    // Discover sections
    const discoveryPage = await browser.newPage({ viewport: { width: pcWidth, height: 900 } });
    await discoveryPage.goto('file://' + mockupPath);

    let sections;
    if (sectionFilter) {
      sections = sectionFilter.map(id => ({ id }));
    } else {
      sections = await discoveryPage.$$eval('.mockup-section[id]', els =>
        els.map(el => ({ id: el.id }))
      );
    }
    await discoveryPage.close();

    if (sections.length === 0) {
      console.error('No sections found. Add id attributes to .mockup-section elements.');
      process.exit(1);
    }

    console.log(`Found ${sections.length} sections: ${sections.map(s => s.id).join(', ')}`);

    // Capture each section
    for (const s of sections) {
      // Determine viewport width from section ID prefix
      const width = s.id.startsWith('sp-') ? spWidth : pcWidth;
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto('file://' + mockupPath);

      const el = await page.locator('#' + s.id);
      const count = await el.count();
      if (count === 0) {
        console.warn(`  SKIP: #${s.id} not found`);
        await page.close();
        continue;
      }

      const outPath = path.join(outDir, s.id + '.png');
      await el.screenshot({ path: outPath });
      console.log(`  Captured: ${outPath}`);
      await page.close();
    }
  } finally {
    await browser.close();
  }

  console.log('Done');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

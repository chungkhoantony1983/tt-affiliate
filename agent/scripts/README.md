# scripts/

フレームワーク運用に必要なスクリプト群。同期・エクスポート・導出・検証の4カテゴリに分類される。

## スクリプト一覧（機能別）

### 同期（sync）

| ファイル | 用途 |
|---------|------|
| `sync.sh` | SSoT を全リポに配布（ファイルコピー + コミット） |
| `sync_codex_skills.sh` | Codex 用スキルのシンボリックリンク作成 |
| `verify-sync.sh` | SSoT と各リポの `.claude/` のバイト一致を検証 |

### エクスポート（export）

| ファイル | 用途 |
|---------|------|
| `export_csv_to_excel.py` | CSV → Excel 変換 |
| `export_markdown_to_pdf.py` | Markdown → PDF 変換（WeasyPrint） |
| `export_project_deliverables.py` | PJ 成果物一括エクスポート |
| `export_slides_pdf.py` | スライド → PDF エクスポート |
| `export_wbs_gantt.py` | WBS → ガントチャート Excel 出力 |

### 導出（derive）

| ファイル | 用途 |
|---------|------|
| `derive_estimate.py` | 見積もり導出 |
| `derive_fte.py` | FTE（工数）導出 |
| `derive_resources.py` | リソース配分導出 |
| `derive_wbs_schedule.py` | WBS スケジュール導出 |
| `pj_derive_common.py` | 導出スクリプト共通ユーティリティ |

### 検証（validate）

| ファイル | 用途 |
|---------|------|
| `validate_artifact_graph.py` | 成果物依存グラフの整合性検証 |
| `validate_artifact_paths.py` | 成果物パスの存在検証 |
| `validate_schema_v2.py` | スキーマ v2 バリデーション |
| `validate_skill_workflow.py` | スキルワークフロー定義の検証 |

### 変換・準備（convert / prepare）

| ファイル | 用途 |
|---------|------|
| `convert_md_to_html.py` | Markdown → HTML 変換 |
| `convert_to_deliverables.py` | 成果物形式への変換 |
| `prepare_slides_markdown.py` | スライド用 Markdown の前処理 |

### フィルタ・マイグレーション

| ファイル | 用途 |
|---------|------|
| `filter_rules.py` | `learned-rules.yaml` からリポ固有ルールを抽出・配信 |
| `migrate_learned_rules_v2.py` | learned-rules v1 → v2 マイグレーション |

### その他

| ファイル | 用途 |
|---------|------|
| `visual-capture.js` | Playwright によるスクリーンショットキャプチャ |
| `mermaid-config.json` | Mermaid 図の描画設定 |
| `styles/` | エクスポート用 CSS スタイル |

## 命名規則

- `{category}_{name}.py` — Python スクリプト（category: sync/export/derive/validate/filter/convert/prepare/migrate）
- `{name}.sh` — シェルスクリプト
- `{name}.js` — Node.js スクリプト

## 関連

- `../CLAUDE.md` — SSoT 索引（各スクリプトの正本定義）
- `../references/` — スクリプトが参照する設定・スキーマ
- `styles/` — `export_markdown_to_pdf.py` が使用する CSS

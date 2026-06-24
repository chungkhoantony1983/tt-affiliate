# ドキュメントスタイルガイド

> **SSoT**: `.claude/references/guides/document-style-guide.md` が正本。`/sync` で全リポに配布される。

## docs/ ディレクトリの命名規則

### 命名体系

| 体系 | 使用箇所 | 例 | 特徴 |
|:----:|:---------|:---|:-----|
| **番号型** | PM・ドキュメント管理 | `0_Project/`, `2_Scope/` | 工程ゲート対応。順序が自明 |
| **英語名型** | 開発・機能モジュール | `specs/`, `capabilities/`, `design/` | 開発者にとって直感的 |

### 使い分けルール

**原則**: 用途によって使い分ける。同一ディレクトリ内で混在させない。

| 用途 | 推奨型 | 理由 |
|:----------|:------:|:-----|
| **ドキュメント管理** | 番号型 | フェーズ・工程の順序を自明にする |
| **開発・capabilityモジュール** | 英語名型 | 機能名が直接わかる |
| **設定・フレームワーク** | 英語名型 | 全モジュール共通の中立的な命名 |

### 禁止事項

- 同一リポ内で番号型と英語名型を混在させない
- 番号型リポの番号体系を勝手に変更しない（工程ゲートと連動しているため）

## ファイル命名規則

### 共通ルール

| 対象 | パターン | 例 |
|:-----|:---------|:---|
| ソースファイル | `{kebab-case}.{ext}` | `auth-service.ts`, `user-model.py` |
| エクスポート成果物 | `{document-name}_{version}_{date}.{ext}` | `proposal_v1.0_2026-03-06.pdf` |
| DR | `{topic-slug}.md` | `api-redesign.md`, `auth-fix.md` |
| 設定ファイル | `{name}.yaml` / `{name}.json` | `config.yaml`, `teams.yaml` |
| テンプレート | `{name}-template.{ext}` | `dr-workplan-template.md` |
| スキーマ | `{name}-schema.yaml` | `pj-config-schema.yaml` |
| ガイド | `{topic}-guide.md` / `{topic}-standard.md` | `development-guide.md` |

### README.md の配置

- 各ディレクトリの README.md はそのディレクトリの SSoT（内容物・命名規則・関連情報）
- 成果物ディレクトリの README.md にはエクスポート命名規則を記載する
- テンプレート: `.claude/references/templates/readme-template.md`（3段階成熟度モデル）

## 関連

- `../templates/readme-template.md` — README テンプレート
- `./export-standard.md` — エクスポート標準（配置・命名の詳細ルール）

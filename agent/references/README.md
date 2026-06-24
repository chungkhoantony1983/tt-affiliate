# references/

フレームワーク運用に必要なリファレンス資料・設定・テンプレートを集約するディレクトリ。`/sync` で全リポに配布される（`repo-registry.md` のみ除外）。

## ディレクトリ構成

```
references/
├── README.md                # このファイル
├── repo-registry.md         # SSoT識別マーカー（配布先には含まれない）
├── config/                  # プロバイダー設定・ドメイン定義
│   ├── config.yaml          #   プロバイダー設定（APIキー・デフォルトモデル）
│   └── teams.yaml           #   ドメイン×ワークフロー×ペルソナ×制約
├── guides/                  # 運用ガイド・リファレンス
│   ├── development-guide.md #   開発運用ガイド（各リポ docs/ に配布）
│   ├── export-standard.md   #   エクスポート標準
│   ├── presentation-frameworks.md # プレゼンフレームワーク（6種）
│   ├── role-workflow-guide.md     # 作業ペルソナ・ワークフロー
│   └── visual-review-guide.md    # ビジュアルレビュー
├── schemas/                 # YAML スキーマ定義
│   ├── pj-config-schema.yaml     # PJ パラメータスキーマ
│   └── artifact-graph-schema.yaml # 成果物依存グラフスキーマ
├── templates/               # テンプレート（新規ファイル作成のコピー元）
│   ├── dr-workplan-template.md   # DR 作業計画テンプレート
│   ├── brief-template.yaml       # ブリーフテンプレート
│   ├── readme-template.md        # README テンプレート（3段階成熟度）
│   ├── slide-skeleton.html       # HTML スライド骨格（TYPE-A〜D）
│   ├── pj-templates/             # PJ 初期化テンプレート群
│   └── artifact-graph-templates/ # 成果物グラフテンプレート（type-a/b/c）
└── rules/                   # 学習ルール・改善計画
    ├── learned-rules.yaml   #   学習ルール（bridge / permanent）
    └── improvement-backlog.yaml # 改善計画
```

## サブディレクトリ

| ディレクトリ | 用途 | 詳細 |
|:------------|:-----|:-----|
| `config/` | 設定ファイル | platform CLI が自動検出。プロバイダー・ドメイン定義 |
| `guides/` | 運用ガイド | 開発規約・エクスポート標準・プレゼンFW・レビューガイド |
| `schemas/` | スキーマ | PJ 初期化・成果物グラフの構造定義 |
| `templates/` | テンプレート | DR・ブリーフ・README・スライド・PJ 初期化のコピー元 |
| `rules/` | ルール・改善計画 | 学習ルール（SSoT）・改善バックログ |

## 命名規則

- 設定: `{name}.yaml`
- ガイド: `{topic}-guide.md` / `{topic}-standard.md`
- スキーマ: `{name}-schema.yaml`
- テンプレート: `{name}-template.{ext}`

## 関連

- `../CLAUDE.md` — SSoT 索引（各ファイルの正本定義）
- `../scripts/filter_rules.py` — `rules/learned-rules.yaml` のリポ固有フィルタリング
- `../skills/` — スキルが参照するリファレンス

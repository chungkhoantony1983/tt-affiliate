# hooks/

Claude Code の PreToolUse / PostToolUse / Stop / SessionStart フック。`settings.json` で登録され、ツール実行時に自動起動する。全フックは Python 3 で実装。

## フック一覧と実行順序

### PreToolUse（Write | Edit | Bash にマッチ）

ファイル書き込み・シェル実行の**前**に実行される。

| 順序 | ファイル | 機能 |
|:----:|---------|------|
| 1 | `context_lock_guard.py` | **GL-001**: `.context-locks/` 内のロックファイルを読み、書き込み先パスがロック範囲内か検証。範囲外はブロック |
| 2 | `validate_rules.py` | `learned-rules.yaml` のルールに基づく事前検証 |

### PostToolUse（Write | Edit にマッチ）

ファイル書き込みの**後**に実行される。

| 順序 | ファイル | 機能 |
|:----:|---------|------|
| 1 | `post_validate_rules.py` | 書き込み結果のルール事後検証 |

### Stop

セッション終了時に実行される。

| ファイル | 機能 |
|---------|------|
| `auto_learn.py` | セッション中のフィードバックを検出し、`.pending-feedback.json` に保存（async, timeout: 60s） |

### SessionStart

セッション開始時に実行される。

| ファイル | 機能 |
|---------|------|
| `session_start.py` | `.pending-feedback.json` を読み込み、前セッションのフィードバックをコンテキストに注入 |

## 依存関係

```
settings.json          → フック登録（matcher + command）
context_lock_guard.py  → logs/.context-locks/*（ロックファイル読み取り）
validate_rules.py      → references/rules/learned-rules.yaml
post_validate_rules.py → references/rules/learned-rules.yaml
auto_learn.py          → logs/.pending-feedback.json（書き込み）
session_start.py       → logs/.pending-feedback.json（読み取り）
```

## 変更・追加ルール

- 新規フック追加時は `settings.json` にも登録すること
- フック内で外部 API を呼ばないこと（レイテンシ影響）
- `_feedback_utils.py` は `auto_learn.py` / `auto_learn_lite.py` の共有ユーティリティ

## 関連

- `../settings.json` — フック登録設定
- `../logs/` — ランタイム状態ファイル（.context-locks, .pending-feedback.json）
- `../references/rules/learned-rules.yaml` — 学習ルール（validate_rules が参照）

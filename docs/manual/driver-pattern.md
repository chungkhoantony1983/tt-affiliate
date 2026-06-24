# Engine driver pattern (AI / SDK 開発者向け)

> **対象読者**: AI agent (Claude Code / Codex) / Python SDK 経由で `Engine.advance()` を呼ぶ開発者。
>
> **エンドユーザー (営業 / エンジニア) 向けの利用マニュアルは [`USAGE.md`](USAGE.md) を参照。**
>
> **SSoT**: 本ファイル (`docs/manual/driver-pattern.md`、Issue #375 で `USAGE.md` から分離) = Engine の **driver loop pattern + advance() 呼び出し方** の正本。Production driver pattern (skill 経由実行 / paused 状態 / streaming / smoke test pattern) を declared する。
>
> **scope 限定**: Engine の **使用方法 (driver pattern)** のみ。設計プロセス / 配置規範 / GitHub 運用 は 4 ガイド (DPG / APG / PPG / DG) を参照。skill 一覧は `CLAUDE.md §skill 一覧` を参照。

## 実行環境

```bash
# Python 3.12 (miniforge3 automation_engine 環境)
~/miniforge3/envs/automation_engine/bin/python3

# 作業ディレクトリ
cd ~/automation_engine

# 環境変数
export PYTHONPATH=src
export GWS_TOKEN_FILE=~/.config/automation_engine/gws_token.json
```

## Engine の呼び方

**重要: Engine.advance() は async。必ず `asyncio.run()` + `await` で呼ぶ。**

### conversation（自由な質問・調査）

```python
import asyncio, sys, os
sys.path.insert(0, "src")

async def main():
    from core import Engine
    e = Engine()
    r = await e.advance(
        thread_id=None,
        expected_version=0,
        user_input="ここに質問や指示を書く",
    )
    print(r.output.get("response", ""))

asyncio.run(main())
```

### /review（コードレビュー）

`/script` 起動 + 完走までの production driver pattern。詳細は本 doc の **Production driver pattern** 節参照。

```python
import asyncio, sys
sys.path.insert(0, "src")

async def main():
    from core import Engine
    e = Engine()

    # turn 1: /script 起動 (workflow start のみで step は実行されない)
    r = await e.advance(
        thread_id=None, expected_version=0,
        user_input="/review PR#7095 @backend",
    )

    # turn 2+: workflow を進めるため loop で advance() を呼ぶ
    # production driver pattern: engine DONE signal で exit、user 意思を捏造しない
    while True:
        if r.status in ("closed", "failed"):
            break  # thread 終端
        if isinstance(r.output, dict) and r.output.get("script_finished"):
            break  # workflow 完走 signal
        if r.status == "paused":
            # production では UI で real user に確認 → user の意思を approve に反映
            # (driver が autonomous で approve=True しない、smoke 等の test は別 pattern)
            user_decision = await ask_real_user_about_pause(r.pause_summary)  # 例
            if user_decision == "approve":
                r = await e.advance(thread_id=r.thread_id, expected_version=r.version, approve=True)
            else:
                break  # user が判断保留 / abort
            continue
        if r.mode == "conversation" and r.needs_input:
            break  # workflow 完走後の real user 次入力待ち → driver は exit (Issue #255)
        # workflow 進行中 (mode=workflow) or 1st turn — engine が次 step を駆動するので advance を呼ぶ
        r = await e.advance(thread_id=r.thread_id, expected_version=r.version)

    print(r.output.get("response", "") if isinstance(r.output, dict) else "")

asyncio.run(main())
```

> ⚠️ 上記は production driver の例。**`user_input="続けてください"` を fake input として投入する pattern は anti-pattern** (本 doc の Production driver pattern 節参照)。
> test/regression smoke の pattern は別途 [`docs/testing/smoke-pattern.md`](../testing/smoke-pattern.md) 参照。

### ワンライナー

```bash
cd ~/automation_engine && \
PYTHONPATH=src ~/miniforge3/envs/automation_engine/bin/python3 -c "
import asyncio, sys; sys.path.insert(0, 'src')
async def main():
    from core import Engine
    e = Engine()
    r = await e.advance(thread_id=None, expected_version=0, user_input='ここに指示')
    print(r.output.get('response', ''))
asyncio.run(main())
"
```

## advance() 引数リファレンス

| 引数 | 型 | デフォルト | 用途 |
|------|----|-----------|------|
| `thread_id` | `str \| None` | — | 既存 Thread を継続する場合に指定。`None` で新規作成 |
| `expected_version` | `int` | — | 楽観ロック用バージョン。新規は `0`、継続は `r.version` |
| `user_input` | `str \| dict \| None` | `None` | ユーザー入力テキストまたはスクリプト指示 |
| `context` | `dict \| None` | `None` | 追加コンテキスト情報 |
| `approve` | `bool` | `False` | paused 状態の承認 |
| `abort` | `bool` | `False` | Thread を failed に遷移（中止） |
| `on_token` | `Callable \| None` | `None` | ストリーミング出力コールバック |
| `owner_id` | `str` | `""` | Thread オーナー ID |

## paused 状態のハンドリング

`advance()` の戻り値 `r.status == "paused"` は、Engine がツール実行の承認を待っている状態。
paused tool の id は `r.pause_summary` 文字列に含まれる (`"ツール 'gh-merger' の実行を保留しています..."`)。

production driver は user に判断を仰ぎ、real user の承認意思を `approve=True` で伝達する。
**driver が user 意思を捏造して `approve=True` を打ってはならない** (catastrophe path: PR #163 autonomous main merge)。

## Production driver pattern

Claude Chat / agent runtime / production 用 client は **user proxy** として automation engine を駆動する。
real user の意思のみを伝達し、engine の DONE signal で loop を exit する。

### 設計原則 (user proxy contract)

1. **real user の意思のみ伝達**: `user_input` には real user が打った文字列、または skill/slash 指示を渡す。**driver が文字列を捏造して投入してはならない** (例: `user_input="続けてください"` で空気を読ませる pattern は禁止)。
2. **engine DONE signal を respect**: 以下の条件で driver は loop を exit する:
   - `r.status in ("closed", "failed")` — thread 終端
   - `r.output.get("script_finished") is True` — workflow 完走 signal
   - **`r.mode == "conversation" and r.needs_input` — workflow 終了後 real user 入力待ち** (Issue #255: mode を見ないと workflow 1st turn でも誤 break する)
3. **paused 状態は real user の判断**: high-risk side_effect tool は user に確認を取る。盲目的 `approve=True` は禁止。

### 推奨 production driver pattern

```python
# Issue #256 self-review B-1: 防衛的上限。engine が想定外状態 (mode=None 固着等)
# を返した場合の無限ループを防ぐ。実機 workflow は 5-10 step、~20 turn で完走する
# ため 100 は十分な margin。production では適宜 metric / alert 連携推奨。
MAX_DRIVER_TURNS = 100


async def production_driver(engine, user_input):
    """real user の発話を engine に伝達し、completion で exit する driver。"""
    r = await engine.advance(thread_id=None, expected_version=0, user_input=user_input)

    for turn in range(MAX_DRIVER_TURNS):
        # engine DONE signal で exit
        if r.status in ("closed", "failed"):
            return r
        if isinstance(r.output, dict) and r.output.get("script_finished"):
            return r  # workflow 完走 → user proxy は exit

        # paused: real user 判断を仰ぐ (driver が autonomous 承認しない)
        if r.status == "paused":
            # production では UI で user に確認を表示 → user の意思を approve に反映
            user_decision = await ask_real_user_about_pause(r.pause_summary)
            if user_decision == "approve":
                r = await engine.advance(thread_id=r.thread_id, expected_version=r.version, approve=True)
            elif user_decision == "abort":
                r = await engine.advance(thread_id=r.thread_id, expected_version=r.version, abort=True)
            else:
                return r  # user が判断保留 → driver は exit
            continue

        # real user 次入力待ち (mode=conversation, needs_input=True)
        # → driver は exit。次の real user 発話で改めて advance() を呼ぶ
        # Issue #255: mode 必須。needs_input は workflow 1st turn / 進行中でも True が立つため、
        # mode を見ないと workflow が 1 step も進まずに break する。
        if r.mode == "conversation" and r.needs_input:
            return r

        # workflow 進行中 (mode=workflow) or 1st turn → 次 step を engine 側で駆動
        r = await engine.advance(thread_id=r.thread_id, expected_version=r.version)

    # MAX_DRIVER_TURNS 到達 = engine が DONE signal を返さない異常状態。
    # 本サンプルは "must abort" の意図で RuntimeError を raise (test/CI 用には明示的失敗が分かりやすい)。
    # production では用途に応じて以下のいずれかへ置換推奨:
    #   - graceful return: `return r` で caller に異常状態 AdvanceResult を委ねる (UI 側で error 表示)
    #   - structured event: `await metric.alert(...) ; return r` で alert 発火 + return
    #   - deferred re-try: thread_id を queue に push して別プロセスで継続 (long-running 対応)
    # いずれの場合も thread_id / status / mode / needs_input を必ず log に残し investigation 可能にする。
    raise RuntimeError(
        f"production_driver: MAX_DRIVER_TURNS={MAX_DRIVER_TURNS} 到達。"
        f"thread_id={r.thread_id}, status={r.status}, mode={r.mode}, "
        f"needs_input={r.needs_input}. engine DONE signal 異常を investigation 必要。"
    )
```

### アンチパターン (production で禁止)

```python
# ❌ NG: driver が user 意思を捏造して loop を駆動
while r.status != "completed":
    if r.status == "active" and r.needs_input:
        r = await engine.advance(user_input="続けてください")  # ← user の意思ではない
```

このパターンは workflow 完走後の `mode=conversation, needs_input=True` で driver が
**fake user input を engine に流し込み**、agenticLLM が「続けて」を真の user 指示として
improvise する root cause になる (例: 当初 scope 外の autonomous PR review post)。

### 関連

- **テスト用 driver pattern** (smoke / e2e regression test): [`docs/testing/smoke-pattern.md`](../testing/smoke-pattern.md) を参照
  (production driver はこれを参照しない。test scaffolding 用)
- **paused state の意味論**: 上記「paused 状態のハンドリング」節
- **engine DONE signal**: `r.output.script_finished` (Issue #105 設計)

## 注意事項

- `Engine()` のデフォルトは `site.yaml` を cwd から探す → **必ず `cd ~/automation_engine` してから実行**
- `advance()` は **1 turn 単位で return する**:
  - `/script` 起動時 (例: `/review PR#N`): workflow を start するのみで step は実行されない (graph: `route→slash→finalize→END`)。`r.status="active"`、`r.current_step="resolve"` 等が返る
  - 以降の turn: `advance(thread_id=r.thread_id, expected_version=r.version)` を **user_input なし** で呼ぶと `route→recall→inference→...` 経路で AgenticGateway 内で workflow steps が連続実行される
  - 全 step 完走 / pause / fail まで進めるには **loop で advance() を呼び続ける**。詳細は本 doc の **Production driver pattern** 節参照
  - ⚠️ **`user_input="続けてください"` で空気を読ませる pattern は anti-pattern** (driver が user 意思を捏造する違反)
- on_token callback でストリーミング出力可能:
  ```python
  r = await e.advance(..., on_token=lambda t: print(t, end="", flush=True))
  ```

#!/usr/bin/env python3
from __future__ import annotations
"""SessionStart hook: hooks 陳腐化検出 + pending feedback 通知 + open work-log 検出 + SSoT索引検証。

1. learned-rules.yaml の hash と .hook-hash を比較し、
   不一致なら compile-hooks で自動再コンパイル
2. .pending-feedback.json が3件以上あれば通知
3. open な work-log を検出してセッションに注入
5c. open work-log の ssot_impact 妥当性チェック（PJファイル誤分類検出）
7. SSoT索引パスの存在検証（GL-007: staleness 検出）
"""
import glob as glob_mod
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    cwd = data.get("cwd", "")
    claude_dir = Path(cwd) / ".claude"
    messages: list[str] = []

    # === 0. セッションID生成・永続化（GL-011） ===
    session_id_file = claude_dir / "logs" / ".session-id"
    session_id = ""
    try:
        if session_id_file.is_file():
            session_id = session_id_file.read_text().strip()
        if not session_id:
            session_id = uuid.uuid4().hex[:8]
            session_id_file.parent.mkdir(parents=True, exist_ok=True)
            session_id_file.write_text(session_id + "\n")
        messages.append(f"あなたのセッションID: {session_id}")
    except OSError:
        pass  # フェイルオープン

    # === 1. validate_rules.py 存在保証 + 陳腐化検出 ===
    validate_script = claude_dir / "hooks" / "validate_rules.py"
    hash_file = claude_dir / "logs" / ".hook-hash"
    rules_dir = claude_dir / "references" / "rules"
    rules_file = rules_dir / "learned-rules.yaml"  # 後方互換

    def _compute_rules_hash() -> str | None:
        """ルールファイル群のハッシュを計算。ディレクトリ/単一ファイル両対応。"""
        h = hashlib.sha256()
        # IMP-072: ドメイン別 YAML ファイルが存在する場合はディレクトリハッシュ
        yamls = sorted(
            f for f in rules_dir.glob("*.yaml")
            if f.name != "improvement-backlog.yaml"
            and not f.name.endswith(".bak")
        ) if rules_dir.is_dir() else []
        if yamls:
            for yf in yamls:
                h.update(yf.read_bytes())
            return h.hexdigest()[:16]
        # 後方互換: 単一ファイル
        if rules_file.exists():
            return hashlib.sha256(rules_file.read_bytes()).hexdigest()[:16]
        return None

    needs_compile = False
    if not validate_script.exists():
        # validate_rules.py がない → 即座に生成（デッドロック防止）
        needs_compile = True
    elif hash_file.exists():
        current_hash = _compute_rules_hash()
        if current_hash:
            saved_hash = hash_file.read_text().strip()
            if saved_hash != current_hash:
                needs_compile = True

    if needs_compile:
        try:
            subprocess.run(
                [
                    "python3", "-m", "automation_engine", "compile-hooks",
                    "--output",
                    str(validate_script),
                ],
                timeout=10,
                capture_output=True,
            )
            messages.append(
                "hooks を自動生成/再コンパイルしました"
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            messages.append(
                "⚠ hooks の生成に失敗。"
                "手動で `python -m automation_engine compile-hooks` を実行してください"
            )

    # === 2. pending feedback 通知（1件以上で通知 — IMP-026） ===
    pending = claude_dir / "logs" / ".pending-feedback.json"
    if pending.exists():
        try:
            fb = json.loads(pending.read_text())
            count = fb.get("count", 0)
            recurrences = len(fb.get("recurrences", []))
            items = fb.get("feedbacks", [])
            if count >= 1:
                # フィードバック内容をサマリとして注入（AI が再発を防げるように）
                summary_lines = []
                for item in items[:5]:  # 最大5件
                    domain = item.get("domain", "global")
                    text = item.get("text", "")[:100]
                    summary_lines.append(f"  [{domain}] {text}")
                detail = "\n".join(summary_lines) if summary_lines else ""
                msg = (
                    f"⚠ 前回セッションで {count}件のフィードバック検出"
                    f"（既存ルール違反 {recurrences}件）。\n"
                    f"以下の指摘を本セッションでも遵守してください:\n{detail}\n"
                    f"永続化するには `/ai-learn` を実行してください。"
                )
                messages.append(msg)
        except (json.JSONDecodeError, KeyError):
            pending.unlink(missing_ok=True)

    # === 3. bridge ルール GC チェック (IMP-071) ===
    try:
        gc_result = subprocess.run(
            ["python3", "-m", "automation_engine", "preset", "gc", "--check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if gc_result.returncode == 0 and gc_result.stdout.strip():
            messages.append(gc_result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # === 4. MEMORY.md 汚染検出（セッション固有情報の混入防止） ===
    memory_dir = Path.home() / ".claude" / "projects"
    if memory_dir.is_dir():
        # CLAUDE_PROJECT_DIR からプロジェクトハッシュを推定
        for proj_dir in memory_dir.iterdir():
            memory_file = proj_dir / "memory" / "MEMORY.md"
            if not memory_file.is_file():
                continue
            try:
                content = memory_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            # セッション固有パターンを検出
            contamination_patterns = [
                "進行中セッション",
                "現在の作業",
                "このセッションの目的",
                "セッション目的",
                "進行中タスク",
            ]
            found = [p for p in contamination_patterns if p in content]
            if found:
                messages.append(
                    f"⚠ MEMORY.md にセッション固有の情報が混入しています: "
                    f"{', '.join(found)}\n"
                    f"  → セッション固有の目的・進捗は work-log に記録してください。\n"
                    f"  → MEMORY.md からセッション固有セクションを削除してください。"
                )
            break  # 最初にマッチしたプロジェクトのみチェック

    # === 5. open work-log 検出・セッション注入 ===
    work_logs_dir = claude_dir / "logs" / "work-logs"
    if work_logs_dir.is_dir():
        open_logs: list[dict[str, str]] = []
        for wl in sorted(work_logs_dir.glob("*.md")):
            try:
                content = wl.read_text(encoding="utf-8")
                # frontmatter から status と unified_purpose を抽出
                fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                if not fm_match:
                    continue
                fm = fm_match.group(1)
                status_match = re.search(r'^status:\s*"?(\w+)"?', fm, re.MULTILINE)
                purpose_match = re.search(
                    r'^unified_purpose:\s*"?(.+?)"?\s*$', fm, re.MULTILINE
                )
                if status_match and status_match.group(1) == "open":
                    purpose = (
                        purpose_match.group(1) if purpose_match else "(目的未記載)"
                    )
                    open_logs.append({"file": wl.name, "purpose": purpose})
            except (OSError, UnicodeDecodeError):
                continue
        if open_logs:
            log_lines = []
            for ol in open_logs[:10]:  # 最大10件
                log_lines.append(f"  - {ol['file']}: {ol['purpose']}")
            detail = "\n".join(log_lines)
            messages.append(
                f"📋 引き継ぎ可能な work-log が {len(open_logs)}件あります:\n"
                f"{detail}\n"
                f"引き継ぐ場合は該当 work-log を Read して `[PURPOSE-LOCKED]` を確認してください。"
            )

    # === 5c. ssot_impact 妥当性チェック（P-008: PJファイル誤分類検出） ===
    # open work-log の ssot_impact が PJ固有ファイルを含んでいないかチェック
    if work_logs_dir.is_dir():
        ssot_index_paths: set[str] = set()
        # SSoT索引からパスを収集
        if ssot_claude_md.is_file():
            try:
                md_c = ssot_claude_md.read_text(encoding="utf-8")
                idx_m = ssot_idx_re.search(md_c)
                if idx_m:
                    for ln in idx_m.group(1).split("\n"):
                        if ln.startswith("|") and "正本ファイル" not in ln and "---" not in ln:
                            for p in path_pattern.findall(ln):
                                ssot_index_paths.add(p)
            except (OSError, UnicodeDecodeError):
                pass
        if ssot_index_paths:
            for wl in sorted(work_logs_dir.glob("*.md")):
                try:
                    wl_content = wl.read_text(encoding="utf-8")
                    wl_fm = re.match(r"^---\n(.*?)\n---", wl_content, re.DOTALL)
                    if not wl_fm:
                        continue
                    wl_fm_text = wl_fm.group(1)
                    # status: open のみ対象
                    st = re.search(r'^status:\s*"?(\w+)"?', wl_fm_text, re.MULTILINE)
                    if not st or st.group(1) != "open":
                        continue
                    # ssot_impact を抽出
                    si = re.search(
                        r'^ssot_impact:\s*(.+?)(?:\n\w|\n---|\Z)',
                        wl_fm_text,
                        re.MULTILINE | re.DOTALL,
                    )
                    if not si:
                        continue
                    si_text = si.group(1).strip()
                    if si_text in ('"none"', "none", '""', ""):
                        continue
                    # YAML list 形式からパスを抽出
                    si_paths = re.findall(r'-\s*["\']?([^"\'#\n]+)', si_text)
                    non_ssot = [
                        sp.strip()
                        for sp in si_paths
                        if sp.strip() and sp.strip() not in ssot_index_paths
                        and not sp.strip().startswith("CLAUDE.md")
                        and not any(sp.strip().startswith(sip) or sip.startswith(sp.strip()) for sip in ssot_index_paths)
                    ]
                    if non_ssot:
                        ns_list = ", ".join(non_ssot[:5])
                        messages.append(
                            f"⚠ {wl.name}: ssot_impact に SSoT索引外のファイルが含まれています: {ns_list}\n"
                            f"  → PJ固有ファイルは ssot_impact の対象外です（work-log のデータ定義に記載）。"
                        )
                except (OSError, UnicodeDecodeError):
                    continue

    # === 5b. stale worklog-lock cleanup (GL-004) ===
    worklog_locks_dir = claude_dir / "logs" / ".worklog-locks"
    if worklog_locks_dir.is_dir():
        for lf in worklog_locks_dir.iterdir():
            if lf.name.startswith("."):
                continue
            try:
                owner_pid = int(lf.read_text().strip())
                os.kill(owner_pid, 0)  # プロセス生存確認（signal 0）
                # 例外なし → プロセス存在 → ロック有効、何もしない
            except ValueError:
                # PID が数値でない → 壊れたロック → 削除
                lf.unlink(missing_ok=True)
            except ProcessLookupError:
                # ESRCH: プロセス不在 → stale lock → 削除
                lf.unlink(missing_ok=True)
            except PermissionError:
                # EPERM: プロセス存在するが権限なし → ロック有効
                pass
            except OSError:
                pass  # その他のエラー → フェイルオープン

    # === 6. stale lock cleanup (GL-001) ===
    locks_dir = claude_dir / "logs" / ".context-locks"
    if locks_dir.is_dir():
        now = time.time()
        for f in locks_dir.iterdir():
            if f.name.startswith("."):
                continue
            try:
                if now - f.stat().st_mtime > 86400:
                    f.unlink()
            except OSError:
                pass

    # === 7. SSoT索引パス検証（GL-007: staleness 検出） ===
    # CLAUDE.md の SSoT 索引テーブルからパスを抽出し、実在を検証する
    cwd_path = Path(cwd)
    # テーブル行からバッククォート内のパスを抽出（Section 7/7b 共通）
    path_pattern = re.compile(r"`([a-zA-Z_.][a-zA-Z0-9_./-]+[a-zA-Z0-9_.*])`")
    # SSoT索引セクションの柔軟マッチ（「## SSoT 索引」「## ドキュメント SSoT 索引」等）
    ssot_idx_re = re.compile(r"##[^\n]*SSoT\s*索引\n(.*?)(?=\n## |\Z)", re.DOTALL)

    ssot_claude_md = claude_dir / "CLAUDE.md"
    if ssot_claude_md.is_file():
        try:
            md_content = ssot_claude_md.read_text(encoding="utf-8")
            idx_match = ssot_idx_re.search(md_content)
            if idx_match:
                idx_section = idx_match.group(1)
                stale_paths: list[str] = []
                for line in idx_section.split("\n"):
                    if not line.startswith("|") or "正本ファイル" in line or "---" in line:
                        continue
                    # 取消線（廃止）は除外
                    if "~~" in line:
                        continue
                    # sync対象外（platform）は除外
                    if "sync対象外" in line:
                        continue
                    paths_in_line = path_pattern.findall(line)
                    for p in paths_in_line:
                        # CLAUDE.md 自己参照は除外
                        if p == "CLAUDE.md":
                            continue
                        # 説明テキスト内のパスは除外
                        if p.startswith("docs/") and "配布" in line:
                            continue
                        # パス解決: .claude/ からと cwd からの両方を試す
                        candidates = [claude_dir / p, cwd_path / p]
                        if "*" in p:
                            found = any(
                                glob_mod.glob(str(c)) for c in candidates
                            )
                            if not found:
                                stale_paths.append(p)
                        elif not any(c.exists() for c in candidates):
                            stale_paths.append(p)
                if stale_paths:
                    stale_list = "\n".join(f"  - {p}" for p in stale_paths[:10])
                    messages.append(
                        f"⚠ GL-007: SSoT索引に {len(stale_paths)}件の不在パスを検出:\n"
                        f"{stale_list}\n"
                        f"  → CLAUDE.md の SSoT 索引を更新するか、不足ファイルを作成してください。"
                    )
        except (OSError, UnicodeDecodeError):
            pass

    # === 7b. リポ CLAUDE.md の SSoT索引パス検証 ===
    # 各リポのルート CLAUDE.md にも SSoT 索引がある場合、パスを検証
    repo_registry = claude_dir / "references" / "repo-registry.md"
    if repo_registry.is_file():
        # マルチリポ環境: repo-registry.md からリポ一覧を取得
        try:
            reg_content = repo_registry.read_text(encoding="utf-8")
            # テーブルから短縮名を抽出 (| 短縮名 | ...)
            repo_dirs: list[Path] = []
            for reg_line in reg_content.split("\n"):
                if not reg_line.startswith("|") or "短縮名" in reg_line or "---" in reg_line:
                    continue
                cols = [c.strip() for c in reg_line.split("|")]
                if len(cols) >= 3:
                    short_name = cols[1].strip("`").strip()
                    if short_name:
                        repo_path = cwd_path / short_name
                        if repo_path.is_dir():
                            repo_dirs.append(repo_path)
            # 各リポの CLAUDE.md を検証
            for repo_dir in repo_dirs:
                repo_claude = repo_dir / "CLAUDE.md"
                if not repo_claude.is_file():
                    continue
                try:
                    repo_md = repo_claude.read_text(encoding="utf-8")
                    repo_idx = ssot_idx_re.search(repo_md)
                    if not repo_idx:
                        continue
                    repo_stale: list[str] = []
                    for rline in repo_idx.group(1).split("\n"):
                        if not rline.startswith("|") or "正本ファイル" in rline or "---" in rline:
                            continue
                        if "~~" in rline:
                            continue
                        rpaths = path_pattern.findall(rline)
                        for rp in rpaths:
                            if rp == "CLAUDE.md":
                                continue
                            rfull = repo_dir / rp
                            if "*" in rp:
                                if not glob_mod.glob(str(rfull)):
                                    repo_stale.append(rp)
                            elif not rfull.exists():
                                repo_stale.append(rp)
                    if repo_stale:
                        stale_list = "\n".join(f"  - {rp}" for rp in repo_stale[:5])
                        messages.append(
                            f"⚠ GL-007: {repo_dir.name}/CLAUDE.md SSoT索引に "
                            f"{len(repo_stale)}件の不在パスを検出:\n"
                            f"{stale_list}"
                        )
                except (OSError, UnicodeDecodeError):
                    continue
        except (OSError, UnicodeDecodeError):
            pass

    # === 8. 非Gitフォルダの古いバックアップ削除（GL-008） ===
    # .claude-backups/ 内の7日以上古いディレクトリを削除
    try:
        from datetime import datetime as _dt, timedelta as _td

        retention_days = 7
        cutoff = _dt.now() - _td(days=retention_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        # repo-registry.md からローカルフォルダを検出、または cwd 直下を走査
        search_dirs: list[Path] = []
        registry = claude_dir / "references" / "repo-registry.md"
        if registry.is_file():
            # マルチリポ環境: cwd 直下の全ディレクトリを走査
            for child in cwd_path.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    backup_dir = child / ".claude-backups"
                    if backup_dir.is_dir():
                        search_dirs.append(backup_dir)
        else:
            # 単一リポ/ローカル環境
            backup_dir = cwd_path / ".claude-backups"
            if backup_dir.is_dir():
                search_dirs.append(backup_dir)

        cleaned = 0
        for bdir in search_dirs:
            for date_dir in sorted(bdir.iterdir()):
                if not date_dir.is_dir():
                    continue
                # ディレクトリ名が YYYY-MM-DD 形式か判定
                if len(date_dir.name) == 10 and date_dir.name < cutoff_str:
                    import shutil as _shutil

                    _shutil.rmtree(date_dir, ignore_errors=True)
                    cleaned += 1
        if cleaned > 0:
            messages.append(
                f"GL-008: 古いバックアップを {cleaned} 件削除しました（保持期間: {retention_days}日）"
            )
    except Exception:
        pass  # フェイルオープン

    if messages:
        msg = " | ".join(messages)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "systemMessage": msg,
                    }
                }
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)

#!/usr/bin/env python3
"""Branch observer: spot parallel work that touches the same files, suggest a merge order,
and clean up branches that are already merged.

Several Claude windows (VS Code, terminal) or several people may work in separate worktrees /
branches at the same time. This script looks at every worktree, local branch, remote branch and
PR, and reports which of them change the same files before anyone tries to merge.

Usage:
  python3 scripts/branch_observer.py report [--fetch] [--no-gh] [--json]
  python3 scripts/branch_observer.py prune  [--yes] [--fetch] [--no-gh]
  python3 scripts/branch_observer.py hook      # PreToolUse Write|Edit hook (reads JSON on stdin)
  python3 scripts/branch_observer.py session   # SessionStart hook: short summary, only if something is wrong

"Merged" means: the branch tip is already in origin/main, or a merged PR has exactly this tip
(squash / rebase merges). Prune never touches main, a worktree with uncommitted changes, or the
worktree the caller is running in.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from itertools import combinations
from pathlib import Path

BASE = "origin/main"
REMOTE = "origin"


def git(*args: str, cwd: str | None = None) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout.rstrip()  # keep leading spaces: `status --porcelain` needs them


def repo_root(start: str) -> str | None:
    rc, common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=start)
    return str(Path(common).parent) if rc == 0 else None


def worktrees(root: str) -> list[dict]:
    _, out = git("worktree", "list", "--porcelain", cwd=root)
    result, cur = [], {}
    for line in out.splitlines() + [""]:
        if not line:
            if cur:
                result.append(cur)
            cur = {}
        elif line.startswith("worktree "):
            cur["path"] = line[9:]
        elif line.startswith("HEAD "):
            cur["head"] = line[5:]
        elif line.startswith("branch "):
            cur["branch"] = line[7:].removeprefix("refs/heads/")
    return [w for w in result if Path(w["path"]).is_dir()]


def dirty_files(path: str) -> set[str]:
    rc, out = git("status", "--porcelain=v1", "--no-renames", "-uall", cwd=path)
    if rc != 0:
        return set()
    return {line[3:].strip('"') for line in out.splitlines() if len(line) > 3}


def changed_files(root: str, tip: str) -> set[str]:
    rc, out = git("diff", "--name-only", f"{BASE}...{tip}", cwd=root)
    return set(out.splitlines()) if rc == 0 and out else set()


def is_ancestor(root: str, a: str, b: str) -> bool:
    return git("merge-base", "--is-ancestor", a, b, cwd=root)[0] == 0


def merge_conflicts(root: str, a: str, b: str) -> list[str] | None:
    """Files that conflict when merging a and b; None if they merge cleanly."""
    rc, out = git("merge-tree", "--write-tree", "--name-only", "--no-messages", a, b, cwd=root)
    if rc == 0:
        return None
    lines = out.splitlines()[1:]
    return sorted(set(l for l in lines if l)) or ["(unknown)"]


def pull_requests(root: str) -> dict[str, list[dict]]:
    try:
        p = subprocess.run(
            ["gh", "pr", "list", "--state", "all", "--limit", "200",
             "--json", "number,state,headRefName,headRefOid,title"],
            cwd=root, capture_output=True, text=True, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if p.returncode != 0:
        return {}
    prs: dict[str, list[dict]] = {}
    for pr in json.loads(p.stdout or "[]"):
        prs.setdefault(pr["headRefName"], []).append(pr)
    return prs


def collect(root: str, use_gh: bool) -> dict:
    wts = worktrees(root)
    wt_by_branch = {w["branch"]: w for w in wts if "branch" in w}
    _, refs = git("for-each-ref", "--format=%(refname) %(objectname)",
                  "refs/heads", f"refs/remotes/{REMOTE}", cwd=root)
    branches: dict[str, dict] = {}
    for line in refs.splitlines():
        ref, sha = line.split()
        if ref.startswith("refs/heads/"):
            branches.setdefault(ref[11:], {})["local"] = sha
        else:
            name = ref[len(f"refs/remotes/{REMOTE}/"):]
            if name != "HEAD":
                branches.setdefault(name, {})["remote"] = sha
    prs = pull_requests(root) if use_gh else {}

    subjects = []
    for name, tips in sorted(branches.items()):
        if name == "main":
            continue
        tip = tips.get("local") or tips["remote"]
        wt = wt_by_branch.get(name)
        branch_prs = prs.get(name, [])
        merged_pr = next((p for p in branch_prs if p["state"] == "MERGED"
                          and p["headRefOid"] in tips.values()), None)
        open_pr = next((p for p in branch_prs if p["state"] == "OPEN"), None)
        in_base = is_ancestor(root, tip, BASE)
        # A fresh worktree branch cut from main is "in base" but is active work, not merged.
        merged = bool(merged_pr) or (in_base and not wt)
        subjects.append({
            "name": name,
            "tip": tip,
            "local": tips.get("local"),
            "remote": tips.get("remote"),
            "unpushed": bool(tips.get("local") and not in_base
                             and not (tips.get("remote") and is_ancestor(root, tips["local"], tips["remote"]))),
            "worktree": wt["path"] if wt else None,
            "dirty": sorted(dirty_files(wt["path"])) if wt else [],
            "committed": sorted(changed_files(root, tip)) if not merged else [],
            "merged": merged,
            "merged_pr": merged_pr["number"] if merged_pr else None,
            "open_pr": open_pr["number"] if open_pr else None,
        })

    # Local main: commits that never reached origin (what caused the 2026-11-12 divergence).
    _, ahead = git("rev-list", "--count", f"{BASE}..main", cwd=root)
    _, behind = git("rev-list", "--count", f"main..{BASE}", cwd=root)
    root_wt = next((w for w in wts if w["path"] == root), None)
    main_info = {
        "ahead": int(ahead or 0),
        "behind": int(behind or 0),
        "root_on_main": bool(root_wt and root_wt.get("branch") == "main"),
        "root_dirty": sorted(dirty_files(root)) if root_wt else [],
    }
    if main_info["ahead"]:
        subjects.append({
            "name": "main (local only)", "tip": "main", "local": None, "remote": None,
            "unpushed": True, "worktree": root, "dirty": main_info["root_dirty"],
            "committed": sorted(changed_files(root, "main")), "merged": False,
            "merged_pr": None, "open_pr": None,
        })
    return {"root": root, "subjects": subjects, "main": main_info}


def analyse(data: dict) -> dict:
    root = data["root"]
    # Empty branches (nothing committed, nothing edited) cannot collide with anything.
    active = [s for s in data["subjects"]
              if (not s["merged"] or s["dirty"]) and (s["committed"] or s["dirty"])]
    for s in active:
        s["base_conflicts"] = merge_conflicts(root, BASE, s["tip"]) if s["committed"] else None

    overlaps = []
    for a, b in combinations(active, 2):
        files_a = set(a["committed"]) | set(a["dirty"])
        files_b = set(b["committed"]) | set(b["dirty"])
        shared = sorted(files_a & files_b)
        if not shared:
            continue
        conflicts = None
        if set(a["committed"]) & set(b["committed"]):
            conflicts = merge_conflicts(root, a["tip"], b["tip"])
        uncommitted = sorted(f for f in shared if f in a["dirty"] or f in b["dirty"])
        overlaps.append({"a": a["name"], "b": b["name"], "shared": shared,
                         "conflicts": conflicts, "uncommitted": uncommitted})

    partners: dict[str, int] = {}
    for o in overlaps:
        if o["conflicts"]:
            partners[o["a"]] = partners.get(o["a"], 0) + 1
            partners[o["b"]] = partners.get(o["b"], 0) + 1

    # Merge first what is finished and least likely to disturb others: clean worktree, no conflict
    # with main, has an open PR, fewest conflicting partners, smallest change. The later branch
    # absorbs the conflicts by merging origin/main after the earlier one lands.
    candidates = [s for s in active if s["committed"] and not s["merged"]]
    order = sorted(candidates, key=lambda s: (
        bool(s["dirty"]), bool(s["base_conflicts"]), s["open_pr"] is None,
        partners.get(s["name"], 0), len(s["committed"])))

    prunable = [s for s in data["subjects"] if s["merged"] and not s["dirty"]]
    return {"active": active, "overlaps": overlaps, "order": order, "prunable": prunable}


def render(data: dict, res: dict) -> str:
    out = []
    m = data["main"]
    if m["ahead"]:
        out.append(f"!! local main has {m['ahead']} commit(s) not on {BASE} (and is {m['behind']} behind). "
                   "Move them to a branch + PR; never merge into local main.")
    elif m["behind"]:
        out.append(f"local main is {m['behind']} commit(s) behind {BASE} (fast-forward with prune --yes).")

    out.append("\nActive branches:")
    if not res["active"]:
        out.append("  (none)")
    for s in res["active"]:
        tags = []
        if s["open_pr"]:
            tags.append(f"PR #{s['open_pr']}")
        if s["unpushed"]:
            tags.append("unpushed commits")
        if s["dirty"]:
            tags.append(f"{len(s['dirty'])} uncommitted file(s)")
        if s["base_conflicts"]:
            tags.append("CONFLICTS with main: " + ", ".join(s["base_conflicts"]))
        where = f" [{os.path.relpath(s['worktree'], data['root'])}]" if s["worktree"] else ""
        out.append(f"  - {s['name']}{where}: {len(s['committed'])} file(s) committed"
                   + (f"; {'; '.join(tags)}" if tags else ""))

    out.append("\nSame files touched by more than one branch:")
    if not res["overlaps"]:
        out.append("  (none)")
    for o in res["overlaps"]:
        if o["conflicts"]:
            level = "CONFLICT on " + ", ".join(o["conflicts"])
        elif o["uncommitted"]:
            level = "being edited now (uncommitted): " + ", ".join(o["uncommitted"])
        else:
            level = "merges cleanly"
        out.append(f"  - {o['a']}  <->  {o['b']}: {', '.join(o['shared'])}  => {level}")

    if res["order"]:
        out.append("\nSuggested merge order:")
        names = [s["name"] for s in res["order"]]
        for i, s in enumerate(res["order"], 1):
            why = []
            if s["dirty"]:
                why.append("has uncommitted work, finish it first")
            if s["base_conflicts"]:
                why.append("merge origin/main into it and resolve first")
            if not s["open_pr"]:
                why.append("no open PR yet")
            out.append(f"  {i}. {s['name']}" + (f"  ({'; '.join(why)})" if why else ""))
        for o in res["overlaps"]:
            if o["conflicts"] and o["a"] in names and o["b"] in names:
                later = max(o["a"], o["b"], key=names.index)
                earlier = o["b"] if later == o["a"] else o["a"]
                out.append(f"  -> after {earlier} lands, run `git merge origin/main` in {later} "
                           f"and resolve: {', '.join(o['conflicts'])}")

    out.append("\nAlready merged, safe to delete (prune --yes):")
    if not res["prunable"]:
        out.append("  (none)")
    for s in res["prunable"]:
        parts = [p for p, ok in (("worktree", s["worktree"]), ("local", s["local"]),
                                 ("remote", s["remote"])) if ok]
        via = f"PR #{s['merged_pr']}" if s["merged_pr"] else "in main"
        out.append(f"  - {s['name']} ({via}): {', '.join(parts)}")
    return "\n".join(out).lstrip("\n")


def prune(data: dict, res: dict, yes: bool, here: str) -> int:
    root = data["root"]
    actions = []
    for s in res["prunable"]:
        if s["worktree"] and Path(here).resolve().is_relative_to(Path(s["worktree"]).resolve()):
            print(f"skip {s['name']}: this session runs inside its worktree; remove it from the repo root")
            continue
        if s["worktree"]:
            actions.append((f"remove worktree {s['worktree']}", ["worktree", "remove", s["worktree"]]))
        if s["local"]:
            # -D: squash-merged branches are not ancestors of main, so -d would refuse.
            actions.append((f"delete local branch {s['name']}", ["branch", "-D", s["name"]]))
        if s["remote"]:
            actions.append((f"delete remote branch {REMOTE}/{s['name']}",
                            ["push", REMOTE, "--delete", s["name"]]))
    m = data["main"]
    if m["behind"] and not m["ahead"] and m["root_on_main"] and not m["root_dirty"]:
        actions.append((f"fast-forward local main by {m['behind']} commit(s)",
                        ["merge", "--ff-only", BASE]))
    if not actions:
        print("nothing to prune")
        return 0
    for label, _ in actions:
        print(("" if yes else "would ") + label)
    if not yes:
        print("\nre-run with --yes to apply")
        return 0
    failed = 0
    for label, cmd in actions:
        rc, out = git(*cmd, cwd=root)
        if rc != 0:
            failed += 1
            print(f"FAILED: {label}")
    git("worktree", "prune", cwd=root)
    git("fetch", "--prune", "-q", REMOTE, cwd=root)
    return 1 if failed else 0


def hook() -> int:
    """Warn (never block) when the file about to be edited is also changed in another worktree
    or another unmerged branch. Warns once per session per file."""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return 0
    target = Path(file_path).resolve()
    probe = target.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    rc, top = git("rev-parse", "--show-toplevel", cwd=str(probe))
    if rc != 0:
        return 0
    rel = os.path.relpath(target, top)
    root = repo_root(top)
    if not root or rel.startswith(".."):
        return 0

    hits = []
    wts = worktrees(root)
    seen_branches = set()
    for w in wts:
        seen_branches.add(w.get("branch"))
        if Path(w["path"]).resolve() == Path(top).resolve():
            continue
        label = f"worktree {os.path.relpath(w['path'], root)} ({w.get('branch', 'detached')})"
        if rel in dirty_files(w["path"]):
            hits.append(f"{label}: uncommitted edits")
        elif git("diff", "--quiet", f"{BASE}...{w['head']}", "--", rel, cwd=root)[0] == 1:
            hits.append(f"{label}: committed changes")
    _, refs = git("for-each-ref", "--format=%(refname:short)", "refs/heads",
                  f"refs/remotes/{REMOTE}", cwd=root)
    for ref in refs.splitlines():
        name = ref.removeprefix(f"{REMOTE}/")
        if name in seen_branches or name in ("main", "HEAD", REMOTE) or ref == REMOTE:
            continue
        seen_branches.add(name)
        if git("diff", "--quiet", f"{BASE}...{ref}", "--", rel, cwd=root)[0] == 1:
            hits.append(f"branch {ref}: committed changes (may be squash-merged already)")
    if not hits:
        return 0

    marker = Path(root) / ".git" / "branch-observer-warned.json"
    key = f"{data.get('session_id', '')}|{top}|{rel}|{len(hits)}"
    try:
        warned = json.loads(marker.read_text()) if marker.exists() else []
    except ValueError:
        warned = []
    if key in warned:
        return 0
    try:
        marker.write_text(json.dumps((warned + [key])[-500:]))
    except OSError:
        pass

    msg = (f"[branch-observer] {rel} is also changed elsewhere: " + "; ".join(hits)
           + ". Tell the user; the branches may conflict on this file. Decide which merges "
             "first (scripts/branch_observer.py report) and keep edits to this file minimal.")
    print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": msg}}))
    return 0


def session(cwd: str) -> int:
    root = repo_root(cwd)
    if not root:
        return 0
    data = collect(root, use_gh=False)
    res = analyse(data)
    notes = []
    if data["main"]["ahead"]:
        notes.append(f"local main has {data['main']['ahead']} commit(s) not on {BASE}")
    risky = [o for o in res["overlaps"] if o["conflicts"] or o["uncommitted"]]
    if risky:
        notes.append("parallel branches touch the same files: "
                     + "; ".join(f"{o['a']} <-> {o['b']} ({', '.join(o['shared'][:3])})" for o in risky))
    if res["prunable"]:
        notes.append(f"{len(res['prunable'])} merged branch(es) can be deleted")
    if notes:
        msg = "[branch-observer] " + " | ".join(notes) + ". Details: python3 scripts/branch_observer.py report"
        print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["report", "prune", "hook", "session"])
    ap.add_argument("--fetch", action="store_true", help="git fetch --prune first")
    ap.add_argument("--no-gh", action="store_true", help="skip PR lookup (squash merges not detected)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--yes", action="store_true", help="prune: actually delete")
    args = ap.parse_args()

    if args.command == "hook":
        return hook()
    cwd = os.getcwd()
    if args.command == "session":
        try:
            data = json.load(sys.stdin)
            cwd = data.get("cwd") or cwd
        except ValueError:
            pass
        return session(cwd)

    root = repo_root(cwd)
    if not root:
        print("not a git repository", file=sys.stderr)
        return 2
    if args.fetch:
        git("fetch", "--prune", "-q", REMOTE, cwd=root)
    data = collect(root, use_gh=not args.no_gh)
    res = analyse(data)
    if args.command == "prune":
        return prune(data, res, args.yes, cwd)
    if args.json:
        print(json.dumps({"main": data["main"], **res}, indent=1, default=str))
    else:
        print(render(data, res))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # hooks must fail open
        if len(sys.argv) > 1 and sys.argv[1] in ("hook", "session"):
            sys.exit(0)
        raise

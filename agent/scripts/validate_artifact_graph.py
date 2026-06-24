#!/usr/bin/env python3
"""
artifact-graph.yaml の整合性チェック

検証項目:
  1. 全ノードIDがPJ内でユニーク
  2. 全エッジの from/to がノードに存在
  3. 循環依存がない（DAG検証）
  4. 各ノードの category が標準フォルダに準拠
  5. derived_by で参照されるスクリプトが .claude/scripts/ に存在
  6. change_categories の entry_points が全てノードに存在
  7. project_id が pj-config.yaml の project.id と一致（pj-config.yaml がある場合）

使い方:
  python validate_artifact_graph.py <PJフォルダパス>
  python validate_artifact_graph.py ./Idemitsu
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# 標準フォルダ名（README.md のフォルダ構成ルールに準拠）
VALID_CATEGORIES = {
    "0_Project",
    "1_Strategy",
    "2_Scope",
    "3_Structure",
    "4_Skeleton",
    "5_Surface",
    "6_Test",
    "7_Operations",
    "8_Modeling",
    "9_Decision_Records",
}

# 有効な依存種別
VALID_DEPENDENCY_TYPES = {"derives", "references", "constrains"}

# 有効な成果物ステータス
VALID_STATUSES = {"active", "draft", "archived"}

# 有効なフォーマット
VALID_FORMATS = {"md", "csv", "xlsx", "docx", "pdf", "yaml", "json"}

# 既知の導出スクリプト
KNOWN_DERIVE_SCRIPTS = {
    "derive_resources",
    "derive_estimate",
    "derive_wbs_schedule",
    "derive_fte",
}


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise ImportError("PyYAML が必要です。pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate(pj_root: Path, claude_root: Path = None) -> list:
    """artifact-graph.yaml を検証し、エラーリストを返す。

    Args:
        pj_root: PJフォルダのパス
        claude_root: .claude/ のルートパス（スクリプト存在チェック用）

    Returns:
        エラーメッセージのリスト（空ならOK）
    """
    graph_path = pj_root / "artifact-graph.yaml"
    if not graph_path.exists():
        return [f"artifact-graph.yaml が見つかりません: {graph_path}"]

    graph = load_yaml(graph_path)
    errors = []

    # --- 基本構造チェック ---
    if "artifacts" not in graph:
        errors.append("'artifacts' セクションがありません")
        return errors

    artifacts = graph.get("artifacts", [])
    dependencies = graph.get("dependencies", [])
    change_categories = graph.get("change_categories", {})

    # --- 1. ノードIDのユニーク性 ---
    node_ids = set()
    for art in artifacts:
        aid = art.get("id", "")
        if not aid:
            errors.append(f"空のノードIDがあります: {art}")
            continue
        if aid in node_ids:
            errors.append(f"重複ノードID: '{aid}'")
        node_ids.add(aid)

    # --- 2. エッジの from/to がノードに存在 ---
    for i, dep in enumerate(dependencies):
        from_id = dep.get("from", "")
        to_id = dep.get("to", "")
        dep_type = dep.get("type", "")

        if from_id not in node_ids:
            errors.append(
                f"依存関係 #{i+1}: from '{from_id}' がノードに存在しません"
            )
        if to_id not in node_ids:
            errors.append(
                f"依存関係 #{i+1}: to '{to_id}' がノードに存在しません"
            )
        if dep_type not in VALID_DEPENDENCY_TYPES:
            errors.append(
                f"依存関係 #{i+1}: 不正な type '{dep_type}' "
                f"(有効: {VALID_DEPENDENCY_TYPES})"
            )
        if from_id == to_id:
            errors.append(
                f"依存関係 #{i+1}: 自己参照 '{from_id}' → '{to_id}'"
            )

    # --- 3. DAG検証（循環依存チェック）---
    adj = defaultdict(list)
    for dep in dependencies:
        adj[dep.get("from", "")].append(dep.get("to", ""))

    # トポロジカルソートで循環を検出
    visited = set()
    in_stack = set()
    cycle_found = []

    def _dfs(node, path):
        if node in in_stack:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycle_found.append(" → ".join(cycle))
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        path.append(node)
        for neighbor in adj.get(node, []):
            _dfs(neighbor, path)
        path.pop()
        in_stack.remove(node)

    for node_id in node_ids:
        if node_id not in visited:
            _dfs(node_id, [])

    for cycle in cycle_found:
        errors.append(f"循環依存を検出: {cycle}")

    # --- 4. category の妥当性 ---
    for art in artifacts:
        cat = art.get("category", "")
        if cat and cat not in VALID_CATEGORIES:
            errors.append(
                f"ノード '{art.get('id')}': 不正な category '{cat}' "
                f"(有効: {sorted(VALID_CATEGORIES)})"
            )

    # --- 5. derived_by のスクリプト存在チェック ---
    for art in artifacts:
        script_name = art.get("derived_by")
        if not script_name:
            continue
        # .claude/scripts/ にスクリプトが存在するかチェック
        if claude_root:
            script_path = claude_root / "scripts" / f"{script_name}.py"
            if not script_path.exists():
                errors.append(
                    f"ノード '{art.get('id')}': derived_by "
                    f"'{script_name}' のスクリプトが見つかりません: "
                    f"{script_path}"
                )
        # 既知のスクリプト名かチェック
        if script_name not in KNOWN_DERIVE_SCRIPTS:
            errors.append(
                f"ノード '{art.get('id')}': derived_by "
                f"'{script_name}' は既知のスクリプトではありません "
                f"(既知: {sorted(KNOWN_DERIVE_SCRIPTS)})"
            )

    # --- 6. change_categories の entry_points チェック ---
    for cat_key, cat_def in change_categories.items():
        entry_points = cat_def.get("entry_points", [])
        for ep in entry_points:
            if ep not in node_ids:
                errors.append(
                    f"change_categories.{cat_key}: entry_point "
                    f"'{ep}' がノードに存在しません"
                )

    # --- 7. project_id の一致チェック ---
    graph_project_id = graph.get("project_id", "")
    config_path = pj_root / "pj-config.yaml"
    if config_path.exists():
        try:
            config = load_yaml(config_path)
            config_project_id = config.get("project", {}).get("id", "")
            if (graph_project_id and config_project_id
                    and graph_project_id != config_project_id):
                errors.append(
                    f"project_id の不一致: artifact-graph='{graph_project_id}' "
                    f"vs pj-config='{config_project_id}'"
                )
        except Exception:
            pass  # pj-config.yaml の読み込みエラーは無視

    # --- 追加チェック: 必須フィールド ---
    for art in artifacts:
        for field in ["id", "doc_id", "title", "category", "gate", "format"]:
            if not art.get(field):
                errors.append(
                    f"ノード '{art.get('id', '???')}': "
                    f"必須フィールド '{field}' が未設定"
                )

        status = art.get("status", "active")
        if status not in VALID_STATUSES:
            errors.append(
                f"ノード '{art.get('id')}': 不正な status '{status}'"
            )

        fmt = art.get("format", "")
        if fmt and fmt not in VALID_FORMATS:
            errors.append(
                f"ノード '{art.get('id')}': 不正な format '{fmt}'"
            )

    return errors


def main():
    if len(sys.argv) < 2:
        print("使い方: python validate_artifact_graph.py <PJフォルダパス>")
        print("例: python validate_artifact_graph.py ./Idemitsu")
        sys.exit(1)

    pj_root = Path(sys.argv[1]).resolve()

    # .claude/ のルートを探す（derive スクリプトが存在する方を優先）
    claude_root = None
    candidates = [
        pj_root.parent / ".claude",           # 配布先パターン
        pj_root.parent.parent / ".claude",    # SSoTパターン
    ]
    # derive スクリプトが存在する候補を優先
    for candidate in candidates:
        scripts_dir = candidate / "scripts"
        if scripts_dir.is_dir() and list(scripts_dir.glob("derive_*.py")):
            claude_root = candidate
            break
    if claude_root is None:
        for candidate in candidates:
            if candidate.exists():
                claude_root = candidate
                break

    errors = validate(pj_root, claude_root)

    if errors:
        print(f"✗ 検証失敗: {len(errors)} 件のエラー\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)
    else:
        print("✓ artifact-graph.yaml の整合性チェック: OK")
        sys.exit(0)


if __name__ == "__main__":
    main()

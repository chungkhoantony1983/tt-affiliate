#!/usr/bin/env python3
"""PostToolUse hook: 書き込み後のファイル全体構造検証。

hook_fuzzy ルールの検証を行う。ブロックはできない（exit 0 固定）が、
stderr メッセージで Claude に即座の修正を促す。
"""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    try:
        content = open(file_path).read()
    except (FileNotFoundError, PermissionError):
        sys.exit(0)

    violations: list[str] = []

    # === IMP-047: learned-rules.yaml の scope チェック（hook_fuzzy） ===
    if file_path.endswith("learned-rules.yaml"):
        try:
            import yaml

            rules_data = yaml.safe_load(content) or {}
            domains = rules_data.get("domains", {})
            if isinstance(domains, dict):
                for domain_name, domain_data in domains.items():
                    if not isinstance(domain_data, dict):
                        continue
                    for key in ("constraints", "processes"):
                        for rule in domain_data.get(key, []):
                            if not isinstance(rule, dict):
                                continue
                            rule_id = rule.get("id", "?")
                            scope = rule.get("scope")
                            if scope is None:
                                violations.append(
                                    f"IMP-047: ドメインルール '{rule_id}' (domains.{domain_name}.{key})"
                                    f" に scope が未設定です。scope.repos または scope.project を追加してください"
                                )
        except Exception:
            pass  # YAML パースエラーはフェイルオープン

    # === prose_gate 警告: enforcement 実装漏れ検出 ===
    if file_path.endswith(".yaml") and "/rules/" in file_path:
        try:
            import yaml

            rules_data = yaml.safe_load(content) or {}
            rules_list = rules_data.get("rules", [])
            if isinstance(rules_list, list):
                prose_gate_rules = []
                no_enforcement_rules = []
                for rule in rules_list:
                    if not isinstance(rule, dict):
                        continue
                    rule_id = rule.get("id", "?")
                    etype = rule.get("enforcement_type")
                    if etype == "prose_gate":
                        prose_gate_rules.append(rule_id)
                    elif etype is None:
                        no_enforcement_rules.append(rule_id)
                if prose_gate_rules:
                    violations.append(
                        f"enforcement 警告: {', '.join(prose_gate_rules)} は prose_gate です。"
                        " hook_strict/hook_fuzzy/phase_py に昇格できないか確認してください。"
                        " prose_gate は自動化不可能な場合の最終手段です"
                    )
                if no_enforcement_rules:
                    violations.append(
                        f"enforcement 未設定: {', '.join(no_enforcement_rules)} に"
                        " enforcement_type が未設定です。"
                        " デシジョンツリー（hook_strict→hook_fuzzy→phase_py→prose_gate）で判定してください"
                    )

            # === 構造変更ファースト警告: ルール追加時に構造変更を検討したか ===
            all_rules = rules_list[:]
            # ドメイン別ルールも収集
            domains_data = rules_data.get("domains", {})
            if isinstance(domains_data, dict):
                for d_data in domains_data.values():
                    if isinstance(d_data, dict):
                        for key in ("constraints", "processes"):
                            all_rules.extend(d_data.get(key, []))

            bridge_count = sum(
                1 for r in all_rules
                if isinstance(r, dict) and r.get("type") == "bridge"
            )
            total_count = len([r for r in all_rules if isinstance(r, dict)])
            if total_count > 0 and bridge_count > 10:
                violations.append(
                    f"構造変更ファースト警告: bridge ルールが {bridge_count} 件あります。"
                    " analyze.py の cluster_rules() でクラスタ化し、"
                    " 構造変更で削減できないか確認してください。"
                    " ルール台帳の肥大化は /ai-learn の本務に反します"
                )
        except Exception:
            pass

    # === HTML ファイルの構造チェック ===
    if file_path.endswith(".html"):
        # SL-032: 4層構造（header/title-block/body/footer）
        if "<header" not in content:
            violations.append("SL-032: <header> タグが見つかりません。4層構造を確認してください。")
        if "<footer" not in content:
            violations.append("SL-032: <footer> タグが見つかりません。4層構造を確認してください。")

        # SL-034: footer は body 直下
        if "<footer" in content and "</body>" in content:
            footer_pos = content.rfind("<footer")
            body_close_pos = content.rfind("</body>")
            # footer と </body> の間に他の closing div がないか簡易チェック
            between = content[footer_pos:body_close_pos]
            if between.count("</div>") > 2:
                violations.append(
                    "SL-034: <footer> が深いネストにあります。body 直下に配置してください。"
                )

    if violations:
        print("⚠ PostToolUse 検証で違反を検出:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print(
            "上記の違反を Edit ツールで即座に修正してください。",
            file=sys.stderr,
        )

    sys.exit(0)  # PostToolUse は常に exit 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)

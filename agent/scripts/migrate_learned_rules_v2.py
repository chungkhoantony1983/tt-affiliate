#!/usr/bin/env python3
"""
learned-rules.yaml v1.3 → v2.0 マイグレーションスクリプト

変換内容:
1. 機械的変換: nested (global/domains) → flat rules[] with binding
2. 手動再分類: GP-012→skill:ai-learn, DD-P01→skill:fix
3. Domain×Phase 紐付け（確定済み分類表に基づく）
4. orchestration ルール抽出（teams.yaml cli_config へ移動分）
5. style_config → style_configs トップレベル移動
"""

import yaml
import sys
import os
from collections import OrderedDict
from io import StringIO

# === Phase 紐付けマッピング（確定済み） ===
PHASE_BINDINGS = {
    # (code-review, scan)
    'CR-008': 'scan',
    'CR-011': 'scan',
    'CR-014': 'scan',
    'CR-P01': 'scan',
    'CR-P03': 'scan',
    'CR-P05-mailer-spec-fix': 'scan',  # CR-P05
    'CR-P07': 'scan',
    # (code-review, discuss)
    'CR-004': 'discuss',
    'CR-P06': 'discuss',
    # (slides, plan)
    'SL-039': 'plan',
    'SL-053': 'plan',
    'SL-P04': 'plan',
    # project-poc plan-phase rules
    'SL-021': 'plan',
    'SL-022': 'plan',
    'SL-023': 'plan',
    'SL-024': 'plan',
    'SL-036': 'plan',
    'SL-043': 'plan',
    'SL-044': 'plan',
    'SL-045': 'plan',
    'SL-046': 'resolve',  # project corrections.md 読み込み → resolve フェーズ
    'SL-047': 'plan',
    'SL-048': 'plan',
    'SL-049': 'plan',
    'SL-050': 'plan',
    # (slides, generate)
    'SL-012': 'generate',
    'SL-P05': 'generate',
    'SL-P08': 'generate',
    # (slides, qa)
    'SL-P02': 'qa',
    'SL-P09': 'qa',
    'SL-052': 'qa',
    # (slides, export)
    'SL-042': 'export',
    'SL-P10': 'export',
    # (slides, resolve)
    'SL-P11': 'resolve',
}

# === Skill-level 再分類 ===
SKILL_RECLASSIFY = {
    'GP-012': 'ai-learn',
    'DD-P01': 'fix',
}

# === Orchestration ルール（teams.yaml cli_config へ移動 → 削除対象） ===
ORCHESTRATION_RULES = {'CR-006', 'CR-010', 'CR-P02', 'CR-P04'}

# === YAML multi-line string representer ===
class LiteralStr(str):
    pass

def literal_str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    if len(data) > 100:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(LiteralStr, literal_str_representer)

def build_binding(rule_id, source_level, source_domain=None):
    """Build the binding dict for a rule."""
    # Skill-level reclassification
    if rule_id in SKILL_RECLASSIFY:
        return {'level': 'skill', 'target': SKILL_RECLASSIFY[rule_id]}

    # Company-level (from global)
    if source_level == 'company':
        binding = {'level': 'company'}
        # Check for phase (none for company rules currently)
        return binding

    # Domain-level
    if source_level == 'domain':
        binding = {'level': 'domain', 'target': source_domain}
        # Check for phase binding
        if rule_id in PHASE_BINDINGS:
            binding['phase'] = PHASE_BINDINGS[rule_id]
        return binding

    return {'level': source_level}


def transform_rule(rule_dict, source_level, source_domain=None):
    """Transform a single rule from v1.3 to v2.0 format."""
    rule_id = rule_dict['id']

    # Skip orchestration rules (they move to teams.yaml)
    if rule_id in ORCHESTRATION_RULES:
        return None

    # Build new rule
    new_rule = OrderedDict()
    new_rule['id'] = rule_id
    new_rule['binding'] = build_binding(rule_id, source_level, source_domain)

    # Copy rule text
    rule_text = rule_dict.get('rule', '')
    new_rule['rule'] = rule_text

    # Copy type
    if 'type' in rule_dict:
        new_rule['type'] = rule_dict['type']

    # Copy enforcement_type (only if non-default)
    if 'enforcement_type' in rule_dict:
        new_rule['enforcement_type'] = rule_dict['enforcement_type']

    # Copy scope
    if 'scope' in rule_dict:
        new_rule['scope'] = rule_dict['scope']

    # Copy linked_improvement
    if 'linked_improvement' in rule_dict:
        new_rule['linked_improvement'] = rule_dict['linked_improvement']

    # Copy origin
    if 'origin' in rule_dict:
        new_rule['origin'] = rule_dict['origin']

    # Copy promoted_at
    if 'promoted_at' in rule_dict:
        new_rule['promoted_at'] = rule_dict['promoted_at']

    return dict(new_rule)


def migrate(input_path, output_path=None):
    """Main migration function."""
    with open(input_path, 'r') as f:
        data = yaml.safe_load(f)

    if data.get('schema_version') != '1.3':
        print(f"WARNING: Expected schema_version 1.3, got {data.get('schema_version')}")

    rules = []
    style_configs = {}
    orchestration_extracted = []

    # === 1. Global constraints → company binding ===
    for rule in data.get('global', {}).get('constraints', []):
        transformed = transform_rule(rule, 'company')
        if transformed:
            rules.append(transformed)

    # === 2. Global processes → company binding ===
    for rule in data.get('global', {}).get('processes', []):
        transformed = transform_rule(rule, 'company')
        if transformed:
            rules.append(transformed)

    # === 3. Domain constraints + processes ===
    for domain_name, domain_data in data.get('domains', {}).items():
        if not domain_data:
            continue

        # Constraints
        for rule in domain_data.get('constraints', []):
            transformed = transform_rule(rule, 'domain', domain_name)
            if transformed:
                rules.append(transformed)
            elif rule['id'] in ORCHESTRATION_RULES:
                orchestration_extracted.append(rule)

        # Processes
        for rule in domain_data.get('processes', []):
            transformed = transform_rule(rule, 'domain', domain_name)
            if transformed:
                rules.append(transformed)
            elif rule['id'] in ORCHESTRATION_RULES:
                orchestration_extracted.append(rule)

        # Style config
        if 'style_config' in domain_data:
            style_configs[domain_name] = domain_data['style_config']

    # === Build output ===
    output = OrderedDict()
    output['schema_version'] = '2.0'
    output['rules'] = rules
    if style_configs:
        output['style_configs'] = style_configs

    # === Write output ===
    out_path = output_path or input_path.replace('.yaml', '.v2.yaml')

    with open(out_path, 'w') as f:
        # Write header comment
        f.write('schema_version: "2.0"\n\n')
        f.write('# learned-rules.yaml v2.0 — フラットルールリスト + binding モデル\n')
        f.write('#\n')
        f.write('# binding:\n')
        f.write('#   level: company                           → 全ドメイン・全スキルに適用\n')
        f.write('#   level: domain, target: code-review       → 指定ドメインの全フェーズに適用\n')
        f.write('#   level: domain, target: code-review, phase: scan → 指定ドメインの指定フェーズのみ\n')
        f.write('#   level: skill, target: ai-learn           → 指定スキル実行時のみ適用\n')
        f.write('#   level: persona, target: bank-cto         → 指定ペルソナのみ（将来拡張）\n')
        f.write('#\n')
        f.write('# ルール分類:\n')
        f.write('#   type: permanent  — 構造化できない半永続ルール\n')
        f.write('#   type: bridge     — 構造変更までの繋ぎ（linked_improvement で紐付け）\n')
        f.write('#\n')
        f.write('# enforcement_type（4層エンフォースメント）:\n')
        f.write('#   hook_strict  — L1: PreToolUse hook で自動ブロック\n')
        f.write('#   hook_fuzzy   — L2: PostToolUse hook で警告\n')
        f.write('#   structural   — L3: コード構造で強制（Phase Runner 等）\n')
        f.write('#   prose_gate   — L4: SKILL.md フェーズ移行時チェック（デフォルト）\n')
        f.write('#\n')
        f.write('# scope（ルールスコープの構造的強制）:\n')
        f.write('#   scope なし       → 全リポに配信\n')
        f.write('#   scope.repos: [ea] → 指定リポにのみ配信\n')
        f.write('#   scope.project: xxx → 該当PJ作業時のみ参照\n')
        f.write('#\n')
        f.write('# 削除済みルール（歴史的記録）:\n')
        f.write('# GP-006: IMP-018 完了 (2026-02-26) → code_review.py _gc_between_rounds()\n')
        f.write('# GP-007: IMP-022 完了 (2026-02-26) → ~/.litellm/api-proxy.py\n')
        f.write('# RV-001~005: IMP-001 完了 (2026-02-24) → /ai-review SKILL.md 収束判定\n')
        f.write('# SL-P01: IMP-004 完了 (2026-02-26) → domain_content_validator.py\n')
        f.write('# SL-P03: IMP-004 完了 (2026-02-26) → domain_content_validator.py\n')
        f.write('# SL-P06: IMP-004 完了 (2026-02-26) → presentation.py\n')
        f.write('# SL-P07: IMP-007 完了 (2026-02-26) → domain_content_validator.py\n')
        f.write('# CR-005: IMP-023 完了 (2026-02-26) → code_review.py parse_rebuttals()\n')
        f.write('# CR-008(old): IMP-051 完了 (2026-03-03) → ReviewScope バリデーション\n')
        f.write('# CR-009: IMP-053 完了 (2026-03-03) → SKILL.md Step 3 Phase 1\n')
        f.write('# CR-016: IMP-059 完了 (2026-03-04) → re_review() プロンプト注入\n')
        f.write('#\n')
        f.write('# orchestration ルール（teams.yaml cli_config に移動済み）:\n')
        f.write('# CR-006: .md のみ PR → platform スキップ → CC 単独 7 ペルソナ\n')
        f.write('# CR-010: Ruby → --extra-exts .rb,.gemspec\n')
        f.write('# CR-P02: 変更ファイル+テストファイルを target_path に含める\n')
        f.write('# CR-P04: 乖離ブランチは diff スコーピング\n')
        f.write('\n')

        # Write rules
        f.write('rules:\n')

        current_binding = None
        for rule in rules:
            binding = rule['binding']
            binding_key = (binding.get('level'), binding.get('target'), binding.get('phase'))

            # Section comment
            if binding_key != current_binding:
                current_binding = binding_key
                level = binding['level']
                if level == 'company':
                    f.write('\n  # === Company（全ドメイン共通） ===\n')
                elif level == 'skill':
                    target = binding['target']
                    f.write(f'\n  # === Skill: {target} ===\n')
                elif level == 'domain':
                    target = binding['target']
                    phase = binding.get('phase')
                    if phase:
                        f.write(f'\n  # === Domain×Phase: ({target}, {phase}) ===\n')
                    else:
                        f.write(f'\n  # === Domain: {target} ===\n')

            # Write the rule
            f.write(f'  - id: {rule["id"]}\n')

            # Binding
            binding_parts = [f'level: {binding["level"]}']
            if 'target' in binding:
                binding_parts.append(f'target: {binding["target"]}')
            if 'phase' in binding:
                binding_parts.append(f'phase: {binding["phase"]}')
            binding_str = ', '.join(binding_parts)
            f.write(f'    binding: {{{binding_str}}}\n')

            # Rule text
            rule_text = rule.get('rule', '')
            if '\n' in rule_text or len(rule_text) > 100:
                f.write('    rule: >\n')
                for line in rule_text.strip().split('\n'):
                    f.write(f'      {line.strip()}\n')
            else:
                f.write(f'    rule: {rule_text}\n')

            # Type
            if 'type' in rule:
                f.write(f'    type: {rule["type"]}\n')

            # Enforcement type
            if 'enforcement_type' in rule:
                f.write(f'    enforcement_type: {rule["enforcement_type"]}\n')

            # Scope
            if 'scope' in rule:
                scope = rule['scope']
                if isinstance(scope, dict):
                    if 'repos' in scope:
                        repos_str = ', '.join(scope['repos'])
                        f.write(f'    scope:\n      repos: [{repos_str}]\n')
                    elif 'project' in scope:
                        f.write(f'    scope:\n      project: {scope["project"]}\n')
                else:
                    f.write(f'    scope: {scope}\n')

            # Linked improvement
            if 'linked_improvement' in rule:
                f.write(f'    linked_improvement: {rule["linked_improvement"]}\n')

            # Origin
            if 'origin' in rule:
                origin = rule['origin']
                if '\n' in str(origin) or len(str(origin)) > 100:
                    f.write('    origin: >\n')
                    for line in str(origin).strip().split('\n'):
                        f.write(f'      {line.strip()}\n')
                else:
                    f.write(f'    origin: "{origin}"\n')

            # Promoted at
            if 'promoted_at' in rule:
                f.write(f'    promoted_at: "{rule["promoted_at"]}"\n')

        # Write style_configs
        if style_configs:
            f.write('\n# === スタイル設定（ドメイン別） ===\n')
            f.write('style_configs:\n')

            # Use yaml.dump for style_configs (simpler structure)
            for config_name, config_data in style_configs.items():
                f.write(f'  {config_name}:\n')
                if isinstance(config_data, dict) and 'inherit' in config_data:
                    f.write(f'    inherit: {config_data["inherit"]}\n')
                else:
                    config_yaml = yaml.dump(config_data, default_flow_style=False, allow_unicode=True)
                    for line in config_yaml.strip().split('\n'):
                        f.write(f'    {line}\n')

    # === Report ===
    print(f'Migration complete: {input_path} → {out_path}')
    print(f'  Total rules: {len(rules)}')

    # Count by binding level
    counts = {}
    for rule in rules:
        b = rule['binding']
        key = b['level']
        if b.get('target'):
            key += f':{b["target"]}'
        if b.get('phase'):
            key += f'.{b["phase"]}'
        counts[key] = counts.get(key, 0) + 1

    print('  By binding:')
    for key, count in sorted(counts.items()):
        print(f'    {key}: {count}')

    print(f'  Style configs: {list(style_configs.keys())}')
    print(f'  Orchestration rules extracted: {[r["id"] for r in orchestration_extracted]}')

    return rules, style_configs, orchestration_extracted


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base, 'references', 'learned-rules.yaml')
    output_path = os.path.join(base, 'references', 'learned-rules.v2.yaml')

    if len(sys.argv) > 1:
        output_path = sys.argv[1]

    migrate(input_path, output_path)

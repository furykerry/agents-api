#!/usr/bin/env python3
"""Patch generated Java SDK models with correct Kubernetes types.

Reads replacement rules from hack/type_mapping.yaml and applies them to
generated Java model files. Prints a preview of all changes before applying.

Usage:
    python3 hack/patch_java_types.py <models_dir> <mapping_yaml>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def load_java_rules(mapping_path: Path) -> list[dict]:
    """Load Java patching rules from type_mapping.yaml."""
    with mapping_path.open() as fh:
        config = yaml.safe_load(fh)

    rules: list[dict] = []
    for field in config.get("fields", []):
        java = field.get("java", {})
        if java.get("skip"):
            continue
        rules.append({
            "field_name": field["name"],
            "old_type": java["old_type"],
            "new_type": java["new_type"],
        })

    # Sort: longer field names first so "volumeClaimTemplates" is processed
    # before "template" (avoids the substring match problem).
    rules.sort(key=lambda r: len(r["field_name"]), reverse=True)
    return rules


def _build_field_patterns(field_name: str) -> list[re.Pattern]:
    """Build regex patterns that precisely match a Java field by name.

    Matches:
      - field declaration: `<type> fieldName;`
      - getter: `getFieldName()`
      - setter: `setFieldName(`
    This avoids substring conflicts (e.g. "template" matching "volumeClaimTemplates").
    """
    lower = field_name[0].lower() + field_name[1:]
    upper = field_name[0].upper() + field_name[1:]
    return [
        re.compile(rf'\b{re.escape(lower)}\b'),       # field declaration
        re.compile(rf'\bget{re.escape(upper)}\b'),     # getter
        re.compile(rf'\bset{re.escape(upper)}\b'),     # setter
    ]


def _line_matches_field(line: str, patterns: list[re.Pattern]) -> bool:
    """Check if a line matches any of the field patterns."""
    return any(p.search(line) for p in patterns)


def collect_java_changes(filepath: Path, rules: list[dict]) -> list[dict]:
    """Scan a Java file and return planned changes without modifying it."""
    lines = filepath.read_text().split("\n")
    changes: list[dict] = []

    for rule in rules:
        patterns = _build_field_patterns(rule["field_name"])
        old_type = rule["old_type"]

        for line_idx, line in enumerate(lines):
            if old_type not in line:
                continue
            if not _line_matches_field(line, patterns):
                continue
            new_line = line.replace(old_type, rule["new_type"])
            if new_line != line:
                changes.append({
                    "file": filepath,
                    "line_no": line_idx + 1,
                    "field": rule["field_name"],
                    "old": line.strip(),
                    "new": new_line.strip(),
                })
    return changes


def apply_java_patch(filepath: Path, rules: list[dict]) -> bool:
    """Apply patches to a single Java file. Returns True if modified."""
    content = filepath.read_text()
    original = content

    for rule in rules:
        patterns = _build_field_patterns(rule["field_name"])
        old_type = rule["old_type"]
        new_type = rule["new_type"]

        new_lines: list[str] = []
        for line in content.split("\n"):
            if old_type in line and _line_matches_field(line, patterns):
                line = line.replace(old_type, new_type)
            new_lines.append(line)
        content = "\n".join(new_lines)

    if content != original:
        filepath.write_text(content)
        return True
    return False


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <models_dir> <mapping_yaml>", file=sys.stderr)
        sys.exit(1)

    models_dir = Path(sys.argv[1])
    mapping_path = Path(sys.argv[2])

    if not models_dir.is_dir():
        print(f"ERROR: Directory not found: {models_dir}", file=sys.stderr)
        sys.exit(1)
    if not mapping_path.is_file():
        print(f"ERROR: Mapping file not found: {mapping_path}", file=sys.stderr)
        sys.exit(1)

    rules = load_java_rules(mapping_path)

    # Phase 1: Collect and print all planned changes
    all_changes: list[dict] = []
    for java_file in sorted(models_dir.glob("*.java")):
        all_changes.extend(collect_java_changes(java_file, rules))

    if not all_changes:
        print("  No Java type changes needed.")
        return

    print("  Planned Java type changes:")
    for change in all_changes:
        print(f"    {change['file'].name}:{change['line_no']}  "
              f"{change['field']}: {change['old']}")
        print(f"      → {change['new']}")
    print()

    # Phase 2: Apply patches
    patched_count = 0
    for java_file in sorted(models_dir.glob("*.java")):
        if apply_java_patch(java_file, rules):
            patched_count += 1

    # Phase 3: Verify no old_type remains
    remaining_files: list[str] = []
    old_types = {r["old_type"] for r in rules}
    for java_file in sorted(models_dir.glob("*.java")):
        content = java_file.read_text()
        if any(ot in content for ot in old_types):
            remaining_files.append(java_file.name)

    if remaining_files:
        print(f"  WARN: {len(remaining_files)} file(s) still contain placeholder types:")
        for fname in remaining_files:
            print(f"    {fname}")

    print(f"  Patched {patched_count} Java file(s)")


if __name__ == "__main__":
    main()

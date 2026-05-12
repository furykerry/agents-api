#!/usr/bin/env python3
"""Patch generated Python SDK models with correct Kubernetes types.

Reads replacement rules from hack/type_mapping.yaml and applies them to
generated Pydantic model files. Prints a preview of all changes before
applying them.

Usage:
    python3 hack/patch_python_types.py <models_dir> <mapping_yaml>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

CONFIGDICT_MARKER = "model_config = ConfigDict(arbitrary_types_allowed=True)"


# ── Load rules from YAML ─────────────────────────────────────────────────────

def load_python_rules(mapping_path: Path) -> list[dict]:
    """Load Python patching rules from type_mapping.yaml."""
    with mapping_path.open() as fh:
        config = yaml.safe_load(fh)

    rules: list[dict] = []
    for field in config.get("fields", []):
        py = field.get("python", {})
        if py.get("skip"):
            continue

        field_name = field["name"]
        old_pattern = py["old_pattern"]
        new_type = py["new_type"]
        k8s_import = py["import"]

        # Build regex: match the field declaration line
        if old_pattern == "Any":
            regex = rf"^(\s+{field_name}:\s+)Any(\s*\|.*)"
        elif old_pattern.startswith("dict["):
            escaped = re.escape(old_pattern).replace(r"\ ", r"\s*")
            regex = rf"^(\s+{field_name}:\s+){escaped}(\s*\|.*)"
        else:
            regex = rf"^(\s+{field_name}:\s+){re.escape(old_pattern)}(\s*\|.*)"

        replacement = rf"\g<1>{new_type}\g<2>"
        rules.append({
            "field_name": field_name,
            "regex": regex,
            "replacement": replacement,
            "old_pattern": old_pattern,
            "new_type": new_type,
            "k8s_import": k8s_import,
        })
    return rules


# ── Diff collection ──────────────────────────────────────────────────────────

def collect_changes(filepath: Path, rules: list[dict]) -> list[dict]:
    """Scan a file and return a list of planned changes without modifying it."""
    lines = filepath.read_text().split("\n")
    changes: list[dict] = []

    for line_idx, line in enumerate(lines):
        for rule in rules:
            new_line = re.sub(rule["regex"], rule["replacement"], line)
            if new_line != line:
                changes.append({
                    "file": filepath,
                    "line_no": line_idx + 1,
                    "field": rule["field_name"],
                    "old": line.strip(),
                    "new": new_line.strip(),
                    "k8s_import": rule["k8s_import"],
                })
    return changes


# ── Apply patch ──────────────────────────────────────────────────────────────

def apply_patch(filepath: Path, rules: list[dict]) -> bool:
    """Apply all patches to a single file. Returns True if modified."""
    content = filepath.read_text()
    original = content
    lines = content.split("\n")

    # Step 1: Replace field types
    used_k8s_types: set[str] = set()
    for i, line in enumerate(lines):
        for rule in rules:
            new_line = re.sub(rule["regex"], rule["replacement"], line)
            if new_line != line:
                lines[i] = new_line
                used_k8s_types.add(rule["k8s_import"])
                line = new_line

    if not used_k8s_types:
        return False

    content = "\n".join(lines)

    # Step 2: Add kubernetes imports
    sorted_types = sorted(used_k8s_types)
    import_line = f"from kubernetes.client.models import {', '.join(sorted_types)}"
    if import_line not in content:
        content = re.sub(
            r"(from pydantic import )",
            import_line + "\n" + r"\g<1>",
            content,
            count=1,
        )

    # Step 3: Add ConfigDict to pydantic import
    if "ConfigDict" not in content:
        content = re.sub(
            r"from pydantic import (.*)",
            lambda m: f"from pydantic import ConfigDict, {m.group(1)}",
            content,
            count=1,
        )

    # Step 4: Add model_config to classes using K8s types
    content = _inject_configdict(content, used_k8s_types)

    # Step 5: Clean up unused Any import
    content = _cleanup_any_import(content)

    if content != original:
        filepath.write_text(content)
        return True
    return False


def _inject_configdict(content: str, k8s_types: set[str]) -> str:
    """Insert model_config = ConfigDict(...) into classes that use K8s types."""
    lines = content.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        result.append(line)

        class_match = re.match(r"^class (\w+)\(BaseModel\):", line)
        if class_match:
            has_k8s_type = False
            has_configdict = False
            lookahead = i + 1
            while lookahead < len(lines):
                next_line = lines[lookahead]
                if re.match(r"^class \w+", next_line) or (
                    next_line.strip()
                    and not next_line.startswith(" ")
                    and not next_line.startswith("#")
                    and not next_line.startswith('"""')
                    and not next_line.startswith("    ")
                ):
                    break
                if CONFIGDICT_MARKER in next_line:
                    has_configdict = True
                for k8s_type in k8s_types:
                    if re.search(rf"\b{k8s_type}\b", next_line):
                        has_k8s_type = True
                lookahead += 1

            if has_k8s_type and not has_configdict:
                j = i + 1
                if j < len(lines) and lines[j].strip().startswith('"""'):
                    if lines[j].strip().endswith('"""') and lines[j].strip() != '"""':
                        j += 1
                    else:
                        j += 1
                        while j < len(lines) and '"""' not in lines[j]:
                            j += 1
                        j += 1

                insert_pos = j
                for k in range(i + 1, min(insert_pos, len(lines))):
                    result.append(lines[k])
                result.append(f"    {CONFIGDICT_MARKER}")
                result.append("")
                i = insert_pos
                continue
        i += 1
    return "\n".join(result)


def _cleanup_any_import(content: str) -> str:
    """Remove 'Any' from typing import if no longer used."""
    non_import_lines = [
        line for line in content.split("\n") if "from typing import" not in line
    ]
    if any(re.search(r"\bAny\b", line) for line in non_import_lines):
        return content

    content = re.sub(r"from typing import Any\n", "", content)
    content = re.sub(r"from typing import Any, ", "from typing import ", content)
    content = re.sub(r"from typing import (.+), Any", r"from typing import \1", content)
    return content


# ── Main ─────────────────────────────────────────────────────────────────────

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

    rules = load_python_rules(mapping_path)

    # Phase 1: Collect and print all planned changes
    all_changes: list[dict] = []
    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        all_changes.extend(collect_changes(py_file, rules))

    if not all_changes:
        print("  No Python type changes needed.")
        return

    print("  Planned Python type changes:")
    for change in all_changes:
        print(f"    {change['file'].name}:{change['line_no']}  "
              f"{change['field']}: {change['old']}  →  {change['new']}")
    print()

    # Phase 2: Apply patches
    patched_count = 0
    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if apply_patch(py_file, rules):
            patched_count += 1

    print(f"  Patched {patched_count} Python file(s)")


if __name__ == "__main__":
    main()

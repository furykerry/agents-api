#!/usr/bin/env bash
# Patch generated SDK type placeholders with correct Kubernetes types.
#
# Reads replacement rules from clients/codegen/type_mapping.yaml and applies them to
# generated Java and Python SDK files. Prints a preview of all changes
# before applying.
#
# Usage:
#   ./hack/patch_sdk_types.sh          # patch both Java and Python
#   ./hack/patch_sdk_types.sh --java   # patch Java only
#   ./hack/patch_sdk_types.sh --python # patch Python only
#   make patch-sdk-types

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────────
CODEGEN_DIR="${PROJECT_ROOT}/clients/codegen"
MAPPING_FILE="${CODEGEN_DIR}/type_mapping.yaml"
JAVA_MODELS_DIR="${PROJECT_ROOT}/clients/java/src/main/java/io/openkruise/agents/client/v2/models"
PYTHON_MODELS_DIR="${PROJECT_ROOT}/clients/python/openkruise/agents/models"

# ── Parse arguments ───────────────────────────────────────────────────────────
PATCH_JAVA=true
PATCH_PYTHON=true
for arg in "$@"; do
    case "${arg}" in
        --java)   PATCH_JAVA=true;  PATCH_PYTHON=false ;;
        --python) PATCH_JAVA=false; PATCH_PYTHON=true  ;;
    esac
done

if [[ ! -f "${MAPPING_FILE}" ]]; then
    echo "ERROR: Type mapping file not found: ${MAPPING_FILE}"
    exit 1
fi

# ── Java Type Patching ────────────────────────────────────────────────────────
patch_java() {
    if [[ ! -d "${JAVA_MODELS_DIR}" ]]; then
        echo "WARN: Java models directory not found: ${JAVA_MODELS_DIR}"
        return 0
    fi

    echo "==> Patching Java SDK types..."
    python3 "${CODEGEN_DIR}/patch_java_types.py" "${JAVA_MODELS_DIR}" "${MAPPING_FILE}"
}

# ── Python Type Patching ──────────────────────────────────────────────────────
patch_python() {
    if [[ ! -d "${PYTHON_MODELS_DIR}" ]]; then
        echo "WARN: Python models directory not found: ${PYTHON_MODELS_DIR}"
        return 0
    fi

    echo "==> Patching Python SDK types..."
    python3 "${CODEGEN_DIR}/patch_python_types.py" "${PYTHON_MODELS_DIR}" "${MAPPING_FILE}"

    echo "==> Formatting Python SDK code..."
    if command -v ruff &>/dev/null; then
        ruff check --fix --select I "${PYTHON_MODELS_DIR}" 2>/dev/null || true
        ruff format "${PYTHON_MODELS_DIR}" 2>/dev/null || true
    elif command -v black &>/dev/null; then
        isort "${PYTHON_MODELS_DIR}" 2>/dev/null || true
        black "${PYTHON_MODELS_DIR}" 2>/dev/null || true
    else
        echo "  WARN: No Python formatter found (ruff/black), skipping format"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo "==> SDK Type Patching (rules: $(basename "${MAPPING_FILE}"))"

if [[ "${PATCH_JAVA}" == "true" ]]; then
    patch_java
fi

if [[ "${PATCH_PYTHON}" == "true" ]]; then
    patch_python
fi

echo ""
echo "========================================="
echo " SDK type patching complete!"
echo "========================================="

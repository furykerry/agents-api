#!/usr/bin/env bash
# Copyright 2025 The OpenKruise Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
SDK="all"
TIMEOUT="300"

usage() {
  echo "Usage: $0 [--sdk go|java|python|all] [--timeout seconds]"
  echo ""
  echo "Options:"
  echo "  --sdk       SDK to test (go, java, python, all). Default: all"
  echo "  --timeout   Timeout in seconds. Default: 300"
  exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --sdk)
      SDK="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --help|-h)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

echo "=== Running E2E tests for SDK: ${SDK} ==="
echo "Timeout: ${TIMEOUT}s"

# Verify cluster is accessible
kubectl cluster-info || { echo "ERROR: Cannot access Kubernetes cluster"; exit 1; }

# Verify CRDs are installed
echo "Checking CRDs..."
kubectl get crd sandboxes.agents.kruise.io > /dev/null 2>&1 || { echo "ERROR: Sandbox CRD not installed"; exit 1; }
kubectl get crd sandboxsets.agents.kruise.io > /dev/null 2>&1 || { echo "ERROR: SandboxSet CRD not installed"; exit 1; }
kubectl get crd sandboxclaims.agents.kruise.io > /dev/null 2>&1 || { echo "ERROR: SandboxClaim CRD not installed"; exit 1; }
echo "CRDs verified."

run_go_test() {
  echo ""
  echo "=== Running Go SDK E2E Test ==="
  cd "${PROJECT_ROOT}"
  go test -v -timeout "${TIMEOUT}s" ./test/e2e/... -ginkgo.v
  echo "Go SDK E2E Test PASSED"
}

run_java_test() {
  echo ""
  echo "=== Running Java v2 SDK E2E Test ==="
  cd "${PROJECT_ROOT}/clients/java"
  mvn test -Dtest="io.openkruise.agents.client.e2e.v2.*Test" -q
  echo "Java v2 SDK E2E Test PASSED"
}

run_python_test() {
  echo ""
  echo "=== Running Python SDK E2E Test ==="
  cd "${PROJECT_ROOT}/clients/python/openkruise"
  pip install -e ".[test]" -q 2>/dev/null || pip3 install -e ".[test]" -q 2>/dev/null
  python -m pytest test/ -v -s
  echo "Python SDK E2E Test PASSED"
}

case ${SDK} in
  go)
    run_go_test
    ;;
  java)
    run_java_test
    ;;
  python)
    run_python_test
    ;;
  all)
    run_go_test
    run_java_test
    run_python_test
    ;;
  *)
    echo "ERROR: Unknown SDK: ${SDK}"
    usage
    ;;
esac

echo ""
echo "=== All E2E tests completed successfully ==="

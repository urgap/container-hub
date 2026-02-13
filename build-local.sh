#!/usr/bin/env bash
#
# Local Docker build and test script
#
# Usage: ./build-local.sh <package-name> <wheel-path> [version]
#
# Examples:
#   ./build-local.sh plink /path/to/urgap-3.2.18-py3-none-any.whl 2.00a2.3-01
#   ./build-local.sh plink /path/to/urgap.whl  # Uses first version from package-information.json
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    echo "Usage: $0 <package-name> <wheel-path> [version]"
    echo ""
    echo "Arguments:"
    echo "  package-name  Name of the package to build (e.g., plink)"
    echo "  wheel-path    Path to the urgap wheel file"
    echo "  version       Optional: specific version to build (defaults to first in package-information.json)"
    echo ""
    echo "Examples:"
    echo "  $0 plink /path/to/urgap-3.2.18-py3-none-any.whl 2.00a2.3-01"
    echo "  $0 plink /path/to/urgap.whl"
    exit 1
}

# Check arguments
if [ $# -lt 2 ]; then
    usage
fi

PACKAGE_NAME="$1"
WHEEL_PATH="$2"
VERSION="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/$PACKAGE_NAME"
JSON_FILE="$SCRIPT_DIR/package-information.json"

# Validate inputs
if [ ! -d "$PACKAGE_DIR" ]; then
    log_error "Package directory not found: $PACKAGE_DIR"
    exit 1
fi

if [ ! -f "$PACKAGE_DIR/Dockerfile" ]; then
    log_error "Dockerfile not found: $PACKAGE_DIR/Dockerfile"
    exit 1
fi

if [ ! -f "$WHEEL_PATH" ]; then
    log_error "Wheel file not found: $WHEEL_PATH"
    exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
    log_error "package-information.json not found: $JSON_FILE"
    exit 1
fi

# Get package info from JSON
PACKAGE_INFO=$(python3 -c "
import json
import sys

with open('$JSON_FILE') as f:
    data = json.load(f)

for pkg in data.get('packages', []):
    if pkg['name'] == '$PACKAGE_NAME':
        print(json.dumps(pkg))
        sys.exit(0)

sys.exit(1)
" 2>/dev/null) || {
    log_error "Package '$PACKAGE_NAME' not found in package-information.json"
    exit 1
}

# Extract package details
BASE_IMAGE=$(echo "$PACKAGE_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin).get('base_image', ''))")
SEPARATE_VENV=$(echo "$PACKAGE_INFO" | python3 -c "import json,sys; print(str(json.load(sys.stdin).get('separate_venv', False)).lower())")
VERSIONS=$(echo "$PACKAGE_INFO" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin).get('versions', [])))")

# Use provided version or first from list
if [ -z "$VERSION" ]; then
    VERSION=$(echo "$VERSIONS" | cut -d',' -f1)
    log_info "Using version: $VERSION (from package-information.json)"
fi

# Resolve base image (append version if ends with ':')
RESOLVED_BASE_IMAGE="$BASE_IMAGE"
if [[ "$BASE_IMAGE" == *: ]]; then
    RESOLVED_BASE_IMAGE="${BASE_IMAGE}${VERSION}"
fi

# Copy wheel to package directory
WHEEL_NAME=$(basename "$WHEEL_PATH")
cp "$WHEEL_PATH" "$PACKAGE_DIR/wheel/$WHEEL_NAME" 2>/dev/null || {
    mkdir -p "$PACKAGE_DIR/wheel"
    cp "$WHEEL_PATH" "$PACKAGE_DIR/wheel/$WHEEL_NAME"
}

log_info "Building Docker image for $PACKAGE_NAME:$VERSION"
log_info "Base image: $RESOLVED_BASE_IMAGE"
log_info "Wheel: $WHEEL_NAME"
log_info "Separate venv: $SEPARATE_VENV"

# Build image
IMAGE_TAG="$PACKAGE_NAME:$VERSION-local"

docker build \
    --build-arg BASEIMAGE="$RESOLVED_BASE_IMAGE" \
    --build-arg URGAP="wheel/$WHEEL_NAME" \
    -t "$IMAGE_TAG" \
    "$PACKAGE_DIR"

log_info "Build successful: $IMAGE_TAG"

# Run tests if they exist
TESTS_DIR="$PACKAGE_DIR/tests"
if [ -d "$TESTS_DIR" ] && [ -n "$(ls -A "$TESTS_DIR" 2>/dev/null)" ]; then
    log_info "Running tests..."

    CONTAINER_NAME="${PACKAGE_NAME}-test-$$"

    # Start container (override entrypoint in case image has one)
    docker run -d --entrypoint "" --name "$CONTAINER_NAME" "$IMAGE_TAG" sleep infinity

    # Copy tests into container
    docker cp "$TESTS_DIR" "$CONTAINER_NAME":/home/nonroot/tests

    # Run tests
    set +e
    if [ "$SEPARATE_VENV" == "true" ]; then
        docker exec "$CONTAINER_NAME" /home/nonroot/venv/bin/pip install pytest
        docker exec "$CONTAINER_NAME" /home/nonroot/venv/bin/pytest /home/nonroot/tests/
    else
        docker exec "$CONTAINER_NAME" pip3 install pytest
        docker exec "$CONTAINER_NAME" pytest /home/nonroot/tests/
    fi
    TEST_RESULT=$?
    set -e

    # Cleanup
    docker stop "$CONTAINER_NAME" >/dev/null
    docker rm "$CONTAINER_NAME" >/dev/null

    if [ $TEST_RESULT -eq 0 ]; then
        log_info "Tests passed!"
    else
        log_error "Tests failed!"
        exit 1
    fi
else
    log_warn "No tests found in $TESTS_DIR"
fi

# Cleanup wheel copy
rm -f "$PACKAGE_DIR/wheel/$WHEEL_NAME"
rmdir "$PACKAGE_DIR/wheel" 2>/dev/null || true

log_info "Done! Image available as: $IMAGE_TAG"
echo ""
echo "To run the container:"
echo "  docker run -it $IMAGE_TAG"

#!/bin/bash
set -euo pipefail

# Build a self-extracting installer for RaspiTalk using makeself.
# The output is a single .run file that can be copied to a Raspberry Pi
# and executed to install the application.
#
# Usage: ./build_installer.sh
# Output: raspitalk-installer.run

ROOT_DIR="$(cd "../$(dirname "$0")" && pwd)"
BUILD_DIR="$(mktemp -d)"
OUTPUT_FILE="${ROOT_DIR}/raspitalk-installer.run"

info() { echo "[INFO] $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

cleanup() { rm -rf "${BUILD_DIR}"; }
trap cleanup EXIT

# Check that makeself is installed
if ! command -v makeself &>/dev/null; then
    error "makeself is required but not installed. Install it with: sudo apt install makeself"
fi

info "Building RaspiTalk installer..."

# Copy application files into the build directory
info "Copying application files..."
cp -r "${ROOT_DIR}/src" "${BUILD_DIR}/"
cp -r "${ROOT_DIR}/resources" "${BUILD_DIR}/"
cp -r "${ROOT_DIR}/launchers" "${BUILD_DIR}/"
cp -r "${ROOT_DIR}/tools" "${BUILD_DIR}/"
cp "${ROOT_DIR}/main.py" "${BUILD_DIR}/"
cp "${ROOT_DIR}/pyproject.toml" "${BUILD_DIR}/"
cp "${ROOT_DIR}/uv.lock" "${BUILD_DIR}/"
cp "${ROOT_DIR}/.python-version" "${BUILD_DIR}/"
cp "${ROOT_DIR}/install.sh" "${BUILD_DIR}/"
cp "${ROOT_DIR}/uninstall.sh" "${BUILD_DIR}/"
chmod +x "${BUILD_DIR}/install.sh" "${BUILD_DIR}/uninstall.sh"

# Build the self-extracting installer
info "Creating self-extracting archive..."
makeself "${BUILD_DIR}" "${OUTPUT_FILE}" "Raspitalk Installer" ./install.sh

info "Installer built: ${OUTPUT_FILE}"
info ""
info "Copy it to the Raspberry Pi and run:"
info "  sudo ./raspitalk-installer.run"

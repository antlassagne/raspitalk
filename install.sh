#!/bin/bash
set -euo pipefail

# RaspiTalk Installer
# Installs the RaspiTalk application on a Raspberry Pi

INSTALL_DIR="/usr/local/raspitalk"
SERVICE_FILE="laboite.service"
SERVICE_USER="${SUDO_USER:-pi}"

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    error "This installer must be run as root (use sudo)."
fi

info "Starting RaspiTalk installation..."

# --- Step 1: Install system dependencies ---
info "Installing system dependencies..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    libportaudio2 \
    portaudio19-dev \
    git-lfs

# --- Step 2: Install uv (Python package manager) if not present ---
if ! command -v uv &>/dev/null; then
    info "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # When running under sudo, uv is installed to the invoking user's home
    if [ -n "${SUDO_USER:-}" ]; then
        SUDO_USER_HOME="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
        export PATH="${SUDO_USER_HOME}/.local/bin:$PATH"
    else
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if ! command -v uv &>/dev/null; then
        error "Failed to install uv. Please install it manually: https://docs.astral.sh/uv/"
    fi
fi
info "uv is available at $(command -v uv)"

# --- Step 3: Copy application files ---
info "Installing application to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"

# Determine the source directory (where the installer is running from)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Copy application files
cp -r "${SCRIPT_DIR}/src" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/resources" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/launchers" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/tools" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/main.py" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/pyproject.toml" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/uv.lock" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/.python-version" "${INSTALL_DIR}/"

# --- Step 4: Set up Python virtual environment ---
info "Setting up Python virtual environment..."
cd "${INSTALL_DIR}"
uv sync

# --- Step 5: Set ownership ---
info "Setting file ownership to ${SERVICE_USER}..."
if ! id "${SERVICE_USER}" &>/dev/null; then
    warn "User '${SERVICE_USER}' does not exist. Skipping ownership change."
    warn "You may need to run: sudo chown -R <user>: ${INSTALL_DIR}"
else
    chown -R "${SERVICE_USER}:" "${INSTALL_DIR}"
fi

# --- Step 6: Install systemd service ---
info "Installing systemd service..."
cp "${INSTALL_DIR}/launchers/${SERVICE_FILE}" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "${SERVICE_FILE}"

info "Installation complete!"
info "  Application installed to: ${INSTALL_DIR}"
info "  Service installed: ${SERVICE_FILE}"
info ""
info "To start the service now:"
info "  sudo systemctl start ${SERVICE_FILE}"
info ""
info "To check service status:"
info "  sudo systemctl status ${SERVICE_FILE}"
info ""
info "Remember to also set up the remote services (Ollama, STT, TTS)"
info "on your worker machine. See the README for details."

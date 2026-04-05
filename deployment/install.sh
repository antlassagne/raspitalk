#!/bin/bash
set -euo pipefail

# RaspiTalk Installer
# Installs the RaspiTalk application on a Raspberry Pi

INSTALL_DIR="/usr/local/raspitalk"
SERVICE_FILE="laboite.service"
SERVICE_USER="raspitalk"

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
    info "uv not found, installing..."
    snap install uv --classic || error "Failed to install uv. Please install it manually and re-run the installer."
    info "uv is available at $(command -v uv)"
else
    info "uv is already installed at $(command -v uv)"
fi

# --- Step 3: Copy application files ---
info "Installing application to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"

# Determine the source directory (where the installer is running from)
ROOT_DIR="$(cd "../$(dirname "$0")" && pwd)"

# Copy application files
cp -r "${ROOT_DIR}/src" "${INSTALL_DIR}/"
cp -r "${ROOT_DIR}/resources" "${INSTALL_DIR}/"
cp -r "${ROOT_DIR}/launchers" "${INSTALL_DIR}/"
cp -r "${ROOT_DIR}/tools" "${INSTALL_DIR}/"
cp "${ROOT_DIR}/main.py" "${INSTALL_DIR}/"
cp "${ROOT_DIR}/pyproject.toml" "${INSTALL_DIR}/"
cp "${ROOT_DIR}/uv.lock" "${INSTALL_DIR}/"
cp "${ROOT_DIR}/.python-version" "${INSTALL_DIR}/"

# --- Step 4: Set up Python virtual environment ---
info "Setting up Python virtual environment..."
cd "${INSTALL_DIR}"
uv sync

# --- Step 5: Set ownership ---
info "Setting file ownership to ${SERVICE_USER}..."
if ! id "${SERVICE_USER}" &>/dev/null; then
    warn "User '${SERVICE_USER}' does not exist yet, creating it..."
    useradd $SERVICE_USER
    chown -R "${SERVICE_USER}:" "${INSTALL_DIR}"
else
    chown -R "${SERVICE_USER}:" "${INSTALL_DIR}"
fi

# --- Step 6: Install systemd user service ---
info "Installing systemd user service..."
USER_HOME=$(eval echo "~${SERVICE_USER}")
mkdir -p "${USER_HOME}/.config/systemd/user"
cp "${INSTALL_DIR}/launchers/${SERVICE_FILE}" "${USER_HOME}/.config/systemd/user/laboite@.service"
chown -R "${SERVICE_USER}:" "${USER_HOME}/.config"

# Enable lingering so user services start at boot without a login session
loginctl enable-linger "${SERVICE_USER}"

# Reload and enable the user service
systemctl --user daemon-reload
systemctl --user enable --now "laboite@${SERVICE_USER}"

info "Installation complete!"
info "  Application installed to: ${INSTALL_DIR}"
info "  Service installed: laboite@${SERVICE_USER} (user service)"
info ""
info "To start the service now:"
info "  systemctl --user start laboite@${SERVICE_USER}"
info ""
info "To check service status:"
info "  systemctl --user status laboite@${SERVICE_USER}"
info ""
info "To check logs:"
info "  journalctl --user -u laboite@${SERVICE_USER} -f"
info ""
info "Remember to also set up the remote services (Ollama, STT, TTS) if you want the AI features."
info "on your worker machine. See the README for details."

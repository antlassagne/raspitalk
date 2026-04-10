#!/bin/bash
set -euo pipefail

# RaspiTalk Installer
# Installs the RaspiTalk application on a Raspberry Pi

INSTALL_DIR="/usr/local/raspitalk"
SERVICE_FILE="laboite.service"
GENERIC_SERVICE_FILE="laboite@.service"
RASPITALK_USER_SERVICE="laboite@raspitalk"
SERVICE_USER="raspitalk"

if [[ ${LOG_LEVEL:-} == "DEBUG" ]]; then
    set -x
fi

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# Check for root privileges
if [ "$(id -u)" -eq 0 ]; then
    error "This installer must not be run as root."
fi

info "Starting RaspiTalk installation..."

# --- Step 1: Install system dependencies ---
info "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    libportaudio2 \
    portaudio19-dev

# --- Step 2: Install uv (Python package manager) if not present ---
if ! command -v uv &>/dev/null; then
    info "uv not found, installing..."
    sudo snap install uv --classic || error "Failed to install uv. Please install it manually and re-run the installer."
fi
UV_BIN="$(command -v uv)" || error "uv not found in PATH after installation."
info "uv is available at ${UV_BIN}"

# --- Step 3: Copy application files ---
info "Installing application to ${INSTALL_DIR}..."
sudo mkdir -p "${INSTALL_DIR}"

# Determine the source directory (where the installer is running from)
ROOT_DIR="$(cd "$(dirname "$0")/../" && pwd)"

# Copy application files
sudo cp -r "${ROOT_DIR}/src" "${INSTALL_DIR}/"
sudo cp -r "${ROOT_DIR}/resources" "${INSTALL_DIR}/"
sudo cp -r "${ROOT_DIR}/deployment" "${INSTALL_DIR}/"
sudo cp -r "${ROOT_DIR}/tools" "${INSTALL_DIR}/"
sudo cp "${ROOT_DIR}/main.py" "${INSTALL_DIR}/"
sudo cp "${ROOT_DIR}/pyproject.toml" "${INSTALL_DIR}/"
sudo cp "${ROOT_DIR}/uv.lock" "${INSTALL_DIR}/"
sudo cp "${ROOT_DIR}/.python-version" "${INSTALL_DIR}/"

# --- Step 4: Create service user and set ownership ---
info "Setting file ownership to ${SERVICE_USER}..."
if ! id "${SERVICE_USER}" &>/dev/null; then
    warn "User '${SERVICE_USER}' does not exist yet, creating it..."
    sudo useradd -m "${SERVICE_USER}"
fi
sudo chown -R "${SERVICE_USER}:" "${INSTALL_DIR}"

# --- Step 5: Set up Python virtual environment (as service user) ---
info "Setting up Python virtual environment..."
sudo -u "${SERVICE_USER}" "${UV_BIN}" sync --directory "${INSTALL_DIR}"

# --- Step 6: Install systemd user service ---
info "Installing systemd user service..."
USER_HOME=$(eval echo "~${SERVICE_USER}")
sudo mkdir -p "${USER_HOME}/.config/systemd/user"
sudo cp "${INSTALL_DIR}/deployment/${SERVICE_FILE}" "${USER_HOME}/.config/systemd/user/${GENERIC_SERVICE_FILE}"
sudo chown -R "${SERVICE_USER}:" "${USER_HOME}/.config"

# Enable lingering so user services start at boot without a login session
sudo loginctl enable-linger "${SERVICE_USER}"

# Start the user's systemd instance and connect to it
SERVICE_USER_UID=$(id -u "${SERVICE_USER}")
sudo systemctl start "user@${SERVICE_USER_UID}.service"

_run_as_user() {
    sudo -u "${SERVICE_USER}" \
        HOME="${USER_HOME}" \
        XDG_RUNTIME_DIR="/run/user/${SERVICE_USER_UID}" \
        DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${SERVICE_USER_UID}/bus" \
        "$@"
}

# Reload and enable the user service
_run_as_user systemctl --user daemon-reload
_run_as_user systemctl --user enable --now "${RASPITALK_USER_SERVICE}"

info "Installation complete!"
info "  Application installed to: ${INSTALL_DIR}"
info "  Service installed and started: ${RASPITALK_USER_SERVICE} (user service)"
info ""
info "Now, run 'sudo su raspitalk' and 'export XDG_RUNTIME_DIR=/run/user/$(id -u raspitalk)' to interact with the service as the raspitalk user."
info ""
info "To check service status:"
info "  systemctl --user status ${RASPITALK_USER_SERVICE}"
info ""
info "To check logs:"
info "  journalctl --user -u ${RASPITALK_USER_SERVICE} -f"
info ""
info "Remember to also set up the remote services (Ollama, STT, TTS) if you want the AI features"
info "on your worker machine. See the README for details."

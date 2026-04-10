#!/bin/bash
set -euo pipefail

# RaspiTalk Uninstaller
# Removes the RaspiTalk application from the system

INSTALL_DIR="/usr/local/raspitalk"
SERVICE_USER="raspitalk"
SERVICE_NAME="laboite@${SERVICE_USER}"

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    error "This uninstaller must be run as root (use sudo)."
fi

info "Uninstalling RaspiTalk..."

# --- Step 1: Stop and disable the user service ---
if id "${SERVICE_USER}" &>/dev/null; then
    USER_HOME=$(eval echo "~${SERVICE_USER}")

    if sudo -u "${SERVICE_USER}" systemctl --user is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        info "Stopping ${SERVICE_NAME}..."
        sudo -u "${SERVICE_USER}" systemctl --user stop "${SERVICE_NAME}"
    fi

    if sudo -u "${SERVICE_USER}" systemctl --user is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        info "Disabling ${SERVICE_NAME}..."
        sudo -u "${SERVICE_USER}" systemctl --user disable "${SERVICE_NAME}"
    fi
else
    warn "User '${SERVICE_USER}' does not exist, skipping service cleanup."
fi

# --- Step 3: Remove the installation directory ---
if [ -d "${INSTALL_DIR}" ]; then
    info "Removing ${INSTALL_DIR}..."
    rm -rf "${INSTALL_DIR}"
fi

sudo userdel -f raspitalk
sudo rm -r /home/raspitalk || true
info "Raspitalk has been uninstalled."

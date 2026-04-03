#!/bin/bash
set -euo pipefail

# RaspiTalk Uninstaller
# Removes the RaspiTalk application from the system

INSTALL_DIR="/usr/local/raspilunii"
SERVICE_FILE="laboite.service"

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    error "This uninstaller must be run as root (use sudo)."
fi

info "Uninstalling RaspiTalk..."

# --- Step 1: Stop and disable the service ---
if systemctl is-active --quiet "${SERVICE_FILE}" 2>/dev/null; then
    info "Stopping ${SERVICE_FILE}..."
    systemctl stop "${SERVICE_FILE}"
fi

if systemctl is-enabled --quiet "${SERVICE_FILE}" 2>/dev/null; then
    info "Disabling ${SERVICE_FILE}..."
    systemctl disable "${SERVICE_FILE}"
fi

# --- Step 2: Remove the service file ---
if [ -f "/etc/systemd/system/${SERVICE_FILE}" ]; then
    info "Removing service file..."
    rm "/etc/systemd/system/${SERVICE_FILE}"
    systemctl daemon-reload
fi

# --- Step 3: Remove the installation directory ---
if [ -d "${INSTALL_DIR}" ]; then
    info "Removing ${INSTALL_DIR}..."
    rm -rf "${INSTALL_DIR}"
fi

info "RaspiTalk has been uninstalled."

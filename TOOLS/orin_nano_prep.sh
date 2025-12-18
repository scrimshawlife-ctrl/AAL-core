#!/usr/bin/env bash
# Jetson Orin Nano bootstrap for AAL-Core.
# Installs system deps, builds a venv, installs Python deps,
# and emits a systemd unit file ready for brainstem handoff.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv}"
SERVICE_NAME="${SERVICE_NAME:-aal-core}"
SERVICE_FILE="$REPO_ROOT/TOOLS/${SERVICE_NAME}.service"
AAL_PORT="${AAL_PORT:-8000}"
RUN_TESTS="${RUN_TESTS:-0}"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"

echo "[AAL-Core] Preparing Jetson Orin Nano environment..."
echo " - Repo root: ${REPO_ROOT}"
echo " - Virtualenv: ${VENV_DIR}"
echo " - Service name: ${SERVICE_NAME}"
echo " - Port: ${AAL_PORT}"
echo " - Run tests: ${RUN_TESTS}"

ARCH="$(uname -m)"
if [[ "${ARCH}" != "aarch64" ]]; then
  echo " [warn] Host arch is '${ARCH}', expected 'aarch64' for Orin Nano."
fi

echo "[Step 1] Installing system dependencies (python3-venv, build-essential, jq)..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip python3-dev build-essential jq

echo "[Step 2] Building virtual environment..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip wheel
pip install --upgrade -r "${REPO_ROOT}/requirements.txt"

echo "[Step 3] Ensuring logs directory exists..."
mkdir -p "${REPO_ROOT}/logs"

if [[ "${RUN_TESTS}" == "1" ]]; then
  echo "[Step 4] Running smoke tests under pytest..."
  PYTHONPATH="${REPO_ROOT}" pytest
fi

echo "[Step 5] Emitting systemd unit to ${SERVICE_FILE}..."
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=AAL-Core overlay bus (Jetson Orin Nano)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
Environment=AAL_DEV_LOG_PAYLOAD=0
ExecStart=${VENV_DIR}/bin/uvicorn main:app --host 0.0.0.0 --port ${AAL_PORT}
Restart=on-failure
User=${SERVICE_USER}

[Install]
WantedBy=multi-user.target
EOF

echo "[DONE] Service template written to ${SERVICE_FILE}"
echo "To install:"
echo "  sudo cp ${SERVICE_FILE} /etc/systemd/system/${SERVICE_NAME}.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now ${SERVICE_NAME}.service"
echo
echo "Validate with:"
echo "  sudo systemctl status ${SERVICE_NAME}.service"
echo "  curl http://localhost:${AAL_PORT}/overlays"

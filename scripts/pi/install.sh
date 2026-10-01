#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo from the repository root: sudo bash scripts/pi/install.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y python3-venv python3-dev libsndfile1 libportaudio2 portaudio19-dev

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements-pi.txt
.venv/bin/pip install -e . --no-deps

echo "Installed inference environment. Export/validate the model and benchmark this Pi before live use."


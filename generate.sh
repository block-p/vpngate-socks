#!/bin/bash
set -e

LIMIT=10
AUTO_UP=false
SKIP_FETCH=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-fetch)
      SKIP_FETCH=true
      shift
      ;;
    --up)
      AUTO_UP=true
      shift
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    [0-9]*)
      LIMIT="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [ "$SKIP_FETCH" != "true" ]; then
    echo "============================================================"
    echo "[1/3] Fetching latest server configs from VPNGate..."
    echo "============================================================"
    python3 update_configs.py --limit "$LIMIT"
fi

echo "============================================================"
echo "[2/3] Mapping fixed ports and generating Xray outbounds..."
echo "============================================================"
python3 generate.py

if [ "$AUTO_UP" = true ]; then
    echo ""
    echo "============================================================"
    echo "[3/3] Starting containers with Docker Compose..."
    echo "============================================================"
    docker compose up -d --remove-orphans
    echo "[+] All containers started successfully!"
else
    echo ""
    echo "To start/apply in Docker:"
    echo "    docker compose up -d --remove-orphans"
    echo "Or automatically next time:"
    echo "    ./generate.sh --up"
fi

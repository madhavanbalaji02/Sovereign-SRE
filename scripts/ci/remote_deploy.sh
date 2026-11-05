#!/usr/bin/env bash
# Runs ON the EC2 instance via SSM Run Command (as root) from .github/workflows/deploy.yml.
# Fast-forwards the checkout to origin/main, reinstalls Python deps only when
# backend/requirements.txt changed, restarts the service and waits for /health.
set -euo pipefail

APP_DIR=/opt/sovereign-sre
APP_USER=ec2-user          # owns the checkout; git refuses root on it ("dubious ownership")
PYTHON=/usr/bin/python3.11 # the interpreter sovereign-sre.service runs on
SERVICE=sovereign-sre

cd "$APP_DIR"
as_app() { sudo -u "$APP_USER" -H "$@"; }

before_req=$(sha256sum backend/requirements.txt | cut -d' ' -f1)
before_rev=$(as_app git rev-parse --short HEAD)

as_app git fetch --quiet origin main
as_app git merge --ff-only --quiet origin/main

after_req=$(sha256sum backend/requirements.txt | cut -d' ' -f1)
after_rev=$(as_app git rev-parse --short HEAD)
echo "Checkout: ${before_rev} -> ${after_rev} ($(as_app git log -1 --format=%s))"

if [ "$before_req" != "$after_req" ]; then
  echo "backend/requirements.txt changed; installing dependencies"
  # t3.micro tmpfs is too small for large wheels; use an EBS-backed temp dir
  mkdir -p /opt/pip-tmp
  TMPDIR=/opt/pip-tmp "$PYTHON" -m pip install --no-cache-dir --quiet -r backend/requirements.txt
else
  echo "Dependencies unchanged; skipping pip install"
fi

systemctl restart "$SERVICE"

for _ in $(seq 1 45); do
  if body=$(curl -fsS --max-time 3 http://127.0.0.1:8000/health 2>/dev/null); then
    echo "$body"
    echo "DEPLOY_OK"
    exit 0
  fi
  sleep 2
done

echo "Service did not become healthy; recent logs:"
journalctl -u "$SERVICE" -n 60 --no-pager || true
exit 1

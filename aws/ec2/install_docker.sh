#!/bin/bash
set -e
exec > >(tee /var/log/sovereign-sre-docker.log) 2>&1
echo "=== $(date) Installing Docker ==="

amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user
echo "Docker installed"

echo "=== Downloading .env from S3 ==="
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="sovereign-sre-artifacts-${ACCOUNT_ID}"
aws s3 cp "s3://${BUCKET}/ec2-config/.env" /opt/sovereign-sre/.env
echo "Loaded .env"

echo "=== Stopping old service ==="
systemctl stop sovereign-sre 2>/dev/null || true

echo "=== Starting backend in Docker (Python 3.11) ==="
docker rm -f sovereign-sre 2>/dev/null || true

docker run -d \
  --name sovereign-sre \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /opt/sovereign-sre:/app \
  --env-file /opt/sovereign-sre/.env \
  -w /app \
  python:3.11-slim \
  bash -c "pip install fastapi 'uvicorn[standard]' pydantic pydantic-settings python-dotenv boto3 botocore httpx aiofiles rich tenacity -q && python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --log-level info"

echo "Waiting for container to start..."
sleep 30

docker ps --filter name=sovereign-sre
curl -s http://localhost:8000/health || echo "Health check failed"
echo "=== Docker logs ==="
docker logs sovereign-sre --tail 20
echo "=== Done ==="

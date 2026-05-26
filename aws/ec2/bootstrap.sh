#!/bin/bash
# Sovereign-SRE EC2 Bootstrap — runs once on first boot via EC2 UserData
# Targets: Amazon Linux 2023 (AL2023)
# Monitor: sudo tail -f /var/log/cloud-init-output.log
set -e
exec > >(tee /var/log/sovereign-sre-bootstrap.log) 2>&1

echo "=== Sovereign-SRE Bootstrap starting $(date) ==="

# System deps — AL2023 uses dnf (not yum; not amazon-linux-extras)
dnf update -y
dnf install -y python3.11 python3.11-pip git nginx

# Node.js 20 via NodeSource (EL9 / AL2023 compatible)
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs

# Clone repo
git clone https://github.com/madhavanbalaji02/Sovereign-SRE /opt/sovereign-sre
cd /opt/sovereign-sre

# Install Python deps — AL2023 ships python3.9; we pin to python3.11
python3.11 -m pip install --upgrade pip
python3.11 -m pip install \
  fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv \
  httpx aiofiles websockets \
  groq anthropic langchain langchain-core langchain-groq langchain-openai \
  langgraph crewai \
  boto3 botocore \
  psycopg2-binary \
  rich tenacity PyGithub \
  "sentence-transformers>=2.6.1,<3.0" \
  "transformers>=4.41.0,<5.0"

# Load secrets from SSM into .env
python3.11 -c "
import boto3, os
region = 'us-east-2'
ssm = boto3.client('ssm', region_name=region)
params = ssm.get_parameters_by_path(Path='/sovereign-sre', WithDecryption=True, Recursive=True)
lines = []
for p in params['Parameters']:
    key = p['Name'].split('/')[-1].upper().replace('-', '_')
    val = p['Value'].replace('\n', ' ')
    lines.append(f'{key}={val}')
# Add computed values
lines.append('BEDROCK_ENABLED=true')
lines.append('BEDROCK_DEFAULT_MODEL=haiku')
lines.append('BEDROCK_FALLBACK_TO_OLLAMA=true')
lines.append('HUMAN_APPROVAL_REQUIRED=true')
lines.append('GROQ_MODEL=llama-3.3-70b-versatile')
lines.append('AWS_DEFAULT_REGION=us-east-2')
with open('/opt/sovereign-sre/.env', 'w') as f:
    f.write('\n'.join(lines) + '\n')
print('SSM secrets loaded:', len(lines), 'vars')
"

# Set proper ownership
chown -R ec2-user:ec2-user /opt/sovereign-sre

# systemd service for FastAPI backend
cat > /etc/systemd/system/sovereign-sre.service << 'SVCEOF'
[Unit]
Description=Sovereign-SRE FastAPI Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/sovereign-sre
EnvironmentFile=/opt/sovereign-sre/.env
ExecStart=/usr/bin/python3.11 -m uvicorn backend.api.main:app \
  --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable sovereign-sre
systemctl start sovereign-sre

# nginx reverse proxy on port 80
cat > /etc/nginx/conf.d/sovereign-sre.conf << 'NGXEOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
NGXEOF

# Remove default nginx site
rm -f /etc/nginx/conf.d/default.conf

systemctl enable nginx
systemctl start nginx
systemctl reload nginx

echo "=== Bootstrap complete $(date) ==="
# AL2023 enforces IMDSv2 — must fetch a token before querying instance metadata
IMDS_TOKEN=$(curl -X PUT -s "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4)
echo "Backend: http://${PUBLIC_IP}/health"

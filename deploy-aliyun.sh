#!/bin/bash
# Deploy AutoPR to Alibaba Cloud ECS
# Prerequisites: aliyun CLI configured, Docker installed on ECS

set -e

REGION="${ALIYUN_REGION:-ap-southeast-1}"
INSTANCE_TYPE="ecs.t6-c1m1.small"   # ~$8/month, 1 vCPU 1GB
IMAGE_FAMILY="aliyun_3_x64_20G_alibase_20240819.vhd"

echo "=== AutoPR → Alibaba Cloud ECS ==="

# Option A: Run directly on an existing ECS instance
# Copy files + run docker
if [ -n "$ECS_IP" ]; then
    echo "Deploying to $ECS_IP..."
    ssh root@$ECS_IP "mkdir -p /opt/autopr"
    scp -r . root@$ECS_IP:/opt/autopr/
    ssh root@$ECS_IP << 'REMOTE'
        cd /opt/autopr
        docker build -t autopr .
        docker stop autopr 2>/dev/null || true
        docker rm autopr 2>/dev/null || true
        docker run -d \
            -e DASHSCOPE_API_KEY=$DASHSCOPE_API_KEY \
            -e GH_TOKEN=$GH_TOKEN \
            -p 7860:7860 \
            --restart=unless-stopped \
            --name autopr autopr
        echo "AutoPR running at http://$(hostname -I | awk '{print $1}'):7860"
REMOTE

# Option B: Alibaba Cloud Function Compute (serverless, free tier covers demos)
else
    echo "Hint: set ECS_IP=your.server.ip to deploy, or use Alibaba Cloud Function Compute:"
    echo ""
    echo "  1. Go to https://fc.console.aliyun.com"
    echo "  2. Create Service: autopr"
    echo "  3. Create Function: HTTP trigger, Docker image"
    echo "  4. Set env vars: DASHSCOPE_API_KEY, GH_TOKEN"
    echo "  5. Expose port 7860"
fi

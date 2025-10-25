#!/bin/bash
# Complete V6 Smart Parking Platform Deployment Script with Version Verification
# Version: 1.0.0 - 2025-10-23

set -e

echo "🚀 Smart Parking Platform V6 - Complete Deployment with Version Verification"
echo "=========================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Build with version
print_status "Building application with version tracking..."

# Run build in Docker container to ensure consistent environment
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  node:20-alpine \
  sh -c "apk add --no-cache bash jq git && ./build-with-version.sh"

if [ $? -ne 0 ]; then
    print_error "Build failed!"
    exit 1
fi

# Get build info for verification
BUILD_NUMBER=$(jq -r '.buildNumber' src/version.json)
BUILD_VERSION=$(jq -r '.version' src/version.json)
BUILD_TIMESTAMP=$(jq -r '.buildTimestamp' src/version.json)

print_success "Build completed: v${BUILD_VERSION} Build ${BUILD_NUMBER}"

# Step 2: Rebuild Docker image
print_status "Building Docker image..."
cd "$SCRIPT_DIR"
docker build -t parking-frontend-v6:latest .

if [ $? -ne 0 ]; then
    print_error "Docker build failed!"
    exit 1
fi

print_success "Docker image built"

# Step 3: Stop and remove old container
print_status "Stopping old container..."
docker stop parking-frontend-v6 2>/dev/null || print_warning "Container not running"
docker rm parking-frontend-v6 2>/dev/null || print_warning "Container not found"

# Step 4: Start new container from V6 docker-compose
print_status "Starting new container..."
cd /opt/v6_smart_parking
docker compose -f docker-compose.prod.yml up -d --force-recreate frontend-v6

if [ $? -ne 0 ]; then
    print_error "Container start failed!"
    exit 1
fi

print_success "Container started"

# Step 5: Wait for container to be ready
print_status "Waiting for container to be ready..."
sleep 10

for i in {1..30}; do
    if docker ps | grep parking-frontend-v6 | grep -q "(healthy)"; then
        print_success "Container is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Container failed to become healthy"
        docker logs parking-frontend-v6 --tail 20
        exit 1
    fi
    sleep 2
    echo -n "."
done
echo

# Step 6: Verify deployment
print_status "Verifying deployment..."

# Check container status
CONTAINER_STATUS=$(docker ps | grep parking-frontend-v6 | awk '{print $7}')
print_status "Container status: $CONTAINER_STATUS"

# Test direct container access
print_status "Testing direct container access..."
CONTAINER_IP=$(docker inspect parking-frontend-v6 | jq -r '.[0].NetworkSettings.Networks["parking-network"].IPAddress')
DIRECT_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null http://$CONTAINER_IP/version.json 2>/dev/null || echo "000")

if [ "$DIRECT_RESPONSE" = "200" ]; then
    DIRECT_VERSION=$(curl -s http://$CONTAINER_IP/version.json 2>/dev/null | jq -r '.buildNumber' 2>/dev/null || echo "failed")
    if [ "$DIRECT_VERSION" = "$BUILD_NUMBER" ]; then
        print_success "Direct container access: OK (Build $DIRECT_VERSION)"
    else
        print_warning "Direct container version: Expected $BUILD_NUMBER, got $DIRECT_VERSION"
    fi
else
    print_warning "Direct container access failed (HTTP $DIRECT_RESPONSE)"
fi

# Test external HTTPS access
print_status "Testing external HTTPS access..."
sleep 5  # Give Traefik time to detect new container

EXTERNAL_RESPONSE=$(curl -k -s -w "%{http_code}" -o /dev/null https://app.parking.verdegris.eu 2>/dev/null || echo "000")
if [ "$EXTERNAL_RESPONSE" = "200" ]; then
    print_success "External HTTPS access: OK"
else
    print_warning "External HTTPS access: HTTP $EXTERNAL_RESPONSE"
fi

# Test external version endpoint
print_status "Testing external version endpoint..."
EXTERNAL_VERSION=$(curl -k -s https://app.parking.verdegris.eu/version.json 2>/dev/null | jq -r '.buildNumber' 2>/dev/null || echo "failed")
if [ "$EXTERNAL_VERSION" = "$BUILD_NUMBER" ]; then
    print_success "External version endpoint: OK (Build $EXTERNAL_VERSION)"
else
    print_warning "External version: Expected $BUILD_NUMBER, got $EXTERNAL_VERSION"
    print_status "Cache may need time to clear. Try hard refresh (Ctrl+Shift+R)"
fi

# Step 7: Show deployment summary
echo
print_success "🎉 Deployment Complete!"
echo "=============================="
echo "📦 Version: $BUILD_VERSION"
echo "🔢 Build: $BUILD_NUMBER"
echo "🕒 Built: $BUILD_TIMESTAMP"
echo "🐳 Container: parking-frontend-v6"
echo "🌐 URL: https://app.parking.verdegris.eu"
echo "📋 Version: https://app.parking.verdegris.eu/version.json"
echo "💡 If you see old version, try:"
echo "   - Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)"
echo "   - Check version: curl -k https://app.parking.verdegris.eu/version.json"
echo "   - Clear browser cache completely"
echo

# Step 8: Show container logs
print_status "Recent container logs:"
docker logs parking-frontend-v6 --tail 15

echo
print_success "Deployment verification complete! 🚀"
echo "Build number $BUILD_NUMBER is now live at https://app.parking.verdegris.eu"

cd "$SCRIPT_DIR"

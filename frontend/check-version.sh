#!/bin/bash
# Quick version check script for V6 Smart Parking Platform
# Version: 1.0.0 - 2025-10-23

echo "🔍 Checking V6 Smart Parking Platform Versions"
echo "=============================================="
echo

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check local source version
if [ -f "src/version.json" ]; then
    echo -e "${BLUE}📁 Source Version (src/version.json):${NC}"
    jq '.' src/version.json
    echo
fi

# Check built version
if [ -f "dist/version.json" ]; then
    echo -e "${BLUE}📦 Built Version (dist/version.json):${NC}"
    jq '.' dist/version.json
    echo
fi

# Check running container
echo -e "${BLUE}🐳 Container Version:${NC}"
CONTAINER_IP=$(docker inspect parking-frontend-v6 2>/dev/null | jq -r '.[0].NetworkSettings.Networks["parking-v5_parking-network"].IPAddress' 2>/dev/null || echo "")
if [ -n "$CONTAINER_IP" ] && [ "$CONTAINER_IP" != "null" ]; then
    curl -s http://$CONTAINER_IP/version.json 2>/dev/null | jq '.' || echo "Failed to fetch container version"
else
    echo "Container not running or not accessible"
fi
echo

# Check production HTTPS
echo -e "${BLUE}🌍 Production (https://app.parking.verdegris.eu):${NC}"
curl -k -s https://app.parking.verdegris.eu/version.json 2>/dev/null | jq '.' || echo "Failed to fetch production version"
echo

# Quick comparison
SRC_BUILD=$(jq -r '.build' src/version.json 2>/dev/null || echo "0")
PROD_BUILD=$(curl -k -s https://app.parking.verdegris.eu/version.json 2>/dev/null | jq -r '.build' 2>/dev/null || echo "0")

echo "=============================================="
if [ "$SRC_BUILD" != "$PROD_BUILD" ]; then
    echo -e "${BLUE}📊 Status:${NC} Source build ($SRC_BUILD) differs from production ($PROD_BUILD)"
    echo "💡 Run ./deploy-with-version.sh to deploy latest build"
else
    echo -e "${GREEN}✅ Production is up to date with source (Build $SRC_BUILD)${NC}"
fi

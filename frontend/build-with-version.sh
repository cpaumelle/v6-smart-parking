#!/bin/bash
# Build script with auto-incrementing version for V6 Smart Parking Platform
# Version: 6.0.0 - 2025-10-23

set -e

echo "🚀 Smart Parking Platform V6 - Build with Version"
echo "================================================="

# Get current timestamp
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
BUILD_DATE=$(date -u +"%Y%m%d")
BUILD_TIME=$(date -u +"%H%M%S")

# Version file path
VERSION_FILE="src/version.json"

# Read current version or create if doesn't exist
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION=$(jq -r '.version' "$VERSION_FILE" 2>/dev/null || echo "6.0.0")
    CURRENT_BUILD=$(jq -r '.build' "$VERSION_FILE" 2>/dev/null || echo "0")
else
    CURRENT_VERSION="6.0.0"
    CURRENT_BUILD="0"
fi

# Extract just the integer part if build has decimal
CURRENT_BUILD_INT=$(echo "$CURRENT_BUILD" | cut -d. -f1)
if ! [[ "$CURRENT_BUILD_INT" =~ ^[0-9]+$ ]]; then
    CURRENT_BUILD_INT="0"
fi

# Increment build number
NEW_BUILD=$((CURRENT_BUILD_INT + 1))

# Get git commit
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')

# Create version info
cat > "$VERSION_FILE" << EOV
{
  "version": "$CURRENT_VERSION",
  "build": $NEW_BUILD,
  "buildNumber": "${BUILD_DATE}.${NEW_BUILD}",
  "buildTimestamp": "$BUILD_TIMESTAMP",
  "buildDate": "$BUILD_DATE",
  "buildTime": "$BUILD_TIME",
  "gitCommit": "$GIT_COMMIT",
  "commit": "$GIT_COMMIT",
  "description": "V6 Smart Parking Platform - Build $NEW_BUILD",
  "environment": "production"
}
EOV

echo "📦 Version: $CURRENT_VERSION"
echo "🔢 Build: $NEW_BUILD (previous: $CURRENT_BUILD)"
echo "🕒 Timestamp: $BUILD_TIMESTAMP"
echo "📋 Build Number: ${BUILD_DATE}.${NEW_BUILD}"
echo "🔧 Git Commit: $GIT_COMMIT"

# Copy version to public directory so it's included in build
mkdir -p public
cp "$VERSION_FILE" public/

# Set environment variables for build
export VITE_VERSION="$CURRENT_VERSION"
export VITE_BUILD_NUMBER="$NEW_BUILD"
export VITE_BUILD_TIMESTAMP="$BUILD_TIMESTAMP"
export VITE_BUILD_ID="${BUILD_DATE}.${NEW_BUILD}"

# Ensure all dependencies are installed (including devDependencies needed for build)
echo ""
echo "📦 Installing dependencies..."
if [ ! -d "node_modules" ]; then
    if [ -f "package-lock.json" ]; then
        npm ci
    else
        npm install
    fi
elif [ ! -f "node_modules/.package-lock.json" ]; then
    if [ -f "package-lock.json" ]; then
        npm ci
    else
        npm install
    fi
fi

# Run the actual build
echo ""
echo "🔨 Starting Vite build..."
npm run build

# Copy version.json to dist for nginx to serve
cp "$VERSION_FILE" dist/version.json

echo ""
echo "✅ Build complete!"
echo "📋 Build ID: ${BUILD_DATE}.${NEW_BUILD}"
echo "🌐 Version file available at: /version.json"
echo ""
echo "💡 Cache-busting info:"
echo "   - Build number incremented: $CURRENT_BUILD → $NEW_BUILD"
echo "   - Clients can check /version.json to detect new builds"
echo "   - HTML will have new asset hashes for cache invalidation"

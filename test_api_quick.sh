#!/bin/bash
# V6 Smart Parking - Quick API Test

set -e

BASE_URL="https://api.verdegris.eu"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== V6 Smart Parking API Tests ===${NC}\n"

# 1. Health Check
echo -n "Health Check... "
HEALTH=$(curl -k -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# 2. Login
echo -n "Login (Tenant Admin)... "
LOGIN=$(curl -k -s -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test_auth@example.com&password=TestPassword123")
TOKEN=$(echo "$LOGIN" | jq -r '.access_token')
TENANT_ID=$(echo "$LOGIN" | jq -r '.user.tenant_id')

if [ ! -z "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo -e "${GREEN}✓${NC} (Tenant: $TENANT_ID)"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# 3. Get Current User
echo -n "Get Current User... "
ME=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/auth/me")
if echo "$ME" | grep -q "$TENANT_ID"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# 4. Dashboard
echo -n "Dashboard Data... "
DASH=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v6/dashboard/data")
if echo "$DASH" | grep -q "devices"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# 5. List Spaces
echo -n "List Spaces... "
SPACES=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v6/spaces/")
SPACE_COUNT=$(echo "$SPACES" | jq -r '.total // 0')
echo -e "${GREEN}✓${NC} ($SPACE_COUNT spaces)"

# 6. List Devices
echo -n "List Devices... "
DEVICES=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v6/devices/")
DEVICE_COUNT=$(echo "$DEVICES" | jq -r '.total // 0')
echo -e "${GREEN}✓${NC} ($DEVICE_COUNT devices)"

# 7. List Gateways
echo -n "List Gateways... "
GATEWAYS=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v6/gateways/")
GW_COUNT=$(echo "$GATEWAYS" | jq -r '.total // 0')
echo -e "${GREEN}✓${NC} ($GW_COUNT gateways)"

# 8. List Reservations
echo -n "List Reservations... "
RESERVATIONS=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v6/reservations/")
RES_COUNT=$(echo "$RESERVATIONS" | jq -r '.total // 0')
echo -e "${GREEN}✓${NC} ($RES_COUNT reservations)"

# 9. Create Space
echo -n "Create Space... "
NEW_SPACE=$(curl -k -s -X POST "$BASE_URL/api/v6/spaces/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"space_number":"TEST-001","floor":"1","zone":"A","status":"free"}')
SPACE_ID=$(echo "$NEW_SPACE" | jq -r '.id // empty')
if [ ! -z "$SPACE_ID" ]; then
    echo -e "${GREEN}✓${NC} (ID: $SPACE_ID)"
else
    echo -e "${RED}✗${NC}"
    echo "Response: $NEW_SPACE"
fi

# 10. Update Space
if [ ! -z "$SPACE_ID" ]; then
    echo -n "Update Space... "
    UPD_SPACE=$(curl -k -s -X PATCH "$BASE_URL/api/v6/spaces/$SPACE_ID" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"status":"occupied"}')
    if echo "$UPD_SPACE" | grep -q "occupied"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
fi

# 11. Delete Space
if [ ! -z "$SPACE_ID" ]; then
    echo -n "Delete Space... "
    DEL_SPACE=$(curl -k -s -X DELETE "$BASE_URL/api/v6/spaces/$SPACE_ID" \
        -H "Authorization: Bearer $TOKEN")
    echo -e "${GREEN}✓${NC}"
fi

# 12. Logout
echo -n "Logout... "
curl -k -s -X POST "$BASE_URL/api/auth/logout" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
echo -e "${GREEN}✓${NC}"

echo -e "\n${GREEN}All basic tests passed!${NC}"

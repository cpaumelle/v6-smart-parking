#!/bin/bash
# V6 Smart Parking Platform - Comprehensive API Test Suite
# Tests all endpoints for both Tenant Admin and Platform Admin roles

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Base URL
BASE_URL="${BASE_URL:-https://api.verdegris.eu}"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test results array
declare -a FAILED_TEST_DETAILS

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo -e "${RED}       $2${NC}"
    FAILED_TEST_DETAILS+=("FAILED: $1 - $2")
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    local token=$5
    local data=$6

    print_test "$description"

    local curl_cmd="curl -k -s -w \"\\n%{http_code}\" -X $method \"$BASE_URL$endpoint\""

    if [ ! -z "$token" ]; then
        curl_cmd="$curl_cmd -H \"Authorization: Bearer $token\""
    fi

    if [ ! -z "$data" ]; then
        curl_cmd="$curl_cmd -H \"Content-Type: application/json\" -d '$data'"
    fi

    # Execute request
    response=$(eval $curl_cmd)
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    # Check status code
    if [ "$status_code" == "$expected_status" ]; then
        print_success "$description (HTTP $status_code)"
        echo "$body" | jq '.' >/dev/null 2>&1 || true
    else
        print_fail "$description" "Expected HTTP $expected_status, got $status_code. Response: $(echo $body | head -c 200)"
    fi
}

# Generate test report
generate_report() {
    print_header "TEST EXECUTION SUMMARY"
    echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "\n${RED}Failed Test Details:${NC}"
        for detail in "${FAILED_TEST_DETAILS[@]}"; do
            echo -e "${RED}- $detail${NC}"
        done
    fi

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}✅ ALL TESTS PASSED!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ SOME TESTS FAILED${NC}"
        exit 1
    fi
}

# Don't trap yet - only at the end
# trap generate_report EXIT

# Start tests
print_header "V6 SMART PARKING PLATFORM - COMPREHENSIVE API TEST SUITE"
print_info "Base URL: $BASE_URL"
print_info "Test Date: $(date)"

##############################################################################
# PHASE 1: AUTHENTICATION & SETUP
##############################################################################

print_header "PHASE 1: AUTHENTICATION & SETUP"

# 1.1 Health Check (No Auth)
test_endpoint "GET" "/health" "200" "Health check endpoint" "" ""

# 1.2 Login as Tenant Admin
print_info "Logging in as Tenant Admin..."
LOGIN_RESPONSE=$(curl -k -s -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test_auth@example.com&password=TestPassword123")

TENANT_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
TENANT_ID=$(echo $LOGIN_RESPONSE | jq -r '.user.tenant_id')
USER_ID=$(echo $LOGIN_RESPONSE | jq -r '.user.id')

if [ "$TENANT_TOKEN" != "null" ] && [ ! -z "$TENANT_TOKEN" ]; then
    print_success "Tenant Admin login successful"
    print_info "Tenant ID: $TENANT_ID"
    print_info "User ID: $USER_ID"
else
    print_fail "Tenant Admin login" "Failed to get access token"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# 1.3 Test /auth/me endpoint
test_endpoint "GET" "/api/auth/me" "200" "Get current user info (Tenant Admin)" "$TENANT_TOKEN" ""

# 1.4 Test token refresh
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')
if [ "$REFRESH_TOKEN" != "null" ]; then
    print_test "Token refresh"
    REFRESH_RESPONSE=$(curl -k -s -X POST "$BASE_URL/api/auth/refresh" \
        -H "Content-Type: application/json" \
        -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")
    NEW_TOKEN=$(echo $REFRESH_RESPONSE | jq -r '.access_token')
    if [ "$NEW_TOKEN" != "null" ] && [ ! -z "$NEW_TOKEN" ]; then
        print_success "Token refresh successful"
    else
        print_fail "Token refresh" "Failed to get new token"
    fi
fi

##############################################################################
# PHASE 2: DASHBOARD TESTS
##############################################################################

print_header "PHASE 2: DASHBOARD TESTS"

test_endpoint "GET" "/api/v6/dashboard/data" "200" "Get dashboard data (Tenant Admin)" "$TENANT_TOKEN" ""

##############################################################################
# PHASE 3: SPACE MANAGEMENT TESTS
##############################################################################

print_header "PHASE 3: SPACE MANAGEMENT TESTS"

# 3.1 List spaces
test_endpoint "GET" "/api/v6/spaces/" "200" "List all spaces (Tenant Admin)" "$TENANT_TOKEN" ""

# 3.2 List spaces with pagination
test_endpoint "GET" "/api/v6/spaces/?page=1&page_size=10" "200" "List spaces with pagination" "$TENANT_TOKEN" ""

# 3.3 Create a new space
print_test "Create new space"
CREATE_SPACE_DATA='{
    "space_number": "TEST-001",
    "floor": "1",
    "zone": "A",
    "status": "free",
    "metadata": {"test": true}
}'
CREATE_SPACE_RESPONSE=$(curl -k -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v6/spaces/" \
    -H "Authorization: Bearer $TENANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CREATE_SPACE_DATA")
CREATE_SPACE_STATUS=$(echo "$CREATE_SPACE_RESPONSE" | tail -n1)
CREATE_SPACE_BODY=$(echo "$CREATE_SPACE_RESPONSE" | head -n-1)

if [ "$CREATE_SPACE_STATUS" == "201" ] || [ "$CREATE_SPACE_STATUS" == "200" ]; then
    SPACE_ID=$(echo "$CREATE_SPACE_BODY" | jq -r '.id')
    print_success "Create new space (HTTP $CREATE_SPACE_STATUS)"
    print_info "Created Space ID: $SPACE_ID"
else
    print_fail "Create new space" "Expected HTTP 201, got $CREATE_SPACE_STATUS"
    SPACE_ID=""
fi

# 3.4 Get space details
if [ ! -z "$SPACE_ID" ]; then
    test_endpoint "GET" "/api/v6/spaces/$SPACE_ID" "200" "Get space details" "$TENANT_TOKEN" ""
fi

# 3.5 Update space
if [ ! -z "$SPACE_ID" ]; then
    UPDATE_SPACE_DATA='{
        "status": "occupied"
    }'
    test_endpoint "PATCH" "/api/v6/spaces/$SPACE_ID" "200" "Update space status" "$TENANT_TOKEN" "$UPDATE_SPACE_DATA"
fi

# 3.6 Get space stats (if endpoint exists)
test_endpoint "GET" "/api/v6/spaces/stats" "200" "Get space statistics" "$TENANT_TOKEN" ""

##############################################################################
# PHASE 4: DEVICE MANAGEMENT TESTS
##############################################################################

print_header "PHASE 4: DEVICE MANAGEMENT TESTS"

# 4.1 List all devices
test_endpoint "GET" "/api/v6/devices/" "200" "List all devices (Tenant Admin)" "$TENANT_TOKEN" ""

# 4.2 List devices with pagination
test_endpoint "GET" "/api/v6/devices/?page=1&page_size=10" "200" "List devices with pagination" "$TENANT_TOKEN" ""

# 4.3 List sensors only
test_endpoint "GET" "/api/v6/devices/sensors/" "200" "List sensors only" "$TENANT_TOKEN" ""

# 4.4 List displays only
test_endpoint "GET" "/api/v6/devices/displays/" "200" "List displays only" "$TENANT_TOKEN" ""

# 4.5 Create a new device (sensor)
print_test "Create new sensor device"
CREATE_DEVICE_DATA='{
    "dev_eui": "TEST1234567890AB",
    "name": "Test Sensor 001",
    "type": "sensor",
    "location": "Test Location",
    "metadata": {"test": true}
}'
CREATE_DEVICE_RESPONSE=$(curl -k -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v6/devices/" \
    -H "Authorization: Bearer $TENANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CREATE_DEVICE_DATA")
CREATE_DEVICE_STATUS=$(echo "$CREATE_DEVICE_RESPONSE" | tail -n1)
CREATE_DEVICE_BODY=$(echo "$CREATE_DEVICE_RESPONSE" | head -n-1)

if [ "$CREATE_DEVICE_STATUS" == "201" ] || [ "$CREATE_DEVICE_STATUS" == "200" ]; then
    DEVICE_ID=$(echo "$CREATE_DEVICE_BODY" | jq -r '.id')
    print_success "Create new sensor device (HTTP $CREATE_DEVICE_STATUS)"
    print_info "Created Device ID: $DEVICE_ID"
else
    print_fail "Create new sensor device" "Expected HTTP 201, got $CREATE_DEVICE_STATUS. Response: $(echo $CREATE_DEVICE_BODY | head -c 200)"
    DEVICE_ID=""
fi

# 4.6 Get device details
if [ ! -z "$DEVICE_ID" ]; then
    test_endpoint "GET" "/api/v6/devices/$DEVICE_ID" "200" "Get device details" "$TENANT_TOKEN" ""
fi

# 4.7 Update device
if [ ! -z "$DEVICE_ID" ]; then
    UPDATE_DEVICE_DATA='{
        "name": "Test Sensor 001 (Updated)"
    }'
    test_endpoint "PUT" "/api/v6/devices/$DEVICE_ID" "200" "Update device" "$TENANT_TOKEN" "$UPDATE_DEVICE_DATA"
fi

# 4.8 Assign device to space
if [ ! -z "$DEVICE_ID" ] && [ ! -z "$SPACE_ID" ]; then
    ASSIGN_DATA="{\"space_id\":\"$SPACE_ID\"}"
    test_endpoint "POST" "/api/v6/devices/$DEVICE_ID/assign" "200" "Assign device to space" "$TENANT_TOKEN" "$ASSIGN_DATA"
fi

# 4.9 Unassign device
if [ ! -z "$DEVICE_ID" ]; then
    test_endpoint "POST" "/api/v6/devices/$DEVICE_ID/unassign" "200" "Unassign device from space" "$TENANT_TOKEN" ""
fi

##############################################################################
# PHASE 5: GATEWAY MANAGEMENT TESTS
##############################################################################

print_header "PHASE 5: GATEWAY MANAGEMENT TESTS"

# 5.1 List all gateways
test_endpoint "GET" "/api/v6/gateways/" "200" "List all gateways (Tenant Admin)" "$TENANT_TOKEN" ""

# 5.2 Create a new gateway
print_test "Create new gateway"
CREATE_GATEWAY_DATA='{
    "gateway_eui": "TESTGW1234567890",
    "name": "Test Gateway 001",
    "location": "Test Location",
    "metadata": {"test": true}
}'
CREATE_GATEWAY_RESPONSE=$(curl -k -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v6/gateways/" \
    -H "Authorization: Bearer $TENANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CREATE_GATEWAY_DATA")
CREATE_GATEWAY_STATUS=$(echo "$CREATE_GATEWAY_RESPONSE" | tail -n1)
CREATE_GATEWAY_BODY=$(echo "$CREATE_GATEWAY_RESPONSE" | head -n-1)

if [ "$CREATE_GATEWAY_STATUS" == "201" ] || [ "$CREATE_GATEWAY_STATUS" == "200" ]; then
    GATEWAY_ID=$(echo "$CREATE_GATEWAY_BODY" | jq -r '.id')
    print_success "Create new gateway (HTTP $CREATE_GATEWAY_STATUS)"
    print_info "Created Gateway ID: $GATEWAY_ID"
else
    print_fail "Create new gateway" "Expected HTTP 201, got $CREATE_GATEWAY_STATUS"
    GATEWAY_ID=""
fi

# 5.3 Get gateway details
if [ ! -z "$GATEWAY_ID" ]; then
    test_endpoint "GET" "/api/v6/gateways/$GATEWAY_ID" "200" "Get gateway details" "$TENANT_TOKEN" ""
fi

##############################################################################
# PHASE 6: RESERVATION MANAGEMENT TESTS
##############################################################################

print_header "PHASE 6: RESERVATION MANAGEMENT TESTS"

# 6.1 List all reservations
test_endpoint "GET" "/api/v6/reservations/" "200" "List all reservations (Tenant Admin)" "$TENANT_TOKEN" ""

# 6.2 Create a new reservation
if [ ! -z "$SPACE_ID" ]; then
    print_test "Create new reservation"
    START_TIME=$(date -u -d "+1 hour" +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME=$(date -u -d "+3 hours" +"%Y-%m-%dT%H:%M:%SZ")
    CREATE_RESERVATION_DATA="{
        \"space_id\": \"$SPACE_ID\",
        \"user_email\": \"test@example.com\",
        \"start_time\": \"$START_TIME\",
        \"end_time\": \"$END_TIME\",
        \"status\": \"active\"
    }"
    CREATE_RESERVATION_RESPONSE=$(curl -k -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v6/reservations/" \
        -H "Authorization: Bearer $TENANT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$CREATE_RESERVATION_DATA")
    CREATE_RESERVATION_STATUS=$(echo "$CREATE_RESERVATION_RESPONSE" | tail -n1)
    CREATE_RESERVATION_BODY=$(echo "$CREATE_RESERVATION_RESPONSE" | head -n-1)

    if [ "$CREATE_RESERVATION_STATUS" == "201" ] || [ "$CREATE_RESERVATION_STATUS" == "200" ]; then
        RESERVATION_ID=$(echo "$CREATE_RESERVATION_BODY" | jq -r '.id')
        print_success "Create new reservation (HTTP $CREATE_RESERVATION_STATUS)"
        print_info "Created Reservation ID: $RESERVATION_ID"
    else
        print_fail "Create new reservation" "Expected HTTP 201, got $CREATE_RESERVATION_STATUS"
        RESERVATION_ID=""
    fi
fi

# 6.3 Get reservation details
if [ ! -z "$RESERVATION_ID" ]; then
    test_endpoint "GET" "/api/v6/reservations/$RESERVATION_ID" "200" "Get reservation details" "$TENANT_TOKEN" ""
fi

##############################################################################
# PHASE 7: TENANT ISOLATION TESTS
##############################################################################

print_header "PHASE 7: TENANT ISOLATION TESTS"

# 7.1 Try to access tenant management (should fail for tenant admin)
test_endpoint "GET" "/api/v6/tenants/" "401" "Access tenants endpoint (should fail)" "$TENANT_TOKEN" ""

# Note: We would need a second tenant to test cross-tenant access properly
print_info "Tenant isolation test requires second tenant - skipping cross-tenant access tests"

##############################################################################
# PHASE 8: CLEANUP (Delete test resources)
##############################################################################

print_header "PHASE 8: CLEANUP"

# Delete created resources
if [ ! -z "$RESERVATION_ID" ]; then
    test_endpoint "DELETE" "/api/v6/reservations/$RESERVATION_ID" "200" "Delete test reservation" "$TENANT_TOKEN" ""
fi

if [ ! -z "$GATEWAY_ID" ]; then
    test_endpoint "DELETE" "/api/v6/gateways/$GATEWAY_ID" "200" "Delete test gateway" "$TENANT_TOKEN" ""
fi

if [ ! -z "$DEVICE_ID" ]; then
    test_endpoint "DELETE" "/api/v6/devices/$DEVICE_ID" "200" "Delete test device" "$TENANT_TOKEN" ""
fi

if [ ! -z "$SPACE_ID" ]; then
    test_endpoint "DELETE" "/api/v6/spaces/$SPACE_ID" "200" "Delete test space" "$TENANT_TOKEN" ""
fi

# Logout
test_endpoint "POST" "/api/auth/logout" "200" "Logout (Tenant Admin)" "$TENANT_TOKEN" ""

print_header "TEST SUITE COMPLETE"

# Generate final report
generate_report

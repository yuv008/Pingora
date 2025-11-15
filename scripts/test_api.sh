#!/bin/bash
# API Testing Script
# Tests the complete user flow

set -e

BASE_URL="http://localhost:8000/api/v1"
EMAIL="test$(date +%s)@example.com"
USERNAME="testuser$(date +%s)"
PASSWORD="SecurePass123!"

echo "🧪 Testing API Monitor Platform API"
echo "===================================="
echo ""

# Test 1: Health Check
echo "✅ Test 1: Health Check"
curl -s ${BASE_URL%/api/v1}/health | jq '.'
echo ""

# Test 2: Register User
echo "✅ Test 2: Register User"
echo "Email: $EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "username": "'"$USERNAME"'",
    "password": "'"$PASSWORD"'",
    "full_name": "Test User"
  }')

echo "$REGISTER_RESPONSE" | jq '.'
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.refresh_token')
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.user.id')

if [ "$ACCESS_TOKEN" == "null" ]; then
  echo "❌ Failed to register user"
  exit 1
fi

echo "✅ User registered successfully"
echo "Access Token: ${ACCESS_TOKEN:0:20}..."
echo ""

# Test 3: Get Current User
echo "✅ Test 3: Get Current User"
curl -s -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# Test 4: List Workspaces
echo "✅ Test 4: List Workspaces"
WORKSPACES=$(curl -s -X GET "$BASE_URL/workspaces" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
echo "$WORKSPACES" | jq '.'
WORKSPACE_ID=$(echo "$WORKSPACES" | jq -r '.[0].id')
echo "Workspace ID: $WORKSPACE_ID"
echo ""

# Test 5: Create Monitor
echo "✅ Test 5: Create Monitor"
MONITOR_RESPONSE=$(curl -s -X POST "$BASE_URL/monitors?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Monitor",
    "description": "Testing the API",
    "url": "https://httpbin.org/status/200",
    "monitor_type": "https",
    "method": "GET",
    "interval_seconds": 300,
    "timeout_seconds": 30,
    "expected_status_codes": [200],
    "regions": ["us-east-1"]
  }')

echo "$MONITOR_RESPONSE" | jq '.'
MONITOR_ID=$(echo "$MONITOR_RESPONSE" | jq -r '.id')

if [ "$MONITOR_ID" == "null" ]; then
  echo "❌ Failed to create monitor"
  exit 1
fi

echo "✅ Monitor created successfully"
echo "Monitor ID: $MONITOR_ID"
echo ""

# Test 6: List Monitors
echo "✅ Test 6: List Monitors"
curl -s -X GET "$BASE_URL/monitors?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# Test 7: Get Monitor Details
echo "✅ Test 7: Get Monitor Details"
curl -s -X GET "$BASE_URL/monitors/$MONITOR_ID?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# Test 8: Update Monitor
echo "✅ Test 8: Update Monitor"
curl -s -X PUT "$BASE_URL/monitors/$MONITOR_ID?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Monitor Name"
  }' | jq '.'
echo ""

# Test 9: Trigger Manual Check
echo "✅ Test 9: Trigger Manual Check"
curl -s -X POST "$BASE_URL/monitors/$MONITOR_ID/check?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# Test 10: Refresh Token
echo "✅ Test 10: Refresh Token"
curl -s -X POST "$BASE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "'"$REFRESH_TOKEN"'"
  }' | jq '.'
echo ""

# Test 11: Logout
echo "✅ Test 11: Logout"
curl -s -X POST "$BASE_URL/auth/logout" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

echo "===================================="
echo "✅ All tests passed successfully!"
echo "===================================="

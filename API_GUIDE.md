# Push Chat - API Usage Guide

## Overview

Push Chat là một dịch vụ gửi thông báo riêng tư qua Microsoft Teams Chat API. Hệ thống yêu cầu authentication và cho phép gửi tin nhắn trực tiếp tới người dùng cụ thể.

## Quick Start

### 1. Login (Get Session Cookie)

```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "PGBank@2026devops"
  }' \
  -c cookies.txt
```

**Response:**
```json
{
  "success": true,
  "message": "Welcome, admin!"
}
```

**Note:** Lệnh `-c cookies.txt` lưu session cookie để sử dụng cho các request tiếp theo.

---

### 2. Send Message to User

**Endpoint:** `POST /api/send`

```bash
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "truongtd3",
    "message": "Hello! This is a test message from Push Chat."
  }'
```

**Response:**
```json
{
  "success": true,
  "recipient": {
    "username": "truongtd3",
    "displayName": "Trương, Trần Đình (TDT)",
    "userPrincipalName": "truongtd3@pgbank.com.vn",
    "id": "77322afa-0c1b-41af-9fe4-761e4f5ff85f"
  },
  "message": "Hello! This is a test message from Push Chat.",
  "status": "Notification sent successfully via Teams Activity API"
}
```

---

### 3. Lookup User Details

**Endpoint:** `GET /api/user/<username>`

```bash
curl -X GET http://localhost:5000/api/user/truongtd3 \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

**Response:**
```json
{
  "id": "77322afa-0c1b-41af-9fe4-761e4f5ff85f",
  "displayName": "Trương, Trần Đình (TDT)",
  "userPrincipalName": "truongtd3@pgbank.com.vn",
  "mail": "truongtd3@pgbank.com.vn"
}
```

---

### 4. Get Configuration Status

**Endpoint:** `GET /api/config`

```bash
curl -X GET http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

**Response:**
```json
{
  "status": "Configured",
  "tenant_id": "c756d8b9-34af-408b-b1e4-9f084cbcc023",
  "client_id": "b155469d-49d3-47be-aefd-4da3c3765a72",
  "bot_id": "b155469d-49d3-47be-aefd-4da3c3765a72",
  "default_sender": "app-monitor@pgbank.com.vn"
}
```

---

### 5. Logout

**Endpoint:** `POST /api/logout`

```bash
curl -X POST http://localhost:5000/api/logout \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Complete Workflow Example

```bash
#!/bin/bash

# Step 1: Login
echo "=== STEP 1: LOGIN ==="
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "PGBank@2026devops"
  }' \
  -c cookies.txt
echo -e "\n"

# Step 2: Lookup user
echo "=== STEP 2: LOOKUP USER ==="
curl -X GET http://localhost:5000/api/user/truongtd3 \
  -H "Content-Type: application/json" \
  -b cookies.txt
echo -e "\n"

# Step 3: Send message
echo "=== STEP 3: SEND MESSAGE ==="
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "truongtd3",
    "message": "Test notification from Push Chat API"
  }'
echo -e "\n"

# Step 4: Get config
echo "=== STEP 4: GET CONFIG ==="
curl -X GET http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -b cookies.txt
echo -e "\n"

# Step 5: Logout
echo "=== STEP 5: LOGOUT ==="
curl -X POST http://localhost:5000/api/logout \
  -H "Content-Type: application/json" \
  -b cookies.txt
echo -e "\n"
```

---

## Advanced: Inline Curl Commands (Without Cookie File)

### Login + Send Message (Chain)

```bash
# Get session cookie và gửi message trong 1 lệnh
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "username": "truongtd3",
    "message": "Hello from curl!"
  }' \
  -H "Cookie: session=$(curl -s -X POST http://localhost:5000/api/login \
    -H 'Content-Type: application/json' \
    -d '{\"username\":\"admin\",\"password\":\"PGBank@2026devops\"}' \
    -c - | grep session | awk '{print $7}')"
```

---

## Error Handling

### 401 Unauthorized - Login Failed
```json
{
  "success": false,
  "error": "Invalid username or password"
}
```
**Solution:** Kiểm tra username/password chính xác

### 404 User Not Found
```json
{
  "error": "User 'invalid-user' not found in Microsoft Directory."
}
```
**Solution:** Sử dụng username chính xác (email, UPN, hoặc display name)

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Failed to get access token: ..."
}
```
**Solution:** Kiểm tra Azure credentials trong `.env` file

---

## Authentication

- **Username:** `admin`
- **Password:** `PGBank@2026devops`
- **Session Timeout:** 5 minutes (auto logout khi không hoạt động)

---

## Tips & Tricks

### 1. Save Credentials (Safe Method)

```bash
# Create a .env file for curl
cat > .curl-env << EOF
USERNAME=admin
PASSWORD=PGBank@2026devops
API_URL=http://localhost:5000
EOF

# Load and use
source .curl-env
curl -X POST $API_URL/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  -c cookies.txt
```

### 2. Pretty Print JSON Response

```bash
curl -X GET http://localhost:5000/api/config \
  -b cookies.txt | jq '.'
```

### 3. Check Response Status Code

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X GET http://localhost:5000/api/config \
  -b cookies.txt
```

### 4. Send HTML Message

```bash
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "truongtd3",
    "message": "<strong>Important:</strong> This is an <em>HTML</em> message"
  }'
```

### 5. Send with Emoji & Unicode

```bash
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "truongtd3",
    "message": "📞 Incoming call! 🎯 Click to answer 📱"
  }'
```

---

## Troubleshooting

### Session Cookie Not Working

```bash
# Check if cookie file exists and is valid
cat cookies.txt

# Try deleting and re-logging in
rm cookies.txt
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"PGBank@2026devops"}' \
  -c cookies.txt
```

### Network Timeout

```bash
# Add timeout parameter
curl --max-time 30 \
  -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"username":"truongtd3","message":"test"}'
```

### Verbose Output (Debugging)

```bash
# Show all request/response details
curl -v -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"username":"truongtd3","message":"test"}'
```

---

## Command Cheat Sheet

```bash
# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"PGBank@2026devops"}' \
  -c cookies.txt

# Send message
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"username":"USER","message":"MSG"}'

# Lookup user
curl -X GET http://localhost:5000/api/user/USERNAME \
  -H "Content-Type: application/json" \
  -b cookies.txt

# Get config
curl -X GET http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -b cookies.txt

# Logout
curl -X POST http://localhost:5000/api/logout \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

---

## API Base URL

- **Local Development:** `http://localhost:5000`
- **Production:** `https://push-chat.pgbank.com.vn`

---

**Last Updated:** 2026-07-10
**Version:** 1.0

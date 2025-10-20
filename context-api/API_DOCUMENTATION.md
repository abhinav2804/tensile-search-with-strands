# Context REST API Documentation

## Overview

The Context REST API is a Go-based service that provides user management functionality with DynamoDB as the backend storage. The API supports dynamic JSON fields and runs on port 4000.

## Base URL
```
http://82.112.235.26:4000/
```

## Authentication
Currently, no authentication is required for API access.

## Content Type
All requests and responses use `application/json` content type.

## Endpoints

### 1. Create User

**Endpoint:** `POST /users`

**Description:** Creates a new user with dynamic fields. The `UserId` field is required.

**Request Body:**
```json
{
  "UserId": "string (required)",
  "ofELK": "string (required - used as primary key)",
  "name": "string (optional)",
  "age": "number (optional)",
  "active": "boolean (optional)",
  // ... any additional dynamic fields
}
```

**Example Request:**
```bash
curl -X POST http://82.112.235.26:4000/users \
  -H "Content-Type: application/json" \
  -d '{
    "UserId": "u1",
    "name": "Alice",
    "age": 30,
    "active": true,
    "ofELK": "1"
  }'
```

**Response:**
- **Status Code:** 200 OK
- **Body:** Returns the created user object

```json
{
  "UserId": "u1",
  "name": "Alice",
  "age": 30,
  "active": true,
  "ofELK": "1"
}
```

**Error Responses:**
- **400 Bad Request:** When `UserId` is missing
- **500 Internal Server Error:** Database operation failed

---

### 2. Get User

**Endpoint:** `GET /users/{id}`

**Description:** Retrieves a user by their ID (uses `ofELK` field as the lookup key).

**Path Parameters:**
- `id` (string, required): The user identifier (corresponds to `ofELK` field)

**Example Request:**
```bash
curl -X GET http://82.112.235.26:4000/users/1
```

**Response:**
- **Status Code:** 200 OK
- **Body:** Returns the user object

```json
{
  "UserId": "u1",
  "name": "Alice",
  "age": 30,
  "active": true,
  "ofELK": "1"
}
```

**Error Responses:**
- **404 Not Found:** User not found or doesn't exist
- **500 Internal Server Error:** Database operation failed

---

### 3. Update User

**Endpoint:** `PUT http://82.112.235.26:4000/users/{id}`

**Description:** Updates an existing user by merging the provided fields. Only the fields included in the request body will be updated.

**Path Parameters:**
- `id` (string, required): The user identifier (corresponds to `UserId` field)

**Request Body:**
```json
{
  "name": "string (optional)",
  "age": "number (optional)",
  "active": "boolean (optional)",
  // ... any other fields to update
}
```

**Example Request:**
```bash
curl -X PUT http://localhost:4000/users/u1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Updated",
    "age": 31
  }'
```

**Response:**
- **Status Code:** 200 OK
- **Body:** Success message

```json
{
  "message": "User updated successfully"
}
```

**Error Responses:**
- **400 Bad Request:** No fields provided to update
- **500 Internal Server Error:** Database operation failed

---

## Data Types

The API supports the following data types for dynamic fields:

- **String:** Text values
- **Number:** Numeric values (stored as strings in DynamoDB)
- **Boolean:** true/false values
- **Dynamic:** Any other type will be converted to string format

## Database Schema

**Table Name:** `users`

**Primary Key:** `ofELK` (String)

**Note:** The API uses `ofELK` as the partition key for DynamoDB operations, but the `UserId` field is also required for user creation.

## Error Handling

All error responses follow this format:

```json
{
  "error": "Error message description"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (missing required fields, invalid JSON)
- `404` - Not Found (user doesn't exist)
- `500` - Internal Server Error (database or server issues)

## Configuration

### Environment Variables

The service uses AWS SDK default configuration for DynamoDB connection. Ensure the following are configured:

- AWS credentials (via AWS CLI, environment variables, or IAM roles)
- AWS region
- DynamoDB table `users` must exist

### Dependencies

- Go modules (see `go.mod`)
- AWS SDK for Go v2
- Gorilla Mux router
- DynamoDB table with appropriate permissions

## Running the Service

1. Ensure AWS credentials are configured
2. Create the DynamoDB table named `users` with `ofELK` as the partition key
3. Run the service:
   ```bash
   go run main.go dynamo.go
   ```
4. The service will start on port 4000

## Example Usage Workflow

1. **Create a user:**
   ```bash
   curl -X POST http://82.112.235.26:4000/users \
     -H "Content-Type: application/json" \
     -d '{"UserId":"123","ofELK":"123","name":"John Doe","email":"john@example.com"}'
   ```

2. **Retrieve the user:**
   ```bash
   curl -X GET http://82.112.235.26:4000/users/123
   ```

3. **Update the user:**
   ```bash
   curl -X PUT http://82.112.235.26:4000/users/user123 \
     -H "Content-Type: application/json" \
     -d '{"email":"john.doe@example.com","active":true}'
   ```

## Notes

- The API supports dynamic fields, allowing you to store any JSON-compatible data
- All numeric values are stored as strings in DynamoDB but can be sent as numbers in JSON
- The service uses the Gorilla Mux router for HTTP routing
- Error logging is printed to console for debugging
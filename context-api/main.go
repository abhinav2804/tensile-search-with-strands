/*
Context API - DynamoDB User Registry for Tensile Search
========================================================

This Go service provides a RESTful API for managing user metadata in AWS DynamoDB.
It stores crucial information about deployed infrastructure for each user:

Purpose:
- Track Elasticsearch instance details (host, port, status)
- Store MCP server endpoints for tool integration
- Manage indexed indices per user
- Persist user authentication and session data

AWS Architecture Role:
- Acts as the central registry for all deployed infrastructure
- Integrates with AWS DynamoDB for serverless, scalable storage
- Enables the frontend and agents to discover user-specific endpoints
- Provides CRUD operations for dynamic field management

Data Flow:
1. User registers → Create entry in DynamoDB
2. Infrastructure deployed → Update with ES/MCP ports
3. Indexing complete → Add indexed index names
4. Search query → Retrieve user's ES endpoint

Example User Record:
{
  "UserId": "user123",
  "email": "user@example.com",
  "elasticsearch_port": 9200,
  "mcp_port": 10200,
  "indexed_indices": ["products_20251022", "customers_20251023"],
  "created_at": "2025-10-22T10:30:00Z"
}
*/

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/gorilla/mux"
)

var (
	db    *dynamodb.Client        // AWS DynamoDB client (auto-configured from env/IAM)
	table = "users"               // DynamoDB table name (customize for your deployment)
	ctx   = context.TODO()        // Global context for DynamoDB operations
)

// Item: Dynamic map for flexible JSON structure
// Allows storing arbitrary user metadata without predefined schema
// This supports the zero-code approach - users can have different fields
type Item map[string]interface{}

// ✅ Create User (dynamic fields)
// 
// Creates a new user record in DynamoDB with flexible field structure.
// This is called when a user first registers on the portal.
//
// Required Field: UserId (partition key)
// Optional Fields: Any JSON-serializable data (email, metadata, etc.)
//
// Request Example:
//   POST /users
//   {
//     "UserId": "user123",
//     "email": "user@example.com",
//     "elasticsearch_port": 9200,
//     "mcp_port": 10200
//   }
//
// Integration: Called by frontend after Descope authentication succeeds
func createUser(w http.ResponseWriter, r *http.Request) {
	var item Item
	_ = json.NewDecoder(r.Body).Decode(&item)

	// Require UserId (partition key for DynamoDB queries)
	if _, ok := item["UserId"]; !ok {
		http.Error(w, "UserId is required", http.StatusBadRequest)
		return
	}

	// Convert map[string]interface{} -> map[string]AttributeValue
	// This transforms Go types to DynamoDB's strongly-typed attribute system
	av, err := toAttributeValueMap(item)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Write to DynamoDB
	// PutItem creates or replaces the entire item (not a merge)
	_, err = db.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(table),
		Item:      av,
	})
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(item)
}

// ✅ Get User by UserId
func getUser(w http.ResponseWriter, r *http.Request) {
	params := mux.Vars(r)
	userId := params["id"]

	fmt.Println("Fetching user with ID:", userId)
	fmt.Println("Table name:", table)
	resp, err := db.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(table),
		Key: map[string]types.AttributeValue{
			"ofELK": &types.AttributeValueMemberS{Value: userId},
		},
	})

	fmt.Println("Get User Response:", resp)

	if err != nil || resp.Item == nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	// Convert back to JSON
	item := map[string]interface{}{}
	for k, v := range resp.Item {
		switch t := v.(type) {
		case *types.AttributeValueMemberS:
			item[k] = t.Value
		case *types.AttributeValueMemberN:
			item[k] = t.Value
		case *types.AttributeValueMemberBOOL:
			item[k] = t.Value
		}
	}
	json.NewEncoder(w).Encode(item)
}

// ✅ Update User (merge fields dynamically)
func updateUser(w http.ResponseWriter, r *http.Request) {
	params := mux.Vars(r)
	userId := params["id"]

	var updates Item
	_ = json.NewDecoder(r.Body).Decode(&updates)

	if len(updates) == 0 {
		http.Error(w, "No fields to update", http.StatusBadRequest)
		return
	}

	// Build UpdateExpression dynamically
	updateExpr := "SET "
	exprAttrValues := map[string]types.AttributeValue{}
	exprAttrNames := map[string]string{}
	i := 0
	for k, v := range updates {
		i++
		placeholder := fmt.Sprintf("#f%d", i)
		valueHolder := fmt.Sprintf(":v%d", i)
		updateExpr += fmt.Sprintf("%s = %s, ", placeholder, valueHolder)
		exprAttrNames[placeholder] = k
		exprAttrValues[valueHolder] = toAttributeValue(v)
	}
	updateExpr = updateExpr[:len(updateExpr)-2] // trim last comma

	_, err := db.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName: aws.String(table),
		Key: map[string]types.AttributeValue{
			"UserId": &types.AttributeValueMemberS{Value: userId},
		},
		UpdateExpression:          aws.String(updateExpr),
		ExpressionAttributeNames:  exprAttrNames,
		ExpressionAttributeValues: exprAttrValues,
		ReturnValues:              types.ReturnValueUpdatedNew,
	})
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(map[string]string{"message": "User updated successfully"})
}

// --- Helpers ---

// Convert generic map to DynamoDB AttributeValue
func toAttributeValueMap(item map[string]interface{}) (map[string]types.AttributeValue, error) {
	av := make(map[string]types.AttributeValue)
	for k, v := range item {
		av[k] = toAttributeValue(v)
	}
	return av, nil
}

func toAttributeValue(v interface{}) types.AttributeValue {
	switch val := v.(type) {
	case string:
		return &types.AttributeValueMemberS{Value: val}
	case float64: // JSON numbers are float64
		return &types.AttributeValueMemberN{Value: fmt.Sprintf("%v", val)}
	case bool:
		return &types.AttributeValueMemberBOOL{Value: val}
	default:
		// fallback: store as string
		return &types.AttributeValueMemberS{Value: fmt.Sprintf("%v", val)}
	}
}

func main() {
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatalf("unable to load SDK config, %v", err)
	}
	db = dynamodb.NewFromConfig(cfg)

	r := mux.NewRouter()
	r.HandleFunc("/users", createUser).Methods("POST")
	r.HandleFunc("/users/{id}", getUser).Methods("GET")
	r.HandleFunc("/users/{id}", updateUser).Methods("PUT")

	fmt.Println("🚀 Server running on :4000")
	log.Fatal(http.ListenAndServe(":4000", r))
}

package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/gorilla/mux"
)

// =====================================================================================
// DynamoDB helpers and HTTP wrappers
//
// This file exposes:
//   1) A small, documented programmatic API for DynamoDB (GET, INSERT, UPDATE).
//   2) Thin HTTP handlers that wrap the programmatic API, so you can mount routes easily.
//
// Notes:
// - This file relies on the package-level variables declared in main.go:
//     var (
//         db    *dynamodb.Client
//         table string
//         ctx   = context.TODO()
//     )
// - Ensure `db` is initialized before using these helpers (see InitDynamo* functions below),
//   or continue initializing it in main.go as you already do.
// - The Item type and helper conversions to AttributeValue are defined in main.go and are
//   reused here.
// =====================================================================================

// Constants used by this module
const (
	// DefaultUsersTable is the default DynamoDB table name for user items.
	DefaultUsersTable = "users"

	// PKUserID is the partition key attribute for the Users table.
	// Change this if your schema uses a different key name.
	PKUserID = "ofELK"

	// PathParamID is the URL path parameter used by HTTP handlers, e.g. /users/{id}
	PathParamID = "id"
)

// InitDynamo initializes the shared DynamoDB client used by this package using a provided AWS config.
// Call this at app startup if you want a single place to initialize the client.
func InitDynamo(cfg aws.Config) {
	db = dynamodb.NewFromConfig(cfg)
}

// InitDynamoDefault loads AWS configuration using the default credential chain and initializes the client.
// This is a convenience if you don't want to manage aws.Config yourself.
func InitDynamoDefault(ctx context.Context) error {
	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		return fmt.Errorf("load default AWS config: %w", err)
	}
	InitDynamo(cfg)
	return nil
}

// =====================================================================================
// Programmatic API (reusable from other code)
// =====================================================================================

// GetItemByPK fetches a single item from DynamoDB by primary key.
// - tableName: DynamoDB table name
// - pkName:    Primary key attribute name (partition key)
// - pkValue:   Primary key value (string)
// Returns the item as Item (map[string]interface{}), or an error if not found or on failure.
func GetItemByPK(ctx context.Context, tableName, pkName, pkValue string) (Item, error) {
	if db == nil {
		return nil, errors.New("dynamodb client is not initialized")
	}

	resp, err := db.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(tableName),
		Key: map[string]types.AttributeValue{
			pkName: &types.AttributeValueMemberS{Value: pkValue},
		},
	})
	if err != nil {
		return nil, err
	}
	if resp.Item == nil || len(resp.Item) == 0 {
		return nil, fmt.Errorf("item not found: %s=%s", pkName, pkValue)
	}
	return fromAttributeValueMap(resp.Item), nil
}

// PutItemGeneric inserts (or replaces) an item into DynamoDB.
// - tableName: DynamoDB table name
// - item:      Arbitrary JSON-compatible map to persist
// Returns the same item on success.
func PutItemGeneric(ctx context.Context, tableName string, item Item) (Item, error) {
	if db == nil {
		return nil, errors.New("dynamodb client is not initialized")
	}
	av, err := toAttributeValueMap(item)
	if err != nil {
		return nil, err
	}
	_, err = db.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(tableName),
		Item:      av,
	})
	if err != nil {
		return nil, err
	}
	return item, nil
}

// UpdateItemByPK updates (merges) fields on an item addressed by primary key.
// Returns the newly updated attributes as Item.
func UpdateItemByPK(ctx context.Context, tableName, pkName, pkValue string, updates Item) (Item, error) {
	if db == nil {
		return nil, errors.New("dynamodb client is not initialized")
	}
	if len(updates) == 0 {
		return nil, errors.New("no fields to update")
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

	out, err := db.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName: aws.String(tableName),
		Key: map[string]types.AttributeValue{
			pkName: &types.AttributeValueMemberS{Value: pkValue},
		},
		UpdateExpression:          aws.String(updateExpr),
		ExpressionAttributeNames:  exprAttrNames,
		ExpressionAttributeValues: exprAttrValues,
		ReturnValues:              types.ReturnValueUpdatedNew,
	})
	if err != nil {
		return nil, err
	}
	return fromAttributeValueMap(out.Attributes), nil
}

// Convenience helpers for the common Users table pattern

// GetUser fetches a user by UserId from the default table.
func GetUser(ctx context.Context, userID string) (Item, error) {
	return GetItemByPK(ctx, table, PKUserID, userID)
}

// PutUser inserts a user item. Requires the PK field (UserId) to be present.
func PutUser(ctx context.Context, user Item) (Item, error) {
	if _, ok := user[PKUserID]; !ok {
		return nil, fmt.Errorf("%s is required", PKUserID)
	}
	return PutItemGeneric(ctx, table, user)
}

// UpdateUserFields merges fields into an existing user.
func UpdateUserFields(ctx context.Context, userID string, updates Item) (Item, error) {
	return UpdateItemByPK(ctx, table, PKUserID, userID, updates)
}

// =====================================================================================
// HTTP wrappers (thin handlers that call the programmatic API)
// =====================================================================================

// CreateUserHandler handles POST /users
// Body: JSON object representing the user. Must include UserId.
func CreateUserHandler(w http.ResponseWriter, r *http.Request) {
	var user Item
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	created, err := PutUser(r.Context(), user)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(created)
}

// GetUserHandler handles GET /users/{id}
func GetUserHandler(w http.ResponseWriter, r *http.Request) {
	id := mux.Vars(r)[PathParamID]
	item, err := GetUser(r.Context(), id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(item)
}

// UpdateUserHandler handles PUT /users/{id}
// Body: JSON object with fields to update.
func UpdateUserHandler(w http.ResponseWriter, r *http.Request) {
	id := mux.Vars(r)[PathParamID]
	var updates Item
	if err := json.NewDecoder(r.Body).Decode(&updates); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	updated, err := UpdateUserFields(r.Context(), id, updates)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(updated)
}

// RegisterUserRoutes wires the HTTP handlers under the given base path.
// Example: RegisterUserRoutes(r, "/users")
func RegisterUserRoutes(r *mux.Router, base string) {
	// POST {base}
	r.HandleFunc(base, CreateUserHandler).Methods("POST")
	// GET {base}/{id}
	r.HandleFunc(fmt.Sprintf("%s/{%s}", base, PathParamID), GetUserHandler).Methods("GET")
	// PUT {base}/{id}
	r.HandleFunc(fmt.Sprintf("%s/{%s}", base, PathParamID), UpdateUserHandler).Methods("PUT")
}

// =====================================================================================
// Internal helpers
// =====================================================================================

// fromAttributeValueMap converts DynamoDB attribute map to Item.
// Only a subset of DynamoDB types are handled here for brevity.
func fromAttributeValueMap(m map[string]types.AttributeValue) Item {
	if m == nil {
		return nil
	}
	item := Item{}
	for k, v := range m {
		switch t := v.(type) {
		case *types.AttributeValueMemberS:
			item[k] = t.Value
		case *types.AttributeValueMemberN:
			item[k] = t.Value
		case *types.AttributeValueMemberBOOL:
			item[k] = t.Value
			// You can extend this with lists, maps, etc., as needed.
		}
	}
	return item
}

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
	db    *dynamodb.Client
	table = "users" // change to your DynamoDB table name
	ctx   = context.TODO()
)

// Dynamic map for any JSON
type Item map[string]interface{}

// ✅ Create User (dynamic fields)
func createUser(w http.ResponseWriter, r *http.Request) {
	var item Item
	_ = json.NewDecoder(r.Body).Decode(&item)

	// Require UserId
	if _, ok := item["UserId"]; !ok {
		http.Error(w, "UserId is required", http.StatusBadRequest)
		return
	}

	// Convert map[string]interface{} -> map[string]AttributeValue
	av, err := toAttributeValueMap(item)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

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

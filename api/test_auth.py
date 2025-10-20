#!/usr/bin/env python3
"""
Test script to demonstrate API authentication functionality
"""
import requests
import base64
import json

# API base URL
BASE_URL = "http://localhost:5000"

def test_authentication():
    """Test different authentication methods"""
    
    print("🔐 Testing File Storage API Authentication\n")
    
    # Test credentials
    credentials = [
        ("admin", "admin123"),
        ("user1", "user1pass"),
        ("user2", "user2pass")
    ]
    
    # Test 1: Health check (no auth required)
    print("1. Testing Health Check (no auth required)")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 2: Basic Authentication
    print("2. Testing Basic Authentication")
    for username, password in credentials:
        try:
            # Create Basic Auth header
            credentials_b64 = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers = {"Authorization": f"Basic {credentials_b64}"}
            
            # Test with upload endpoint
            files = {"file": ("test.txt", "Hello World", "text/plain")}
            data = {"userid": "testuser", "filetype": "data"}
            
            response = requests.post(f"{BASE_URL}/upload", headers=headers, files=files, data=data)
            print(f"   User: {username} - Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
            else:
                print(f"   Error: {response.json()}")
        except Exception as e:
            print(f"   Error for {username}: {e}")
    print()
    
    # Test 3: API Key Authentication
    print("3. Testing API Key Authentication")
    api_keys = ["admin123", "user1pass", "user2pass", "invalid_key"]
    
    for api_key in api_keys:
        try:
            headers = {"X-API-Key": api_key}
            files = {"file": ("test.txt", "Hello World", "text/plain")}
            data = {"userid": "testuser", "filetype": "query"}
            
            response = requests.post(f"{BASE_URL}/upload", headers=headers, files=files, data=data)
            print(f"   API Key: {api_key[:8]}... - Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error: {response.json()}")
        except Exception as e:
            print(f"   Error for {api_key}: {e}")
    print()
    
    # Test 4: Bearer Token Authentication
    print("4. Testing Bearer Token Authentication")
    tokens = ["admin123", "user1pass", "user2pass", "invalid_token"]
    
    for token in tokens:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            files = {"file": ("test.txt", "Hello World", "text/plain")}
            data = {"userid": "testuser", "filetype": "data"}
            
            response = requests.post(f"{BASE_URL}/upload", headers=headers, files=files, data=data)
            print(f"   Token: {token[:8]}... - Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error: {response.json()}")
        except Exception as e:
            print(f"   Error for {token}: {e}")
    print()
    
    # Test 5: No Authentication (should fail)
    print("5. Testing No Authentication (should fail)")
    try:
        files = {"file": ("test.txt", "Hello World", "text/plain")}
        data = {"userid": "testuser", "filetype": "data"}
        
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    print("✅ Authentication tests completed!")

if __name__ == "__main__":
    test_authentication()

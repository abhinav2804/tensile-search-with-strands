#!/usr/bin/env python3

import requests
import json
import time

def test_automated_deployment():
    """Test the fully automated deployment with API key generation"""
    
    print("🚀 Testing Automated Deployment with API Key Generation")
    print("=" * 60)
    
    # Deploy with auto ports
    print("1. Starting deployment...")
    response = requests.post('http://localhost:8000/deploy', 
                           json={}, 
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code != 201:
        print(f"❌ Deployment failed: {response.json()}")
        return None
    
    deployment = response.json()
    instance_id = deployment['instance_id']
    
    print(f"✅ Deployment started with instance ID: {instance_id}")
    print(f"📍 Endpoints:")
    for service, url in deployment['endpoints'].items():
        print(f"   • {service}: {url}")
    
    # Wait for deployment to complete
    print(f"\n2. Waiting for deployment to complete (this may take 2-3 minutes)...")
    wait_response = requests.get(f'http://localhost:8000/deployments/{instance_id}/wait?timeout=300')
    
    if wait_response.status_code == 200:
        result = wait_response.json()
        print(f"✅ Deployment completed successfully!")
        print(f"🔑 Auto-generated API Key: {result.get('elasticsearch_api_key', 'Not found')}")
        
        # Test all endpoints
        print(f"\n3. Testing all services...")
        endpoints = deployment['endpoints']
        
        # Test Elasticsearch
        try:
            es_response = requests.get(f"{endpoints['elasticsearch']}/_cluster/health", 
                                     auth=('elastic', 'changeme'), timeout=5)
            if es_response.status_code == 200:
                health = es_response.json()
                print(f"✅ Elasticsearch: {health['status'].upper()} ({health['number_of_nodes']} nodes)")
            else:
                print("❌ Elasticsearch: Unhealthy")
        except Exception as e:
            print(f"❌ Elasticsearch: Connection failed - {e}")
        
        # Test MCP Server
        try:
            mcp_response = requests.get(f"{endpoints['mcp_server']}/", timeout=5)
            if mcp_response.status_code == 200 and 'MCP server' in mcp_response.text:
                print("✅ MCP Server: Connected and responding")
            else:
                print("❌ MCP Server: Unhealthy")
        except Exception as e:
            print(f"❌ MCP Server: Connection failed - {e}")
        
        # Test AI Agent
        try:
            ai_response = requests.get(f"{endpoints['ai_agent']}/health", timeout=5)
            if ai_response.status_code == 200:
                health = ai_response.json()
                print(f"✅ AI Agent: {health['status'].upper()} (MCP enabled: {health['mcp_enabled']})")
            else:
                print("❌ AI Agent: Unhealthy")
        except Exception as e:
            print(f"❌ AI Agent: Connection failed - {e}")
        
        print(f"\n🎉 Deployment {instance_id} is fully operational!")
        print(f"🔗 You can now use the services at the endpoints above.")
        
        return instance_id
    else:
        result = wait_response.json()
        print(f"❌ Deployment failed or timed out: {result}")
        return None

if __name__ == '__main__':
    print("Starting automated deployment test...")
    print("Make sure the infrastructure deployment API is running: python infra_deployment_api.py")
    print()
    
    try:
        # Check if wrapper API is running
        response = requests.get('http://localhost:8000/health', timeout=2)
        print("✅ Wrapper API is running")
        print()
        
        instance_id = test_automated_deployment()
        
        if instance_id:
            print(f"\n📋 To stop this deployment later, run:")
            print(f"   curl -X POST http://localhost:8000/deployments/{instance_id}/stop")
        
    except requests.exceptions.ConnectionError:
        print("❌ Wrapper API is not running!")
        print("   Please start it first: python infra_deployment_api.py")
    except Exception as e:
        print(f"❌ Error: {e}")
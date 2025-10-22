#!/usr/bin/env python3
"""
Setup script for MCP Elasticsearch Integration
This script helps set up the MCP server integration with your existing pipeline
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Check if required dependencies are installed"""
    required_packages = [
        'docker',
        'paramiko',
        'elasticsearch',
        'pandas',
        'pyyaml',
        'aiohttp',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is missing")
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_docker():
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Docker is installed: {result.stdout.strip()}")
        else:
            print("✗ Docker is not properly installed")
            return False
            
        # Check if Docker daemon is running
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Docker daemon is running")
        else:
            print("✗ Docker daemon is not running")
            return False
            
    except FileNotFoundError:
        print("✗ Docker is not installed")
        return False
    
    return True

def create_directory_structure():
    """Create necessary directories"""
    directories = [
        'mcp_configs',
        'schemas',
        'uploads',
        'temp'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_config_template():
    """Create a config template if it doesn't exist"""
    config_content = '''
# Configuration for Enhanced Data Pipeline with MCP Integration
CONFIG = {
    'aws_access_key': 'your-aws-access-key',
    'aws_secret_key': 'your-aws-secret-key',
    'aws_region': 'us-east-1',
    'es_host': 'http://localhost:9200',
    'es_auth': ('username', 'password'),  # or None for no auth
}

# MCP Configuration
MCP_CONFIG = {
    'base_port': 9200,
    'mcp_port_offset': 1000,  # MCP servers will run on ES_PORT + 1000
    'docker_network': 'elasticsearch-network',
    'health_check_interval': 30,  # seconds
    'connection_timeout': 60  # seconds
}

# Remote Server Configuration
REMOTE_CONFIG = {
    'vm_host': '54.227.251.28',
    'vm_user': 'khemchand',
    'vm_password': 'wq0XYdUWKa1EN7LI7',
    'ssh_timeout': 30
}
'''
    
    if not os.path.exists('config.py'):
        with open('config.py', 'w') as f:
            f.write(config_content)
        print("✓ Created config.py template")
        print("  Please edit config.py with your actual credentials")
    else:
        print("✓ config.py already exists")

def create_requirements_file():
    """Create requirements.txt for the project"""
    requirements_content = '''flask>=2.3.0
flask-cors>=4.0.0
elasticsearch>=8.0.0
pandas>=1.5.0
paramiko>=3.0.0
docker>=6.0.0
pyyaml>=6.0.0
aiohttp>=3.8.0
asyncio
werkzeug>=2.3.0
requests>=2.28.0
descope>=1.0.0
'''
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements_content)
    print("✓ Created requirements.txt")

def create_docker_network():
    """Create Docker network for Elasticsearch containers"""
    try:
        result = subprocess.run([
            'docker', 'network', 'create', 'elasticsearch-network'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Created Docker network: elasticsearch-network")
        else:
            if "already exists" in result.stderr:
                print("✓ Docker network elasticsearch-network already exists")
            else:
                print(f"✗ Failed to create Docker network: {result.stderr}")
                return False
    except Exception as e:
        print(f"✗ Error creating Docker network: {e}")
        return False
    
    return True

def test_mcp_integration():
    """Test if MCP integration modules can be imported"""
    try:
        # Test if we can import the modules
        sys.path.append('.')
        
        # Try importing MCP modules
        from mcp_elasticsearch_server import MCPElasticsearchServer
        from mcp_integration import MCPIntegrationManager
        
        print("✓ MCP integration modules can be imported successfully")
        
        # Test basic initialization
        mcp_server = MCPElasticsearchServer()
        integration_manager = MCPIntegrationManager()
        
        print("✓ MCP components can be initialized")
        return True
        
    except ImportError as e:
        print(f"✗ Cannot import MCP modules: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing MCP integration: {e}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    sample_data = [
        {
            "name": "iPhone 15 Pro Max",
            "category": "Electronics",
            "price": 1199.99,
            "brand": "Apple",
            "features": ["5G", "Pro Camera", "Titanium Design"]
        },
        {
            "name": "Samsung Galaxy S24 Ultra", 
            "category": "Electronics",
            "price": 1299.99,
            "brand": "Samsung",
            "features": ["S Pen", "200MP Camera", "AI Features"]
        },
        {
            "name": "MacBook Pro 16-inch",
            "category": "Computers",
            "price": 2499.99,
            "brand": "Apple", 
            "features": ["M3 Pro Chip", "Liquid Retina XDR", "18-hour Battery"]
        }
    ]
    
    os.makedirs('sample_data', exist_ok=True)
    
    with open('sample_data/products.json', 'w') as f:
        import json
        json.dump(sample_data, f, indent=2)
    
    print("✓ Created sample data: sample_data/products.json")

def show_next_steps():
    """Show next steps to the user"""
    print("\n" + "="*60)
    print("MCP INTEGRATION SETUP COMPLETE!")
    print("="*60)
    
    print("\nNext Steps:")
    print("1. Edit config.py with your actual Elasticsearch credentials")
    print("2. Make sure Docker is running")
    print("3. Start your application:")
    print("   python app.py")
    print("\n4. Upload the sample data to test MCP integration:")
    print("   - Go to http://localhost:7000")
    print("   - Upload sample_data/products.json")
    print("   - Choose 'Remote Deployment' to test MCP integration")
    
    print("\n5. Your browser should automatically open to:")
    print("   - Elasticsearch instance URL")
    print("   - MCP server capabilities endpoint")
    
    print("\nMCP Endpoints:")
    print("  GET  /mcp/connections - View all MCP connections")
    print("  POST /mcp/test/<instance> - Test MCP connection") 
    print("  GET  /mcp/status - Overall MCP status")
    
    print("\nTroubleshooting:")
    print("  - Check Docker daemon is running: docker info")
    print("  - Check network exists: docker network ls | grep elasticsearch")
    print("  - Check MCP configs directory: ls -la mcp_configs/")
    print("  - View logs in the application terminal")

def main():
    """Main setup function"""
    print("MCP Elasticsearch Integration Setup")
    print("=" * 40)
    
    # Check requirements
    print("\n1. Checking Python requirements...")
    if not check_requirements():
        print("Please install missing packages before continuing")
        return False
    
    print("\n2. Checking Docker...")
    if not check_docker():
        print("Please install and start Docker before continuing")
        return False
    
    print("\n3. Creating directory structure...")
    create_directory_structure()
    
    print("\n4. Creating configuration files...")
    create_config_template()
    create_requirements_file()
    
    print("\n5. Setting up Docker network...")
    if not create_docker_network():
        print("Warning: Docker network creation failed, but continuing...")
    
    print("\n6. Testing MCP integration...")
    if not test_mcp_integration():
        print("Warning: MCP integration test failed")
        print("Make sure all Python files are in the same directory")
    
    print("\n7. Creating sample data...")
    create_sample_data()
    
    show_next_steps()
    return True

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
    except Exception as e:
        print(f"\nSetup failed with error: {e}")
        sys.exit(1)

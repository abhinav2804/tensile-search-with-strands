
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from elasticsearch import Elasticsearch
from aiohttp import web
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPElasticsearchHandler:
    def __init__(self):
        self.es_url = os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.index_name = os.environ.get('ELASTICSEARCH_INDEX', 'default')
        self.server_name = os.environ.get('MCP_SERVER_NAME', 'elasticsearch-mcp')
        
        # Initialize Elasticsearch client
        self.es = Elasticsearch([self.es_url], verify_certs=False, request_timeout=30)
        
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            if self.es.ping():
                return web.json_response({
                    'status': 'healthy',
                    'elasticsearch_url': self.es_url,
                    'index': self.index_name,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return web.json_response({
                    'status': 'unhealthy',
                    'error': 'Cannot connect to Elasticsearch'
                }, status=503)
        except Exception as e:
            return web.json_response({
                'status': 'unhealthy',
                'error': str(e)
            }, status=503)
    
    async def search_documents(self, request):
        """Search documents in Elasticsearch"""
        try:
            data = await request.json()
            query = data.get('query', '*')
            size = data.get('size', 10)
            
            search_body = {
                'query': {
                    'query_string': {
                        'query': query
                    }
                },
                'size': min(size, 100)
            }
            
            result = self.es.search(index=self.index_name, body=search_body)
            
            return web.json_response({
                'total_hits': result['hits']['total']['value'],
                'documents': [hit['_source'] for hit in result['hits']['hits']],
                'took': result['took']
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_index_info(self, request):
        """Get index information"""
        try:
            # Get index stats
            stats = self.es.indices.stats(index=self.index_name)
            mapping = self.es.indices.get_mapping(index=self.index_name)
            
            return web.json_response({
                'index': self.index_name,
                'document_count': stats['indices'][self.index_name]['total']['docs']['count'],
                'store_size': stats['indices'][self.index_name]['total']['store']['size_in_bytes'],
                'mapping': mapping[self.index_name]['mappings'],
                'server_name': self.server_name
            })
            
        except Exception as e:
            logger.error(f"Index info error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def mcp_capabilities(self, request):
        """MCP protocol capabilities endpoint"""
        return web.json_response({
            'capabilities': {
                'search': True,
                'index_info': True,
                'real_time': False
            },
            'server_info': {
                'name': self.server_name,
                'version': '1.0.0',
                'elasticsearch_url': self.es_url,
                'index': self.index_name
            }
        })

async def create_app():
    handler = MCPElasticsearchHandler()
    app = web.Application()
    
    # Add routes
    app.router.add_get('/health', handler.health_check)
    app.router.add_post('/search', handler.search_documents)
    app.router.add_get('/index-info', handler.get_index_info)
    app.router.add_get('/capabilities', handler.mcp_capabilities)
    
    return app

if __name__ == '__main__':
    app = asyncio.run(create_app())
    web.run_app(app, host='0.0.0.0', port=8080)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging
from contextlib import asynccontextmanager

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from elastic_mapping_tool import get_elastic_index_mapping
from elasticsearch_agent_prompt import ELASTICSEARCH_AGENT_SYSTEM_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for agent and MCP client
agent = None
mcp_client = None

class QueryRequest(BaseModel):
    query: str
    temperature: Optional[float] = 0.3

class QueryResponse(BaseModel):
    response: str
    status: str = "success"
    error: Optional[str] = None

def create_streamable_http_transport():
    """Create HTTP transport for MCP client"""
    headers = {
        "Authorization": f"ApiKey QmhMczhKa0JoSVNaRlVzNkp1U1E6RlA4X2FENFdGR2hubU5wRHZ1QjJVUQ==",
        "Content-Type": "application/json"
    }
    return streamablehttp_client("http://localhost:8080/mcp", headers=headers)

async def initialize_agent():
    """Initialize the AI agent with MCP tools and Bedrock model"""
    global agent, mcp_client
    
    try:
        # Create BedrockModel
        bedrock_model = BedrockModel(
            model_id="arn:aws:bedrock:us-east-1:301697000154:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
            region_name="us-east-1",
            temperature=0.3,
        )
        
        # Create MCP client
        mcp_client = MCPClient(create_streamable_http_transport)
        
        # Enter the MCP client context and keep it active
        mcp_client.__enter__()
        
        # Get MCP tools
        mcp_tools = mcp_client.list_tools_sync()
        logger.info(f"Found {len(mcp_tools)} MCP tools")
        
        # Debug: Check what attributes the MCP tool has
        if mcp_tools:
            logger.info(f"MCP tool attributes: {dir(mcp_tools[0])}")
            logger.info(f"First tool: {mcp_tools[0]}")
        
        # Filter out problematic tools - check different possible attribute names
        problematic_tools = ['get_mappings', 'esql']
        filtered_mcp_tools = []
        
        for tool in mcp_tools:
            # Try different attribute names that might contain the tool name
            tool_name = None
            if hasattr(tool, 'name'):
                tool_name = tool.name
            elif hasattr(tool, '_name'):
                tool_name = tool._name
            elif hasattr(tool, 'tool_name'):
                tool_name = tool.tool_name
            elif hasattr(tool, '__name__'):
                tool_name = tool.__name__
            
            logger.info(f"Tool name found: {tool_name}")
            
            if tool_name and tool_name not in problematic_tools:
                filtered_mcp_tools.append(tool)
            elif tool_name is None:
                # If we can't find the name, include it for now
                filtered_mcp_tools.append(tool)
        
        # Add your custom elastic tools to replace broken MCP functionality
        custom_elastic_tools = [get_elastic_index_mapping]
        all_tools = filtered_mcp_tools + custom_elastic_tools
        
        logger.info(f"Original MCP tools: {len(mcp_tools)}")
        logger.info(f"Filtered out {len(mcp_tools) - len(filtered_mcp_tools)} problematic tools: {problematic_tools}")
        logger.info(f"Available tools: {len(filtered_mcp_tools)} working MCP tools + {len(custom_elastic_tools)} custom elastic tools = {len(all_tools)} total")
        
        # Create agent with filtered MCP tools and custom elastic tools using the system prompt
        agent = Agent(
            model=bedrock_model,
            tools=all_tools,
            system_prompt=ELASTICSEARCH_AGENT_SYSTEM_PROMPT
        )
        
        logger.info("Agent initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global mcp_client
    
    # Startup
    logger.info("Starting up API wrapper...")
    if not await initialize_agent():
        logger.error("Failed to initialize agent")
        raise RuntimeError("Agent initialization failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API wrapper...")
    if mcp_client:
        try:
            mcp_client.__exit__(None, None, None)
        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")

# Create FastAPI app
app = FastAPI(
    title="Elasticsearch AI Agent API",
    description="REST API wrapper for AI-powered Elasticsearch queries using AWS Bedrock",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Doc Agent API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None,
        "mcp_enabled": mcp_client is not None,
        "tools_count": len(agent.tools) if agent else 0
    }

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Query the Elasticsearch AI agent
    
    Args:
        request: QueryRequest containing the query string and optional temperature
    
    Returns:
        QueryResponse with the agent's response
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Update model temperature if provided
        if request.temperature != 0.3:
            agent.model.temperature = request.temperature
        
        # Execute query
        result = agent(request.query.strip())
        
        # Extract response text
        response_text = ""
        if hasattr(result, 'message') and result.message:
            content = result.message.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                response_text = content[0].get('text', '')
        
        if not response_text:
            response_text = str(result) if result else "No response generated"
        
        logger.info("Query processed successfully")
        
        return QueryResponse(
            response=response_text,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return QueryResponse(
            response="",
            status="error",
            error=str(e)
        )

@app.post("/query-async", response_model=QueryResponse)
async def query_agent_async(request: QueryRequest):
    """
    Async version of query endpoint for better performance
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        logger.info(f"Processing async query: {request.query}")
        
        # Run agent query in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, agent, request.query.strip())
        
        # Extract response text
        response_text = ""
        if hasattr(result, 'message') and result.message:
            content = result.message.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                response_text = content[0].get('text', '')
        
        if not response_text:
            response_text = str(result) if result else "No response generated"
        
        logger.info("Async query processed successfully")
        
        return QueryResponse(
            response=response_text,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing async query: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return QueryResponse(
            response="",
            status="error",
            error=str(e)
        )

@app.get("/tools")
async def list_tools():
    """List available tools"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        tools_info = []
        for tool in agent.tools:
            tool_name = getattr(tool, 'name', None) or getattr(tool, '__name__', 'Unknown')
            tool_doc = getattr(tool, '__doc__', 'No description available')
            tools_info.append({
                "name": tool_name,
                "description": tool_doc
            })
        
        return {
            "tools": tools_info,
            "count": len(tools_info),
            "mcp_enabled": mcp_client is not None
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
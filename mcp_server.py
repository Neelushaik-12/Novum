#!/usr/bin/env python3
"""
MCP Server for Jobsearch AI
Model Context Protocol server for connecting with other applications
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import requests

app = FastAPI(title="Jobsearch AI MCP Server", version="1.0.0")

# ======================
# TOOL REGISTRY
# ======================
class ToolRegistry:
    """Registry to store tool metadata and descriptions"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, name: str, description: str, parameters: dict = None):
        """Register a tool with its metadata"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {}
        }
    
    def get_tools(self):
        """Return all registered tools"""
        return list(self.tools.values())

# Global tool registry
tool_registry = ToolRegistry()

# Register tools
tool_registry.register_tool(
    "search_jobs",
    "Search for jobs using external APIs (SerpAPI, LinkedIn, etc.)",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Job search query"},
            "location": {"type": "string", "description": "Job location"},
            "limit": {"type": "integer", "description": "Number of results"}
        },
        "required": ["query"]
    }
)

tool_registry.register_tool(
    "match_resume_to_jobs",
    "Match a resume to available jobs using RAG",
    {
        "type": "object",
        "properties": {
            "resume_text": {"type": "string", "description": "Resume text content"},
            "top_k": {"type": "integer", "description": "Number of top matches"}
        },
        "required": ["resume_text"]
    }
)

tool_registry.register_tool(
    "get_job_details",
    "Get detailed information about a specific job",
    {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID"}
        },
        "required": ["job_id"]
    }
)

# ======================
# MCP ENDPOINTS
# ======================

@app.get("/tools")
async def list_tools():
    """List all available MCP tools"""
    return {"tools": tool_registry.get_tools()}

@app.post("/tools/search_jobs")
async def search_jobs_tool(request_data: Dict[str, Any]):
    """Search for jobs using external APIs"""
    try:
        query = request_data.get("query", "")
        location = request_data.get("location", os.getenv("JOB_LOCATION", "United States"))
        limit = request_data.get("limit", 10)
        
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        
        # Use SerpAPI if available
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return {
                "ok": False,
                "error": "SERPAPI_KEY not configured",
                "results": []
            }
        
        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": api_key,
            "location": location,
            "num": limit
        }
        
        response = requests.get("https://serpapi.com/search", params=params, timeout=30)
        response.raise_for_status()
        data = response.json() or {}
        items = data.get("jobs_results", []) or []
        
        results = []
        for item in items[:limit]:
            if isinstance(item, dict) and item.get("title"):
                results.append({
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "location": item.get("location", ""),
                    "description": item.get("description", ""),
                    "apply_link": (item.get("apply_options", [{}])[0].get("link", "") if item.get("apply_options") else ""),
                })
        
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e), "results": []}

@app.post("/tools/match_resume_to_jobs")
async def match_resume_tool(request_data: Dict[str, Any]):
    """Match resume to jobs using RAG"""
    try:
        resume_text = request_data.get("resume_text", "")
        top_k = request_data.get("top_k", 5)
        
        if not resume_text:
            raise HTTPException(status_code=400, detail="resume_text is required")
        
        # Call the internal RAG endpoint
        internal_api = os.getenv("INTERNAL_API_URL", "http://localhost:5001")
        response = requests.post(
            f"{internal_api}/api/rag-search",
            json={
                "resume_text": resume_text,
                "top_k": top_k,
                "rerank_with_llm": True
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return {"ok": False, "error": f"RAG search failed: {response.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/tools/get_job_details")
async def get_job_details_tool(request_data: Dict[str, Any]):
    """Get detailed information about a specific job"""
    try:
        job_id = request_data.get("job_id", "")
        
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")
        
        # Call the internal API
        internal_api = os.getenv("INTERNAL_API_URL", "http://localhost:5001")
        response = requests.get(
            f"{internal_api}/api/jobs/{job_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"ok": False, "error": "Job not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "jobsearch-ai-mcp"}

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", 8001))
    print(f"Starting MCP Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


# MCP Server Setup Guide

## Overview
The MCP (Model Context Protocol) server allows the Jobsearch AI application to connect with other applications and services. It provides a standardized interface for job searching, resume matching, and job details retrieval.

## Features

1. **Job Search Tool**: Search for jobs using external APIs (SerpAPI, LinkedIn, etc.)
2. **Resume Matching Tool**: Match resumes to jobs using RAG (Retrieval Augmented Generation)
3. **Job Details Tool**: Get detailed information about specific jobs

## Installation

### 1. Install Dependencies

```bash
pip install fastapi uvicorn pydantic requests
```

Or add to `requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
requests>=2.31.0
```

### 2. Environment Variables

Add to your `.env` file:
```
MCP_PORT=8000
INTERNAL_API_URL=http://localhost:5001
SERPAPI_KEY=your_serpapi_key_here
```

## Running the MCP Server

### Standalone Mode

```bash
python mcp_server.py
```

The server will start on port 8000 (or the port specified in `MCP_PORT`).

### With Custom Port

```bash
MCP_PORT=9000 python mcp_server.py
```

## API Endpoints

### 1. List Available Tools
```
GET /tools
```

Returns a list of all available MCP tools.

### 2. Search Jobs
```
POST /tools/search_jobs
Body: {
  "query": "Software Engineer Python",
  "location": "United States",
  "limit": 10
}
```

### 3. Match Resume to Jobs (RAG)
```
POST /tools/match_resume_to_jobs
Body: {
  "resume_text": "Resume content here...",
  "top_k": 5
}
```

### 4. Get Job Details
```
POST /tools/get_job_details
Body: {
  "job_id": "job_123"
}
```

### 5. Health Check
```
GET /health
```

## Integration with Other Applications

### Example: Python Client

```python
import requests

MCP_SERVER = "http://localhost:8000"

# List tools
tools = requests.get(f"{MCP_SERVER}/tools").json()
print(tools)

# Search jobs
response = requests.post(
    f"{MCP_SERVER}/tools/search_jobs",
    json={
        "query": "Data Scientist",
        "location": "San Francisco, CA",
        "limit": 5
    }
)
jobs = response.json()
print(jobs)

# Match resume
response = requests.post(
    f"{MCP_SERVER}/tools/match_resume_to_jobs",
    json={
        "resume_text": "Your resume text here...",
        "top_k": 10
    }
)
matches = response.json()
print(matches)
```

### Example: JavaScript/Node.js Client

```javascript
const axios = require('axios');

const MCP_SERVER = 'http://localhost:8000';

// List tools
const tools = await axios.get(`${MCP_SERVER}/tools`);
console.log(tools.data);

// Search jobs
const jobs = await axios.post(`${MCP_SERVER}/tools/search_jobs`, {
  query: 'Software Engineer',
  location: 'United States',
  limit: 10
});
console.log(jobs.data);

// Match resume
const matches = await axios.post(`${MCP_SERVER}/tools/match_resume_to_jobs`, {
  resume_text: 'Your resume text here...',
  top_k: 5
});
console.log(matches.data);
```

## RAG Integration

The MCP server uses the RAG (Retrieval Augmented Generation) endpoint from the main Flask application. This provides:

1. **Vector-based similarity search**: Uses embeddings to find semantically similar jobs
2. **LLM-enhanced explanations**: Provides detailed explanations of why a resume matches a job
3. **Better accuracy**: Combines vector search with LLM re-ranking for improved results

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, change it:
```bash
export MCP_PORT=9000
python mcp_server.py
```

### Cannot Connect to Internal API
Make sure the Flask backend is running on port 5001 (or update `INTERNAL_API_URL` in `.env`).

### SerpAPI Errors
Ensure `SERPAPI_KEY` is set in your `.env` file. Get a free key from https://serpapi.com/

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  External Apps  │    │   MCP Server     │    │  Flask Backend  │
│                 │    │                  │    │                 │
│ • Job Boards    │───▶│ • Tool Registry  │───▶│ • RAG Search    │
│ • Other Services│    │ • API Gateway    │    │ • Job Matching  │
│ • Integrations  │    │ • Request Router │    │ • Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Next Steps

1. Add more tools to the MCP server (e.g., LinkedIn integration, Indeed API)
2. Implement authentication/authorization for MCP endpoints
3. Add rate limiting and caching
4. Create SDKs for popular languages (Python, JavaScript, Go)


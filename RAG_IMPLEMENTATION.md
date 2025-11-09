# RAG Implementation for Resume Matching

## Overview
This document describes the RAG (Retrieval Augmented Generation) implementation for resume matching in the Jobsearch AI application.

## What is RAG?

RAG combines:
1. **Retrieval**: Finding relevant jobs using vector similarity search
2. **Augmented Generation**: Using LLM to provide detailed explanations of matches

## Implementation Details

### 1. Vector Embeddings
- Resumes and job descriptions are converted to embeddings using OpenAI's embedding model
- Embeddings capture semantic meaning, not just keywords
- Similarity is calculated using cosine similarity

### 2. Retrieval Phase
- Top-K jobs are retrieved based on vector similarity
- Combines both local (admin-created) and external (SerpAPI) jobs
- Filters jobs by location and job type preferences

### 3. Generation Phase
- LLM analyzes each match and provides:
  - Match score (0-100)
  - Detailed explanation of why the resume matches
  - Key skills alignment
  - Experience alignment
  - Areas for improvement

## API Endpoint

### `/api/rag-search`

**Request:**
```json
{
  "user_id": "user_123",
  "resume_text": "Optional: if not provided, uses latest uploaded resume",
  "top_k": 10,
  "rerank_with_llm": true
}
```

**Response:**
```json
{
  "ok": true,
  "results": [
    {
      "job": {
        "id": "job_123",
        "title": "Software Engineer",
        "description": "...",
        "source": "local"
      },
      "similarity": 0.85,
      "match_explanation": "This resume matches well because..."
    }
  ]
}
```

## Frontend Integration

The frontend (`seeker.js`) now:
1. Validates resume upload before matching
2. Uses RAG endpoint for better results
3. Displays match explanations in expandable sections
4. Shows appropriate error messages when resume is not uploaded

## Key Features

### Resume Validation
- Users must upload a resume before matching
- Error message displayed under resume upload field if no resume
- Success message shown when resume is uploaded

### Match Explanations
- Each job match includes a detailed explanation
- Explanations are collapsible to save space
- Shows why the resume matches the job

### Better Accuracy
- RAG provides more accurate matches than simple keyword matching
- LLM re-ranking improves result quality
- Semantic understanding of resume and job descriptions

## Usage Flow

1. User uploads resume
2. User clicks "Start Matching"
3. System validates resume is uploaded
4. RAG endpoint is called with user_id
5. Vector search finds top-K similar jobs
6. LLM generates explanations for each match
7. Results displayed with explanations

## Configuration

Set in `.env`:
```
MATCH_THRESHOLD=50  # Minimum similarity percentage (0-100)
```

## Performance Considerations

- Embeddings are cached to avoid repeated API calls
- LLM explanations are optional (set `rerank_with_llm: false` to disable)
- Top-K limit prevents processing too many jobs

## Future Improvements

1. Batch processing for multiple resumes
2. Caching of job embeddings
3. Incremental updates when new jobs are added
4. Fine-tuned models for better matching
5. Multi-language support


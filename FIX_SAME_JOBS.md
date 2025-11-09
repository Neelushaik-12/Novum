# Fix: Same Jobs Showing for All Resumes

## Problem
Different resumes were showing the same job openings, regardless of resume content.

## Root Causes Found

### 1. **Weak Query Extraction** (FIXED)
- **Issue**: LLM query extraction was too generic and often failed, defaulting to "software engineer" for all resumes
- **Location**: `app.py` lines 924-942
- **Fix**: 
  - Improved prompt to be more specific and resume-focused
  - Better fallback logic that extracts keywords from resume
  - More context (2000 chars vs 1500)
  - Logging to see what query is generated

### 2. **No Similarity Threshold Filtering** (FIXED)
- **Issue**: All jobs were considered, even with very low similarity scores
- **Location**: `app.py` lines 1075-1094
- **Fix**:
  - Added minimum similarity threshold (default 30%, configurable via `RAG_MIN_SIMILARITY`)
  - Only shows jobs above threshold
  - Better ranking of top-k results

### 3. **Insufficient Debugging** (FIXED)
- **Issue**: Hard to debug why same jobs appeared
- **Fix**: Added comprehensive logging:
  - Resume preview
  - Generated search query
  - Job pool composition
  - Similarity scores
  - Top matches

## Changes Made

### 1. Improved Query Generation (`app.py` lines 924-1000)
```python
# Before: Simple prompt, weak fallback
# After: Detailed prompt with examples, better keyword extraction
```

**Key improvements**:
- More specific prompt asking for resume-specific queries
- Better cleanup of LLM response
- Smarter keyword extraction fallback
- Logging of generated query

### 2. Similarity Threshold Filtering (`app.py` lines 1079-1101)
```python
# Before: top_k from all jobs regardless of similarity
# After: Filter by threshold, then get top_k
```

**Key improvements**:
- Minimum similarity threshold (30% default)
- Configurable via `RAG_MIN_SIMILARITY` env var
- Better error handling if no jobs meet threshold

### 3. Enhanced Logging
- Resume preview for debugging
- Generated search query
- Job pool composition
- Similarity scores for top matches

## How It Works Now

1. **Resume Analysis**: 
   - LLM extracts resume-specific search query (e.g., "React Developer" not "software engineer")
   - Falls back to keyword extraction if LLM fails

2. **Job Fetching**:
   - External jobs: Fetched using resume-specific query
   - Local jobs: All admin-created jobs (same for all, but that's expected)

3. **Similarity Matching**:
   - Resume embedded using AI
   - All jobs embedded
   - Cosine similarity calculated
   - Only jobs above threshold considered
   - Top-k selected from qualified jobs

4. **Result Ranking**:
   - Sorted by similarity score
   - LLM re-ranking with explanations (optional)

## Configuration

Add to `.env`:
```bash
# Minimum similarity threshold (0.0 to 1.0)
RAG_MIN_SIMILARITY=0.3  # 30% minimum

# Job location for external search
JOB_LOCATION=United States
```

## Testing

After these fixes:
1. Upload a Python developer resume → Should see Python/backend jobs
2. Upload a React developer resume → Should see frontend/React jobs
3. Upload a Data Scientist resume → Should see data/ML jobs

Check server logs for:
- `🔍 Generated search query for resume: '...'`
- `📋 Job pool: X local jobs, Y external jobs`
- `✅ Found N jobs above threshold`

## Expected Behavior

✅ **Different resumes → Different queries → Different external jobs**
✅ **Similarity scores differ based on resume content**
✅ **Only highly relevant jobs shown (above threshold)**
✅ **Better logging to debug issues**

## If Issues Persist

1. **Check logs**: Look for generated queries - are they different?
2. **Check job pool**: Are external jobs different for different resumes?
3. **Check similarity scores**: Are they varying between resumes?
4. **Lower threshold**: Try `RAG_MIN_SIMILARITY=0.2` if too strict
5. **Check LLM**: Is `chat_complete` working correctly?

## Summary

The main fixes:
1. ✅ Better query extraction (resume-specific)
2. ✅ Similarity threshold filtering
3. ✅ Enhanced debugging/logging

These changes ensure that different resumes get different job recommendations based on their actual content.


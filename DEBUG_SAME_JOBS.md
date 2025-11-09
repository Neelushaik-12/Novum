# Issue Analysis: Same Jobs for All Resumes

## Problem Identified

After analyzing the code, I found several issues causing the same jobs to appear for different resumes:

### Issue 1: External Jobs Query Extraction Fails
**Location**: `app.py` lines 924-942
- The LLM query extraction might fail and default to "software engineer" for all resumes
- This causes all resumes to search for the same external jobs
- Even if the query succeeds, similar resumes might generate similar queries

### Issue 2: Job Pool Not Resume-Specific
**Location**: `app.py` lines 915-1004
- Local jobs: Always the same (all admin-created jobs)
- External jobs: Fetched based on query, but if query is same/similar → same jobs
- The job pool is built BEFORE resume-specific matching happens

### Issue 3: Similarity Scores Not Diverse Enough
**Location**: `app.py` lines 1012-1020
- Even with different similarity scores, if the job pool is identical, top_k results might overlap
- Need better filtering or more resume-specific job fetching

### Issue 4: No Resume-Specific Job Filtering
- All resumes get the same job pool
- Only the similarity ranking differs
- If similarity scores are close, same jobs appear at top

## Solutions Needed

1. **Improve query extraction** - Better LLM prompts, handle failures better
2. **Resume-specific job fetching** - Use resume content to filter jobs before similarity calculation
3. **Better job diversity** - Ensure different resumes get different job pools
4. **Threshold filtering** - Apply stricter similarity thresholds to show only highly relevant jobs
5. **Debug logging** - Add logs to see what query is generated for each resume


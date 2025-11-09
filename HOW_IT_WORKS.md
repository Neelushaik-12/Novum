# How Job Search Works 🔍

## Overview
This system uses **AI-powered semantic matching** (not simple keyword matching) to find jobs that match your resume.

## Search Process

### 1. **Resume Upload** 📄
- When you upload a resume, it's saved to the database
- Text is extracted from PDF, DOC, DOCX, or TXT files
- Each upload creates a new entry (so you can upload multiple resumes)
- The system uses the **latest uploaded resume** for matching

### 2. **Job Search Query Extraction** 🧠
- The system uses **AI (LLM)** to analyze your resume
- Extracts a 3-5 word search query (e.g., "Software Engineer Python" or "Data Scientist Machine Learning")
- This is smarter than keyword matching because it understands context
- Example: Resume with "Java, Spring Boot, REST APIs" → Query: "Software Engineer Java"

### 3. **External Job Search** 🌐
- Searches Google Jobs via SerpAPI using the AI-extracted query
- **Prioritizes jobs from company websites** (direct company sources)
- Fetches up to 20 jobs, then:
  - Takes up to 10 jobs from company websites
  - Adds up to 5 from other sources (job boards)
- Each job includes: title, description, location, company, apply link

### 4. **Semantic Matching** 🎯
- **NOT keyword matching** - uses AI embeddings (semantic understanding)
- Converts resume and job descriptions into numerical vectors (embeddings)
- Compares vectors using **cosine similarity** (measures how similar the meaning is)
- Result: Similarity percentage (0-100%)

#### Why Semantic Matching?
- Understands meaning, not just words
- "Software Engineer" matches "Developer" even if words differ
- "Python Developer" matches "Python Programmer"
- "Machine Learning Engineer" matches "ML Engineer"

### 5. **Threshold Filtering** 🔒
- Only shows jobs with similarity **above the threshold** (default: 50%)
- Configurable via `MATCH_THRESHOLD` in `.env` file
- Example: If threshold is 60%, only jobs with 60%+ match are shown

### 6. **Results Display** 📊
- Jobs are sorted by similarity (highest first)
- Shows match percentage for each job
- Company site jobs are marked as "Direct from Company"
- Each job shows: title, company, location, description, apply link

## Key Features

### ✅ **Multiple Resume Support**
- You can upload multiple resumes
- Each upload is saved separately
- System uses the **latest** resume for matching

### ✅ **Company Website Priority**
- Jobs from company websites are prioritized
- These are marked with "Direct from Company" badge
- More reliable than job board listings

### ✅ **AI-Powered Query Extraction**
- Uses LLM to understand your resume
- Extracts relevant search terms intelligently
- Better than simple keyword extraction

### ✅ **Semantic Matching**
- Uses embeddings (not keywords)
- Understands meaning and context
- More accurate than keyword matching

## Configuration

### Environment Variables
- `MATCH_THRESHOLD`: Minimum similarity percentage (default: 50)
- `SERPAPI_KEY`: API key for external job search
- `JOB_LOCATION`: Location for job search (default: "United States")

### Example `.env`:
```
MATCH_THRESHOLD=60
SERPAPI_KEY=your_api_key_here
JOB_LOCATION=United States
```

## Troubleshooting

### "No resume found for user"
- **Solution**: Upload a resume first before clicking "Start Matching"

### "Only one resume works"
- **Solution**: Each upload creates a new resume entry. The system uses the **latest** one. Make sure you:
  1. Upload the new resume
  2. Wait for "Resume uploaded successfully" message
  3. Then click "Start Matching"

### "No jobs found"
- Check if `SERPAPI_KEY` is configured in `.env`
- Check server logs for error messages
- Try lowering `MATCH_THRESHOLD` temporarily

### "Jobs not from company sites"
- Company site detection is automatic
- Look for "Direct from Company" badge
- If not showing, check server logs for company job count

## Technical Details

### Embedding Model
- Uses Vertex AI `text-embedding-004` or OpenAI embeddings
- Each resume/job is converted to a 768-dimensional vector
- Similarity is computed using cosine similarity

### Query Extraction
- Uses Vertex AI `gemini-1.5-flash` or OpenAI `gpt-4o-mini`
- Analyzes first 1500 characters of resume
- Extracts job title + key technology/skill

### Database
- SQLite database stores resumes
- Each resume has: id, user_id, filename, text, uploaded_at
- Latest resume is retrieved by sorting by `uploaded_at DESC`


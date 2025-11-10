# backend/app.py
import os
import json
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import numpy as np
from vector_store import search_index
from classifier import get_embedding, chat_complete, cosine_similarities
from dotenv import load_dotenv
from classifier import build_rag_search_prompt
from gcp_secrets import get_secret


# Load env for local overrides
load_dotenv()

# Secrets
SERPAPI_KEY = get_secret("SERPAPI_KEY", required=False)

# Import your AI functions (assumes classifier.py in same folder)
from classifier import get_embedding, cosine_similarities, chat_complete

# Optional notifier if present, import safely
try:
    from email_notifier import send_pass_notification
except Exception:
    send_pass_notification = None
try:
    from email_notifier import send_candidate_notification
except Exception:
    send_candidate_notification = None

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobmatch")

# App setup
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # restrict origins in production

# Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Simple SQLite DB
import sqlite3
DB_PATH = DATA_DIR / "jobmatch.db"
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, name TEXT)""")
c.execute("""CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, title TEXT, description TEXT, skills TEXT, questions TEXT, created_by TEXT, responsibilities TEXT, qualifications TEXT, company_name TEXT, hr_email TEXT)""")
# Add new columns if they don't exist (migration for existing databases)
try:
    c.execute("ALTER TABLE jobs ADD COLUMN responsibilities TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists
try:
    c.execute("ALTER TABLE jobs ADD COLUMN qualifications TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists
try:
    c.execute("ALTER TABLE jobs ADD COLUMN company_name TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists
try:
    c.execute("ALTER TABLE jobs ADD COLUMN hr_email TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists
c.execute("""CREATE TABLE IF NOT EXISTS resumes (id TEXT PRIMARY KEY, user_id TEXT, filename TEXT, text TEXT, uploaded_at TEXT)""")
c.execute("""CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, user_id TEXT, job_id TEXT, answers TEXT, score REAL, status TEXT, submitted_at TEXT)""")
conn.commit()

# Embedding cache to avoid repeated calls
@lru_cache(maxsize=1024)
def cached_get_embedding(text: str):
    return get_embedding(text)

def clear_embedding_cache():
    cached_get_embedding.cache_clear()

# Utility: extract text safely from uploaded file
def extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            # pypdf extraction
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = []
            for p in reader.pages:
                t = p.extract_text()
                if t:
                    pages.append(t)
            return "\n".join(pages)
        elif ext in [".docx", ".doc"]:
            import docx
            doc = docx.Document(str(path))
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        else:
            # treat as text
            with open(path, "r", errors="ignore") as f:
                return f.read()
    except Exception as e:
        logger.exception("Failed to extract text: %s", e)
        return ""

# Helpers for DB operations
def register_user(username, password, role, name):
    uid = str(uuid.uuid4())
    try:
        conn.execute("INSERT INTO users (id, username, password, role, name) VALUES (?,?,?,?,?)",
                     (uid, username, password, role, name))
        conn.commit()
        return True, uid
    except sqlite3.IntegrityError:
        return False, "Username exists"

def authenticate(username, password):
    cur = conn.cursor()
    cur.execute("SELECT id, role, name FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "role": row[1], "name": row[2], "username": username}

def save_job(title, description, skills, questions, created_by, responsibilities=None, qualifications=None, company_name=None, hr_email=None):
    jid = str(uuid.uuid4())
    conn.execute("INSERT INTO jobs (id, title, description, skills, questions, created_by, responsibilities, qualifications, company_name, hr_email) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (jid, title, description, json.dumps(skills), json.dumps(questions) if questions else None, created_by, 
                  json.dumps(responsibilities) if responsibilities else None, json.dumps(qualifications) if qualifications else None,
                  company_name or None, hr_email or None))
    conn.commit()
    return jid

def update_job(job_id, title, description, skills, responsibilities=None, qualifications=None, company_name=None, hr_email=None):
    """Update an existing job"""
    conn.execute("""UPDATE jobs SET title=?, description=?, skills=?, responsibilities=?, qualifications=?, company_name=?, hr_email=? 
                   WHERE id=?""",
                 (title, description, json.dumps(skills), 
                  json.dumps(responsibilities) if responsibilities else None,
                  json.dumps(qualifications) if qualifications else None,
                  company_name or None, hr_email or None, job_id))
    conn.commit()
    return True

def delete_job(job_id):
    """Delete a job by ID"""
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()
    return True

def get_job_by_id(job_id):
    """Get a single job by ID"""
    cur = conn.cursor()
    cur.execute("SELECT id,title,description,skills,questions,created_by,responsibilities,qualifications,company_name,hr_email FROM jobs WHERE id=?", (job_id,))
    r = cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0],
        "title": r[1],
        "description": r[2],
        "skills": json.loads(r[3]) if r[3] else [],
        "questions": json.loads(r[4]) if r[4] else None,
        "created_by": r[5],
        "responsibilities": json.loads(r[6]) if len(r) > 6 and r[6] else [],
        "qualifications": json.loads(r[7]) if len(r) > 7 and r[7] else [],
        "company_name": r[8] if len(r) > 8 and r[8] else None,
        "hr_email": r[9] if len(r) > 9 and r[9] else None
    }

def list_jobs():
    cur = conn.cursor()
    # Try to select with new columns, fallback to old schema if they don't exist
    try:
        cur.execute("SELECT id,title,description,skills,questions,created_by,responsibilities,qualifications,company_name,hr_email FROM jobs")
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append({
                "id": r[0],
                "title": r[1],
                "description": r[2],
                "skills": json.loads(r[3]) if r[3] else [],
                "questions": json.loads(r[4]) if r[4] else None,
                "created_by": r[5],
                "responsibilities": json.loads(r[6]) if len(r) > 6 and r[6] else [],
                "qualifications": json.loads(r[7]) if len(r) > 7 and r[7] else [],
                "company_name": r[8] if len(r) > 8 and r[8] else None,
                "hr_email": r[9] if len(r) > 9 and r[9] else None
            })
    except sqlite3.OperationalError:
        # Old schema - migrate on the fly
        try:
            cur.execute("SELECT id,title,description,skills,questions,created_by,responsibilities,qualifications FROM jobs")
            rows = cur.fetchall()
            out = []
            for r in rows:
                out.append({
                    "id": r[0],
                    "title": r[1],
                    "description": r[2],
                    "skills": json.loads(r[3]) if r[3] else [],
                    "questions": json.loads(r[4]) if r[4] else None,
                    "created_by": r[5],
                    "responsibilities": json.loads(r[6]) if len(r) > 6 and r[6] else [],
                    "qualifications": json.loads(r[7]) if len(r) > 7 and r[7] else [],
                    "company_name": None,
                    "hr_email": None
                })
        except sqlite3.OperationalError:
            # Very old schema
            cur.execute("SELECT id,title,description,skills,questions,created_by FROM jobs")
            rows = cur.fetchall()
            out = []
            for r in rows:
                out.append({
                    "id": r[0],
                    "title": r[1],
                    "description": r[2],
                    "skills": json.loads(r[3]) if r[3] else [],
                    "questions": json.loads(r[4]) if r[4] else None,
                    "created_by": r[5],
                    "responsibilities": [],
                    "qualifications": [],
                    "company_name": None,
                    "hr_email": None
                })
    return out

def save_resume_to_db(user_id, filename, text):
    rid = str(uuid.uuid4())
    conn.execute("INSERT INTO resumes (id,user_id,filename,text,uploaded_at) VALUES (?,?,?,?,?)",
                 (rid, user_id, filename, text, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return rid

def get_latest_resume(user_id):
    cur = conn.cursor()
    cur.execute("SELECT id, filename, text FROM resumes WHERE user_id=? ORDER BY uploaded_at DESC LIMIT 1", (user_id,))
    r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "filename": r[1], "text": r[2]}

def save_application(user_id, job_id, answers, score, status):
    aid = str(uuid.uuid4())
    conn.execute("INSERT INTO applications (id, user_id, job_id, answers, score, status, submitted_at) VALUES (?,?,?,?,?,?,?)",
                 (aid, user_id, job_id, json.dumps(answers), score, status, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return aid

def get_applications_for_job(job_id):
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, answers, score, status, submitted_at FROM applications WHERE job_id=?", (job_id,))
    return cur.fetchall()

def update_job_questions(job_id, questions):
    conn.execute("UPDATE jobs SET questions=? WHERE id=?", (json.dumps(questions) if questions else None, job_id))
    conn.commit()
    return True

# --- Endpoints ---

@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.get("/api/jobs")
def api_list_jobs():
    return jsonify(list_jobs())

@app.get("/api/jobs/<job_id>")
def get_job(job_id):
    job = get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    job_data = dict(job)
    if job_data.get("questions"):
     if isinstance(job_data["questions"], str):
        job_data["questions"] = json.loads(job_data["questions"])
     elif isinstance(job_data["questions"], list):
        pass  # already parsed
     else:
        job_data["questions"] = []
    else:
     job_data["questions"] = []
    return jsonify(job_data)

@app.post("/api/jobs")
def api_create_job():
    """
    Creates a new job posting.
    Accepts JSON:
      - title (required)
      - description (required)
      - skills (array or comma-separated string)
      - responsibilities (array or newline-separated string, optional)
      - qualifications (array or newline-separated string, optional)
      - company_name (optional)
      - hr_email (optional)
      - created_by (required)
    """
    try:
        data = request.get_json(force=True)
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        created_by = data.get("created_by", "").strip()
        
        if not title:
            return jsonify({"ok": False, "error": "title is required"}), 400
        if not description:
            return jsonify({"ok": False, "error": "description is required"}), 400
        if not created_by:
            return jsonify({"ok": False, "error": "created_by is required"}), 400
        
        # Handle skills - can be array or comma-separated string
        skills = data.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif not isinstance(skills, list):
            skills = []
        
        # Handle responsibilities - can be array or newline-separated string
        responsibilities = data.get("responsibilities", [])
        if isinstance(responsibilities, str):
            responsibilities = [r.strip() for r in responsibilities.split("\n") if r.strip()]
        elif not isinstance(responsibilities, list):
            responsibilities = []
        
        # Handle qualifications - can be array or newline-separated string
        qualifications = data.get("qualifications", [])
        if isinstance(qualifications, str):
            qualifications = [q.strip() for q in qualifications.split("\n") if q.strip()]
        elif not isinstance(qualifications, list):
            qualifications = []
        
        # Handle company_name and hr_email
        company_name = data.get("company_name", "").strip() or None
        hr_email = data.get("hr_email", "").strip() or None
        
        jid = save_job(title, description, skills, None, created_by, responsibilities, qualifications, company_name, hr_email)
        print(f"✅ Created job: {jid} - {title} (Company: {company_name}, HR: {hr_email})")
        return jsonify({"ok": True, "job_id": jid, "message": "Job created successfully"})
    except Exception as e:
        logger.exception("Create job failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.put("/api/jobs/<job_id>")
def api_update_job(job_id):
    """Update an existing job"""
    try:
        job = get_job_by_id(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404
        
        data = request.get_json(force=True)
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        
        if not title:
            return jsonify({"ok": False, "error": "title is required"}), 400
        if not description:
            return jsonify({"ok": False, "error": "description is required"}), 400
        
        # Handle skills - can be array or comma-separated string
        skills = data.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif not isinstance(skills, list):
            skills = []
        
        # Handle responsibilities
        responsibilities = data.get("responsibilities", [])
        if isinstance(responsibilities, str):
            responsibilities = [r.strip() for r in responsibilities.split("\n") if r.strip()]
        elif not isinstance(responsibilities, list):
            responsibilities = []
        
        # Handle qualifications
        qualifications = data.get("qualifications", [])
        if isinstance(qualifications, str):
            qualifications = [q.strip() for q in qualifications.split("\n") if q.strip()]
        elif not isinstance(qualifications, list):
            qualifications = []
        
        # Handle company_name and hr_email
        company_name = data.get("company_name", "").strip() or None
        hr_email = data.get("hr_email", "").strip() or None
        
        update_job(job_id, title, description, skills, responsibilities, qualifications, company_name, hr_email)
        print(f"✅ Updated job: {job_id} - {title}")
        return jsonify({"ok": True, "message": "Job updated successfully"})
    except Exception as e:
        logger.exception("Update job failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.delete("/api/jobs/<job_id>")
def api_delete_job(job_id):
    """Delete a job"""
    try:
        job = get_job_by_id(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404
        
        delete_job(job_id)
        print(f"✅ Deleted job: {job_id}")
        return jsonify({"ok": True, "message": "Job deleted successfully"})
    except Exception as e:
        logger.exception("Delete job failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/jobs/<job_id>/generate-questions")
def api_generate_questions(job_id):
    """Generate technical questions based on job description and experience level"""
    try:
        job = get_job_by_id(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404
        
        data = request.get_json(force=True) or {}
        experience_level = data.get("experience_level", "mid-level")  # entry, mid-level, senior
        
        # Extract job details
        title = job.get("title", "")
        description = job.get("description", "")
        skills = job.get("skills", [])
        responsibilities = job.get("responsibilities", [])
        qualifications = job.get("qualifications", [])
        
        # Build comprehensive job context
        job_context = f"Job Title: {title}\n\n"
        job_context += f"Description: {description}\n\n"
        if skills:
            job_context += f"Required Skills: {', '.join(skills) if isinstance(skills, list) else skills}\n\n"
        if responsibilities:
            resp_text = '\n'.join(responsibilities) if isinstance(responsibilities, list) else responsibilities
            job_context += f"Responsibilities:\n{resp_text}\n\n"
        if qualifications:
            qual_text = '\n'.join(qualifications) if isinstance(qualifications, list) else qualifications
            job_context += f"Qualifications:\n{qual_text}\n\n"
        
        # Generate questions using AI
        prompt = f"""Generate 5-7 technical interview questions for this job posting. The questions should be:
1. Relevant to the job description and required skills
2. Appropriate for {experience_level} level candidates
3. Cover both technical skills and problem-solving abilities
4. Mix of conceptual and practical questions

Job Details:
{job_context}

Return the questions as a JSON array of strings. Each question should be clear, specific, and test relevant technical knowledge.

Example format:
["What is the difference between REST and GraphQL APIs?", "How would you optimize a slow database query?", ...]

Return ONLY the JSON array, no other text:"""
        
        try:
            response = chat_complete(prompt)
            # Try to parse JSON from response
            import re
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                questions_json = json_match.group(0)
                questions = json.loads(questions_json)
            else:
                # Fallback: try parsing entire response
                questions = json.loads(response)
            
            if not isinstance(questions, list):
                questions = [str(questions)]
            
            # Ensure we have at least 5 questions
            if len(questions) < 5:
                # Add some generic questions based on skills
                generic_questions = [
                    f"Explain your experience with {skill}." for skill in (skills[:3] if isinstance(skills, list) else [])
                ]
                questions.extend(generic_questions[:5-len(questions)])
            
            # Save questions to job
            conn.execute("UPDATE jobs SET questions=? WHERE id=?", (json.dumps(questions), job_id))
            conn.commit()
            
            return jsonify({"ok": True, "questions": questions, "job_id": job_id})
        except Exception as e:
            logger.exception("Failed to generate questions: %s", e)
            # Return generic questions as fallback
            fallback_questions = [
                "What relevant experience do you have for this role?",
                "Describe a challenging technical problem you've solved.",
                "How do you stay updated with the latest technologies in this field?",
                "What is your approach to debugging and troubleshooting?",
                "Can you walk us through a project you're proud of?"
            ]
            return jsonify({"ok": True, "questions": fallback_questions, "job_id": job_id, "note": "Used fallback questions due to AI generation error"})
    except Exception as e:
        logger.exception("Generate questions failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/jobs/<job_id>/save-questions")
def api_save_questions(job_id):
    try:
        job = get_job_by_id(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404
        data = request.get_json(force=True) or {}
        questions = data.get("questions", [])
        if not isinstance(questions, list):
            return jsonify({"ok": False, "error": "questions must be an array"}), 400
        cleaned = []
        for q in questions:
            if isinstance(q, str):
                text = q.strip()
            elif isinstance(q, dict):
                text = str(q.get("question", "")).strip()
            else:
                text = str(q).strip()
            if text:
                cleaned.append(text)
        update_job_questions(job_id, cleaned)
        print(f"✅ Saved questions for job {job_id} ({len(cleaned)} questions)")
        return jsonify({"ok": True, "questions": cleaned})
    except Exception as e:
        logger.exception("Save questions failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/register")
def api_register():
    data = request.get_json(force=True)
    ok, info = register_user(data.get("username"), data.get("password"), data.get("role", "seeker"), data.get("name", ""))
    if ok:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": info}), 400

@app.post("/api/login")
def api_login():
    data = request.get_json(force=True)
    u = authenticate(data.get("username"), data.get("password"))
    if not u:
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401
    return jsonify({"ok": True, "user": u})

@app.post("/api/upload-resume")
def api_upload_resume():
    """
    Accepts multipart/form-data:
      - file (resume)
      - user_id
    Saves file, extracts text, stores in DB.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "No file part"}), 400
        file = request.files['file']
        user_id = request.form.get("user_id") or request.args.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "user_id required"}), 400
        filename = secure_filename(file.filename)
        saved_name = f"{uuid.uuid4()}_{filename}"
        fp = UPLOAD_DIR / saved_name
        file.save(str(fp))
        # extract text
        text = extract_text_from_file(fp)
        if not text.strip():
            logger.warning("Extracted resume text empty for file %s", filename)
            return jsonify({"ok": False, "error": "Could not extract text from resume. Please ensure the file is a valid PDF, DOC, or TXT file."}), 400
        
        print(f"📄 Uploaded resume: {filename} -> Extracted {len(text)} characters")
        rid = save_resume_to_db(user_id, saved_name, text)
        print(f"✅ Saved resume to database: {rid} for user {user_id}")
        return jsonify({"ok": True, "resume_id": rid, "filename": saved_name, "text_length": len(text)})
    except Exception as e:
        logger.exception("Upload resume failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/match")
def api_match():
    """
    Accepts JSON:
      - resume_text (optional if user_id provided)
      - user_id (optional)
      - preferred_location, job_type (optional)
    Returns list of matches (job objects + similarity)
    """
    try:
        payload = request.get_json(force=True)
        resume_text = (payload.get("resume_text") or "").strip()
        user_id = payload.get("user_id")
        preferred_location = (payload.get("preferred_location") or "").lower()
        job_type = (payload.get("job_type") or "").lower()

        if not resume_text and user_id:
            res = get_latest_resume(user_id)
            if not res or not res.get("text"):
                return jsonify({"ok": False, "error": "No resume found for user. Please upload a resume first."}), 400
            resume_text = res["text"]
            print(f"📄 Using resume from database: {res.get('filename', 'unknown')} ({len(resume_text)} chars)")

        if not resume_text:
            return jsonify({"ok": False, "error": "resume_text or user_id required"}), 400
        
        print(f"📋 Resume text length: {len(resume_text)} characters")

        # Get local jobs (admin-created jobs) first
        local_jobs = list_jobs() or []
        print(f"📋 Found {len(local_jobs)} local jobs from admin")
        
        # Try to get external jobs from SerpAPI
        external_jobs = []
        try:
            import requests
            api_key = SERPAPI_KEY
            if api_key and api_key.strip():
                # Use LLM to extract better search query from resume
                from classifier import chat_complete
                resume_preview = resume_text[:1500]
                query_prompt = f"""You are a job search assistant. Analyze this resume and extract a SPECIFIC job search query.

Resume:
{resume_preview}

Based on this resume, create a job search query (3-5 words) that would find the most relevant jobs.
...
Return ONLY the search query (3-5 words), nothing else. No explanation, no quotes, just the query.
"""
                try:
                    query = chat_complete(query_prompt).strip()
                    # Clean up: remove quotes, markdown, prefixes
                    query = query.replace('"', '').replace("'", '').strip()
                    if query.lower().startswith('query:'):
                        query = query[6:].strip()
                    if query.startswith('```'):
                        lines = query.split('\n')
                        query = '\n'.join(lines[1:-1]).strip()
                    # Limit to first 50 chars and 3-5 words
                    words = query.split()[:5]
                    query = ' '.join(words)[:50]
                    if not query or len(query) < 3:
                        query = "software engineer"  # Fallback
                except Exception as e:
                    print(f"⚠️ LLM query extraction failed: {e}, using fallback")
                    # Fallback to simple extraction
                    resume_lower = resume_text.lower()
                    common_titles = ["engineer", "developer", "analyst", "scientist", "manager", "designer", "architect", "programmer"]
                    found_title = None
                    for title in common_titles:
                        if title in resume_lower:
                            found_title = title
                            break
                    words = resume_text[:300].split()
                    skills = [w for w in words if len(w) > 3 and w.isalpha()][:3]
                    query_parts = []
                    if found_title:
                        query_parts.append(found_title.title())
                    query_parts.extend(skills[:2])
                    query = " ".join(query_parts) if query_parts else "software engineer"
                
                print(f"🔍 Searching external jobs with LLM-extracted query: '{query}'")
                
                params = {
                    "engine": "google_jobs",
                    "q": query,
                    "api_key": api_key,
                    "location": os.getenv("JOB_LOCATION", "United States"),
                    "num": 20
                }
                r = requests.get("https://serpapi.com/search", params=params, timeout=30)
                r.raise_for_status()
                data = r.json() or {}
                items = data.get("jobs_results", []) or []
                
                company_jobs = []  # Jobs from company websites
                other_jobs = []    # Jobs from other sources
                
                for item in items[:20]:  # Get more jobs to prioritize company sites
                    if isinstance(item, dict) and item.get("title") and item.get("description"):
                        # Get full description
                        desc = item.get("description", "")
                        # Add job highlights if available
                        highlights = item.get("job_highlights", {})
                        if isinstance(highlights, dict):
                            quals = highlights.get("Qualifications", [])
                            resp = highlights.get("Responsibilities", [])
                            if quals:
                                desc += "\n" + "\n".join(quals if isinstance(quals, list) else [str(quals)])
                            if resp:
                                desc += "\n" + "\n".join(resp if isinstance(resp, list) else [str(resp)])
                        
                        # Check if job is from company website (via field indicates source)
                        via = item.get("via", "").lower()
                        is_company_site = "company" in via or "direct" in via or item.get("company_name", "").lower() in via
                        
                        job_data = {
                            "id": f"ext_{item.get('job_id', str(uuid.uuid4()))}",
                            "title": item.get("title", ""),
                            "description": desc[:4000],  # Limit description length
                            "location": item.get("location", ""),
                            "company": item.get("company_name", item.get("via", "")),
                            "apply_link": (item.get("apply_options", [{}])[0].get("link", "") if item.get("apply_options") and len(item.get("apply_options", [])) > 0 else ""),
                            "source": "company" if is_company_site else "other",
                            "via": item.get("via", "")
                        }
                        
                        if is_company_site:
                            company_jobs.append(job_data)
                        else:
                            other_jobs.append(job_data)
                
                # Prioritize company jobs: take up to 10 company jobs, then fill with others
                external_jobs = company_jobs[:10] + other_jobs[:5]
                print(f"✅ Found {len(external_jobs)} external jobs from SerpAPI ({len(company_jobs)} from company sites, {len(other_jobs)} from other sources)")
            else:
                print("⚠️ SERPAPI_KEY not configured - skipping external job search")
        except ImportError:
            print("⚠️ 'requests' library not installed - cannot search external jobs")
        except Exception as e:
            print(f"⚠️ External job search failed: {e}")
            import traceback
            traceback.print_exc()
        
        if len(local_jobs) == 0 and len(external_jobs) == 0:
            return jsonify({
                "ok": True,
                "matches": [],
                "message": "No jobs found. Please check: 1) SERPAPI_KEY is configured in .env, 2) There are local jobs in the database, or 3) Try adjusting your search criteria."
            })

        # compute resume embedding once (using semantic embedding, not keyword matching)
        print(f"🧠 Computing semantic embedding for resume ({len(resume_text)} chars)...")
        print(f"   📝 This uses AI embeddings to understand meaning, not just keywords")
        resume_emb = cached_get_embedding(resume_text)

        # PHASE 1: Match local jobs (admin-created jobs) first
        local_matches = []
        if local_jobs:
            print(f"🔍 Phase 1: Matching {len(local_jobs)} local jobs against resume requirements...")
            for j in local_jobs:
                # Build comprehensive job description from all fields
                job_desc = j.get("description", "") or ""
                skills = j.get("skills", [])
                responsibilities = j.get("responsibilities", [])
                qualifications = j.get("qualifications", [])
                
                # Combine all job requirements into a comprehensive description
                full_job_desc = job_desc
                if skills and isinstance(skills, list) and len(skills) > 0:
                    full_job_desc += "\n\nRequired Skills: " + ", ".join(skills)
                if responsibilities and isinstance(responsibilities, list) and len(responsibilities) > 0:
                    full_job_desc += "\n\nResponsibilities:\n" + "\n".join(responsibilities)
                if qualifications and isinstance(qualifications, list) and len(qualifications) > 0:
                    full_job_desc += "\n\nQualifications:\n" + "\n".join(qualifications)
                
                # Skip if job description is empty
                if not full_job_desc.strip():
                    print(f"  ⚠️ Skipping local job '{j.get('title', 'Unknown')}' - no description")
                    continue
                
                # Compute similarity
                try:
                    job_emb = cached_get_embedding(full_job_desc)
                    sim_val = cosine_similarities(resume_emb, job_emb)
                    if isinstance(sim_val, (list, tuple, np.ndarray)):
                        try:
                            sim = float(sim_val[0])
                        except Exception:
                            sim = float(sim_val)
                    else:
                        sim = float(sim_val)
                    pct = round(sim * 100, 2)
                except Exception as e:
                    print(f"  ⚠️ Error computing similarity for local job '{j.get('title', 'Unknown')}': {e}")
                    continue
                
                # For local jobs, be more lenient with location/job_type filters
                # Only filter if location is explicitly set AND doesn't match
                loc = (j.get("location") or "").lower() if isinstance(j.get("location"), str) else ""
                title_desc = (j.get("title", "") + " " + full_job_desc).lower()
                
                # Skip only if location filter is provided AND job has location AND it doesn't match
                if preferred_location and loc and preferred_location not in loc:
                    print(f"  ⚠️ Local job '{j.get('title', 'Unknown')}' filtered by location: '{loc}' doesn't match '{preferred_location}'")
                    continue
                
                # Skip only if job_type filter is provided AND it doesn't match (be more lenient)
                if job_type and job_type != 'any' and job_type not in title_desc:
                    print(f"  ⚠️ Local job '{j.get('title', 'Unknown')}' filtered by job type: '{job_type}' not in description")
                    continue
                
                j_copy = j.copy()
                j_copy["similarity_pct"] = pct
                j_copy["source"] = "local"  # Mark as local job
                local_matches.append({"job": j_copy, "similarity": pct / 100.0})
                print(f"  ✓ Local job '{j.get('title', 'Unknown')}': {pct}% match")
            
            print(f"✅ Phase 1 complete: Found {len(local_matches)} matching local jobs (out of {len(local_jobs)} total)")

        # PHASE 2: Match external jobs
        external_matches = []
        if external_jobs:
            print(f"🔍 Phase 2: Matching {len(external_jobs)} external jobs...")
            # Filter external jobs by location/job_type if provided
            candidate_external = []
            for j in external_jobs:
                loc = (j.get("location") or "").lower() if isinstance(j.get("location"), str) else ""
                title_desc = (j.get("title", "") + " " + j.get("description", "")).lower()
                if preferred_location and preferred_location not in loc:
                    continue
                if job_type and job_type not in title_desc:
                    continue
                candidate_external.append(j)
            
            print(f"🔍 Computing similarity scores for {len(candidate_external)} external jobs...")
            for j in candidate_external:
                desc = j.get("description", "")
                job_emb = cached_get_embedding(desc)
                sim_val = cosine_similarities(resume_emb, job_emb)
                if isinstance(sim_val, (list, tuple, np.ndarray)):
                    try:
                        sim = float(sim_val[0])
                    except Exception:
                        sim = float(sim_val)
                else:
                    sim = float(sim_val)
                pct = round(sim * 100, 2)
                j_copy = j.copy()
                j_copy["similarity_pct"] = pct
                j_copy["source"] = "external"  # Mark as external job
                external_matches.append({"job": j_copy, "similarity": pct / 100.0})
            
            print(f"✅ Phase 2 complete: Found {len(external_matches)} matching external jobs")

        # Combine matches: local jobs first, then external jobs
        matches = local_matches + external_matches
        print(f"📊 Total matches: {len(matches)} (local: {len(local_matches)}, external: {len(external_matches)})")

        # Sort: local jobs by similarity (descending), then external jobs by similarity (descending)
        # Since we already have local_matches first, we just need to sort each group
        local_matches = sorted(local_matches, key=lambda x: -x["similarity"])
        external_matches = sorted(external_matches, key=lambda x: -x["similarity"])
        matches = local_matches + external_matches  # Local jobs first, then external
        
        # apply threshold if provided in env
        threshold_env = float(os.getenv("MATCH_THRESHOLD", "50"))  # Default to 50%
        if threshold_env < 1:
            threshold_pct = threshold_env * 100
        else:
            threshold_pct = threshold_env
        # ensure reasonable minimum (at least 40% - allow some flexibility)
        threshold_pct = max(threshold_pct, 40.0)
        
        print(f"🔒 Using similarity threshold: {threshold_pct}%")
        print(f"📈 Found {len(matches)} total matches before filtering")
        
        # Log all matches for debugging
        print(f"\n📊 Match Results Summary:")
        if local_matches:
            print(f"  Local Jobs (Admin-created):")
            for m in local_matches[:3]:  # Show top 3 local
                sim_pct = m["similarity"] * 100
                job_title = m["job"].get("title", "Unknown")
                print(f"    [{sim_pct:.1f}%] '{job_title}' - {'✓ PASS' if sim_pct >= threshold_pct else '✗ FILTERED OUT'}")
        if external_matches:
            print(f"  External Jobs (SerpAPI):")
            for m in external_matches[:3]:  # Show top 3 external
                sim_pct = m["similarity"] * 100
                job_title = m["job"].get("title", "Unknown")
                print(f"    [{sim_pct:.1f}%] '{job_title}' - {'✓ PASS' if sim_pct >= threshold_pct else '✗ FILTERED OUT'}")
        
        filtered = [m for m in matches if m["similarity"] * 100 >= threshold_pct]
        
        # Log detailed breakdown
        filtered_local_count = len([m for m in filtered if m["job"].get("source") == "local"])
        filtered_external_count = len([m for m in filtered if m["job"].get("source") == "external"])
        
        print(f"✅ Returning {len(filtered)} matches above {threshold_pct}% threshold")
        print(f"   - Local jobs: {filtered_local_count}/{len(local_matches)} passed threshold")
        print(f"   - External jobs: {filtered_external_count}/{len(external_matches)} passed threshold")
        
        # If local jobs exist but none passed threshold, show them anyway if they're above 30%
        # This ensures admin-created jobs are always visible if they exist
        if len(local_matches) > 0 and filtered_local_count == 0:
            print(f"⚠️ No local jobs passed {threshold_pct}% threshold. Showing local jobs above 30%...")
            local_above_30 = [m for m in local_matches if m["similarity"] * 100 >= 30.0]
            if local_above_30:
                print(f"   Found {len(local_above_30)} local jobs above 30% threshold - adding to results")
                # Add local jobs above 30% to filtered results (prioritize them)
                filtered = local_above_30 + [m for m in filtered if m["job"].get("source") != "local"]
        
        # Provide helpful message if no matches
        message = None
        if not filtered:
            if len(matches) > 0:
                top_match = matches[0]
                top_sim = top_match["similarity"] * 100
                message = f"Found {len(matches)} jobs, but none meet the {threshold_pct}% similarity threshold. Highest match: {top_sim:.1f}%. Try: 1) Uploading a more detailed resume, 2) Adding more relevant skills/experience, or 3) Lowering the threshold temporarily."
            elif len(local_matches) == 0 and len(external_matches) == 0:
                if len(local_jobs) == 0 and len(external_jobs) == 0:
                    message = "No jobs found. Check if SERPAPI_KEY is configured and there are local jobs in the database."
                else:
                    message = "No jobs found matching your location/job type filters. Try adjusting your search criteria."
            else:
                message = f"No jobs found with {threshold_pct}% or higher similarity. Try refining your resume or search criteria."
        
        # Separate filtered matches back into local and external for frontend display
        filtered_local = [m for m in filtered if m["job"].get("source") == "local"]
        filtered_external = [m for m in filtered if m["job"].get("source") == "external"]
        
        return jsonify({
            "ok": True, 
            "matches": filtered,  # Combined list (local first, then external)
            "local_matches": filtered_local,  # Local matches only
            "external_matches": filtered_external,  # External matches only
            "threshold_pct": threshold_pct,
            "message": message
        })
    except Exception as e:
        logger.exception("Match failed: %s", e)
        print(f"Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# New endpoint: /api/rag-search
@app.post("/api/rag-search")
def api_rag_search():
    """
    RAG-style search: finds top-k jobs using vector similarity, then optionally asks LLM to rescore/explain.
    Uses RAG (Retrieval Augmented Generation) for better matching.
    Accepts JSON:
      - resume_text (required) or user_id (to get latest resume)
      - top_k (optional, default 10)
      - rerank_with_llm (optional bool, default True)
    """
    try:
        payload = request.get_json(force=True) or {}
        resume_text = payload.get("resume_text", "").strip()
        user_id = payload.get("user_id")
        top_k = int(payload.get("top_k", 10))
        rerank = bool(payload.get("rerank_with_llm", True))

        # Get resume text if user_id provided
        if not resume_text and user_id:
            res = get_latest_resume(user_id)
            if not res or not res.get("text"):
                return jsonify({"ok": False, "error": "No resume found for user. Please upload a resume first."}), 400
            resume_text = res["text"]
            print(f"📄 Using resume from database: {res.get('filename', 'unknown')} ({len(resume_text)} chars)")

        if not resume_text:
            return jsonify({"ok": False, "error": "resume_text or user_id required"}), 400

        # Log resume summary for debugging
        resume_preview_words = resume_text[:500].split()[:20]
        resume_preview = ' '.join(resume_preview_words)
        print(f"🔍 RAG Search: Processing resume ({len(resume_text)} chars)")
        print(f"   Resume preview: {resume_preview}...")
        print(f"   Requested top_k: {top_k}")

        # Get all jobs (local + external)
        local_jobs = list_jobs() or []
        
        # Try to get external jobs
        external_jobs = []
        try:
            import requests
            api_key = SERPAPI_KEY
            if api_key and api_key.strip():
                from classifier import chat_complete
                # Extract key terms from resume for better query generation
                resume_preview = resume_text[:2000]  # Use more context
                
                query_prompt = f"""You are a job search assistant. Analyze this resume and extract a SPECIFIC job search query.

Resume:
{resume_preview}

Based on this resume, create a job search query (3-5 words) that would find the most relevant jobs.
Focus on:
1. Job title/role mentioned or implied
2. Primary technology/skill/domain
3. Experience level if apparent

Examples:
- "Software Engineer Python" for Python developers
- "Data Scientist Machine Learning" for ML data scientists
- "Product Manager SaaS" for product managers in SaaS
- "Marketing Manager Digital" for digital marketing managers

IMPORTANT: Make it SPECIFIC to this resume. If resume mentions "React developer", use "React Developer" not generic "software engineer".
If resume mentions "Data Analyst SQL", use "Data Analyst SQL" not just "Data Analyst".

Return ONLY the search query (3-5 words), nothing else. No explanation, no quotes, just the query.
"""
                try:
                    query = chat_complete(query_prompt).strip()
                    # Clean up the query
                    query = query.replace('"', '').replace("'", '').strip()
                    # Remove common prefixes
                    for prefix in ["Query:", "Search:", "Jobs:", "The query is:", "Query is:"]:
                        if query.lower().startswith(prefix.lower()):
                            query = query[len(prefix):].strip()
                    
                    # Extract first 5 meaningful words
                    words = [w for w in query.split() if len(w) > 2][:5]
                    query = ' '.join(words)[:50]
                    
                    # Fallback: Try to extract from resume directly
                    if not query or len(query) < 3:
                        query = "software engineer"
                        # Extract key skills/technologies from resume
                        resume_lower = resume_text.lower()
                        common_titles = ["engineer", "developer", "analyst", "scientist", "manager", "designer", "architect", "consultant", "specialist"]
                        common_skills = ["python", "java", "react", "javascript", "sql", "data", "machine learning", "ai", "cloud", "aws"]
                        
                        found_title = None
                        for title in common_titles:
                            if title in resume_lower:
                                found_title = title
                                break
                        
                        found_skill = None
                        for skill in common_skills:
                            if skill in resume_lower:
                                found_skill = skill
                                break
                        
                        if found_title and found_skill:
                            query = f"{found_title.title()} {found_skill.title()}"
                        elif found_title:
                            query = found_title.title()
                        else:
                            query = "software engineer"
                    
                    print(f"🔍 Generated search query for resume: '{query}' (resume length: {len(resume_text)} chars)")
                except Exception as e:
                    print(f"⚠️ Query extraction failed: {e}")
                    # Fallback: Try keyword extraction
                    resume_lower = resume_text.lower()
                    if "data" in resume_lower and "scientist" in resume_lower:
                        query = "Data Scientist"
                    elif "engineer" in resume_lower or "developer" in resume_lower:
                        query = "Software Engineer"
                    else:
                        query = "software engineer"
                    print(f"🔍 Using fallback query: '{query}'")
                
                params = {
                    "engine": "google_jobs",
                    "q": query,
                    "api_key": api_key,
                    "location": os.getenv("JOB_LOCATION", "United States"),
                    "num": 20
                }
                r = requests.get("https://serpapi.com/search", params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json() or {}
                    items = data.get("jobs_results", []) or []
                    for item in items[:15]:
                        if isinstance(item, dict) and item.get("title") and item.get("description"):
                            desc = item.get("description", "")
                            highlights = item.get("job_highlights", {})
                            if isinstance(highlights, dict):
                                quals = highlights.get("Qualifications", [])
                                resp = highlights.get("Responsibilities", [])
                                if quals:
                                    desc += "\n" + "\n".join(quals if isinstance(quals, list) else [str(quals)])
                                if resp:
                                    desc += "\n" + "\n".join(resp if isinstance(resp, list) else [str(resp)])
                            
                            external_jobs.append({
                                "id": f"ext_{item.get('job_id', str(uuid.uuid4()))}",
                                "title": item.get("title", ""),
                                "description": desc[:4000],
                                "location": item.get("location", ""),
                                "company": item.get("company_name", ""),
                                "apply_link": (item.get("apply_options", [{}])[0].get("link", "") if item.get("apply_options") else ""),
                                "source": "external"
                            })
        except Exception as e:
            print(f"⚠️ External job search failed: {e}")

        # Combine all jobs
        all_jobs = []
        for j in local_jobs:
            job_desc = j.get("description", "") or ""
            skills = j.get("skills", [])
            responsibilities = j.get("responsibilities", [])
            qualifications = j.get("qualifications", [])
            
            full_job_desc = job_desc
            if skills and isinstance(skills, list) and len(skills) > 0:
                full_job_desc += "\n\nRequired Skills: " + ", ".join(skills)
            if responsibilities and isinstance(responsibilities, list) and len(responsibilities) > 0:
                full_job_desc += "\n\nResponsibilities:\n" + "\n".join(responsibilities)
            if qualifications and isinstance(qualifications, list) and len(qualifications) > 0:
                full_job_desc += "\n\nQualifications:\n" + "\n".join(qualifications)
            
            if full_job_desc.strip():
                j_copy = j.copy()
                j_copy["full_description"] = full_job_desc
                j_copy["source"] = "local"
                all_jobs.append(j_copy)
        
        for j in external_jobs:
            j_copy = j.copy()
            j_copy["full_description"] = j.get("description", "")
            all_jobs.append(j_copy)

        if not all_jobs:
            return jsonify({"ok": True, "results": [], "message": "No jobs available for matching"})

        print(f"📋 Job pool: {len(local_jobs)} local jobs, {len(external_jobs)} external jobs = {len(all_jobs)} total")
        if external_jobs:
            print(f"   External job titles: {[j.get('title', 'N/A')[:30] for j in external_jobs[:5]]}")

        # Build job descriptions list for vector search
        job_descriptions = [j.get("full_description", j.get("description", "")) for j in all_jobs]
        
        # Use vector store for RAG retrieval
        resume_emb = cached_get_embedding(resume_text)
        job_embeddings = [cached_get_embedding(desc) for desc in job_descriptions]
        job_embeddings_array = np.array(job_embeddings)
        
        # Search using cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity([resume_emb], job_embeddings_array)[0]
        
        # Apply minimum similarity threshold to ensure quality matches
        min_similarity = float(os.getenv("RAG_MIN_SIMILARITY", "0.3"))  # 30% minimum
        print(f"📊 Computing similarities for {len(all_jobs)} jobs (min threshold: {min_similarity*100:.1f}%)")
        
        # Filter by minimum similarity and get top-k
        valid_indices = [i for i, sim in enumerate(sims) if sim >= min_similarity]
        if not valid_indices:
            print(f"⚠️ No jobs above {min_similarity*100:.1f}% similarity threshold")
            # Relax threshold slightly if no matches
            min_similarity = 0.2
            valid_indices = [i for i, sim in enumerate(sims) if sim >= min_similarity]
        
        # Get top-k from valid indices, sorted by similarity
        valid_sims = [(i, sims[i]) for i in valid_indices]
        valid_sims.sort(key=lambda x: x[1], reverse=True)
        top_indices = [i for i, _ in valid_sims[:top_k]]
        
        if top_indices:
            print(f"✅ Found {len(top_indices)} jobs above threshold (top similarity: {sims[top_indices[0]]*100:.1f}%)")
            # Log some similarity scores for debugging
            print(f"   Top 3 similarities: {[f'{sims[i]*100:.1f}%' for i in top_indices[:3]]}")
        else:
            print(f"⚠️ No jobs found above threshold after filtering")
        
        # Build initial results
        raw_results = []
        for idx in top_indices:
            job = all_jobs[idx]
            score = float(sims[idx])
            match_pct = round(score * 100, 2)
            raw_results.append({
                "job": job,
                "score": score,
                "match_pct": match_pct
            })

        # RAG: Use LLM to enhance results with explanations
        results = []
        for r in raw_results:
            job = r["job"]
            match_pct = r["match_pct"]
            job_desc = job.get("full_description", job.get("description", ""))

            result_entry = {
                "job": job,
                "similarity": r["score"],
                "match_score": match_pct,
                "match_explanation": ""
            }

            # LLM re-ranking and explanation for better RAG results
            if rerank:
                prompt = (
                    f"Analyze how well this resume matches the job description. "
                    f"Provide a detailed explanation of the match, highlighting:\n"
                    f"1. Key skills that match\n"
                    f"2. Experience alignment\n"
                    f"3. Any gaps or areas for improvement\n\n"
                    f"Resume (first 2000 chars):\n{resume_text[:2000]}\n\n"
                    f"Job Description:\n{job_desc[:2000]}\n\n"
                    f"Return a JSON object with: {{\"score\": <0-100>, \"explanation\": \"<detailed explanation>\"}}"
                )
                try:
                    llm_out = chat_complete(prompt)
                    import json as _json
                    # Try to extract JSON from response
                    if "{" in llm_out and "}" in llm_out:
                        start = llm_out.find("{")
                        end = llm_out.rfind("}") + 1
                        json_str = llm_out[start:end]
                        parsed = _json.loads(json_str)
                        if isinstance(parsed, dict):
                            if parsed.get("score") is not None:
                                result_entry["llm_score"] = int(parsed.get("score"))
                            result_entry["match_explanation"] = parsed.get("explanation", "")
                    else:
                        result_entry["match_explanation"] = llm_out
                except Exception as e:
                    result_entry["match_explanation"] = f"Analysis unavailable: {str(e)}"

            results.append(result_entry)

        # Sort by LLM score if available, otherwise by similarity
        if rerank and any("llm_score" in r for r in results):
            results = sorted(results, key=lambda x: x.get("llm_score", x.get("match_score", 0)), reverse=True)
        else:
            results = sorted(results, key=lambda x: x.get("match_score", 0), reverse=True)

        # Format results for frontend (similar to /api/match format)
        formatted_results = []
        for r in results:
            job_data = r["job"].copy()
            if job_data.get("source") == "local":
                if not job_data.get("questions"):
                    job_details = get_job_by_id(job_data.get("id"))
                    if job_details and job_details.get("questions"):
                        job_data["questions"] = job_details.get("questions")
            formatted_results.append({
                "job": job_data,
                "similarity": r["similarity"],
                "match_explanation": r.get("match_explanation", "")
            })

        if formatted_results:
            try:
                top_preview = [f"{item['job'].get('title', 'N/A')} ({item['similarity']*100:.1f}%)" for item in formatted_results[:3]]
                print(f"🔎 Returning {len(formatted_results)} matches | Preview: {top_preview}")
            except Exception as log_err:
                print(f"⚠️ Failed to log match preview: {log_err}")
        else:
            print("🔎 No matches to return after formatting")

        return jsonify({"ok": True, "results": formatted_results, "matches": formatted_results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception("RAG search failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/submit-answers")
def api_submit_answers():
    """
    Accepts JSON:
      - user_id
      - job (object with id, description, title)
      - questions (array)
      - answers: dict keyed by "1","2",...
    """
    try:
        data = request.get_json(force=True) or {}
        user_id = data.get("user_id")
        job = data.get("job") or {}
        job_id = job.get("id")
        questions = data.get("questions", [])
        answers = data.get("answers", {})

        if not user_id or not job_id:
            return jsonify({"ok": False, "error": "user_id and job.id required"}), 400

        total_score = 0
        results = {}
        for idx, q in enumerate(questions):
            key = str(idx + 1)
            ans = answers.get(key, "")
            if isinstance(q, dict):
                qtxt = q.get("question") or q.get("text") or ""
            else:
                qtxt = str(q)
            validate_prompt = f"Job description: {job.get('description','')}\nQuestion: {qtxt}\nAnswer: {ans}\nAssess relevance from 0-100 and say if likely copied or original. Return JSON like {{'score':int,'originality':'original'|'copied','feedback':'...'}}"
            out = chat_complete(validate_prompt)
            try:
                parsed = json.loads(out)
            except Exception:
                parsed = {"score": 70, "originality": "original", "feedback": out[:200]}
            results[key] = {"question": qtxt, "answer": ans, "validation": parsed}
            total_score += int(parsed.get("score", 70))
        percent = round((total_score / (len(questions) * 100)) * 100, 2) if questions else 0
        threshold = float(os.getenv("PASS_THRESHOLD", "60"))
        status = "passed" if percent >= threshold else "failed"
        app_id = save_application(user_id, job_id, results, percent, status)
        hr_email = job.get("hr_email") or job.get("HR_EMAIL") or os.getenv("ADMIN_EMAIL")
        if send_pass_notification and hr_email:
            try:
                cur = conn.cursor()
                cur.execute("SELECT name, username FROM users WHERE id=?", (user_id,))
                row = cur.fetchone()
                if row:
                    candidate_name, candidate_email = row
                    send_pass_notification(candidate_name, candidate_email, job.get("title", ""), percent, status=status, recipient_email=hr_email)
                    if send_candidate_notification:
                        send_candidate_notification(candidate_name, candidate_email, job.get("title", ""), percent, status=status)
            except Exception:
                logger.exception("Notification failed")
        return jsonify({"ok": True, "application_id": app_id, "score": percent, "status": status, "results": results})
    except Exception as e:
        logger.exception("Submit answers failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/api/my-applications")
def api_my_applications():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "user_id required"}), 400
    cur = conn.cursor()
    cur.execute("SELECT id, job_id, score, status, submitted_at FROM applications WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    out = []
    for r in rows:
        jid = r[1]
        cur2 = conn.cursor()
        cur2.execute("SELECT title FROM jobs WHERE id=?", (jid,))
        jt = cur2.fetchone()
        out.append({"application_id": r[0], "job_id": jid, "job_title": jt[0] if jt else jid, "score": r[2], "status": r[3], "submitted_at": r[4]})
    return jsonify(out)

# Simple debug endpoint
@app.get("/api/debug")
def api_debug():
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM resumes")
    resume_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs")
    job_count = cur.fetchone()[0]
    cur.execute("SELECT id, username FROM users LIMIT 5")
    users = [{"id": r[0], "username": r[1]} for r in cur.fetchall()]
    
    # Get sample jobs
    cur.execute("SELECT id, title, description FROM jobs LIMIT 3")
    sample_jobs = []
    for r in cur.fetchall():
        sample_jobs.append({
            "id": r[0],
            "title": r[1],
            "description_length": len(r[2] or "")
        })
    
    return jsonify({
        "status": "ok",
        "resume_count": resume_count,
        "job_count": job_count,
        "sample_jobs": sample_jobs,
        "users": users,
        "vertex_config": {
            "use_vertex": os.getenv("USE_VERTEX", "false"),
            "credentials_file": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        },
        "match_threshold": os.getenv("MATCH_THRESHOLD", "50")
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)

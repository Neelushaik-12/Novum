# backend/index_jobs.py
import json
from classifier import get_embedding
from vector_store import build_faiss_index
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent / "data" / "jobmatch.db"

def fetch_jobs_from_db():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, skills FROM jobs")
    rows = cur.fetchall()
    jobs = []
    for r in rows:
        jid, title, desc, skills_json = r
        skills = []
        try:
            skills = json.loads(skills_json) if skills_json else []
        except Exception:
            skills = []
        text = " ".join([title or "", desc or "", " ".join(skills)])
        jobs.append({"id": jid, "title": title, "description": desc, "text": text})
    conn.close()
    return jobs

def index_jobs():
    jobs = fetch_jobs_from_db()
    if not jobs:
        print("No jobs found to index.")
        return
    index, meta = build_faiss_index(jobs, embedding_fn=get_embedding)
    print(f"Indexed {len(jobs)} jobs.")
    return index, meta

if __name__ == "__main__":
    index_jobs()

# sample_data_generator.py
import json, os, uuid
from faker import Faker
fake = Faker()

JOB_FILE = "sample_jobs.json"
RESUME_DIR = "sample_resumes"

def create_sample_jobs():
    jobs = [
        {
            "id": str(uuid.uuid4()),
            "title": "Senior Python Developer",
            "description": "We need a senior python dev with experience in APIs, Pandas, and cloud deployment. Responsibilities: build backend services, data pipelines, and integrate with ML models.",
            "skills": ["python","apis","pandas","docker","gcp"],
            "questions": [
                {"question":"Explain how you'd design a REST API for a resume parsing service.","type":"text","max_score":100},
                {"question":"What Python library would you use to process CSV and why?","type":"text","max_score":50}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Data Analyst",
            "description": "Analyze transactional datasets, create dashboards, and work on data cleaning and feature engineering. Required: SQL, Excel, Python.",
            "skills": ["sql","excel","python","tableau"],
            "questions": None  # allow AI generation
        }
    ]
    with open(JOB_FILE,"w") as f:
        json.dump(jobs, f, indent=2)
    print("Created sample jobs:", JOB_FILE)

def create_sample_resumes():
    os.makedirs(RESUME_DIR, exist_ok=True)
    # resume for Python dev
    r1 = """John Doe
Senior Python Developer
Experience: 6 years in Python, built APIs with FastAPI, used Pandas for ETL, deployed on GCP with Docker and Cloud Run.
Skills: python, pandas, docker, gcp, apis"""
    with open(os.path.join(RESUME_DIR,"john_doe.txt"),"w") as f:
        f.write(r1)
    # resume for Data Analyst
    r2 = """Jane Smith
Data Analyst
Experience: 4 years analyzing transactional data, SQL expert, Excel pivot tables, generated dashboards using Tableau, scripting in Python for data cleaning.
Skills: sql, excel, tableau, python"""
    with open(os.path.join(RESUME_DIR,"jane_smith.txt"),"w") as f:
        f.write(r2)
    print("Created sample resumes in", RESUME_DIR)

if __name__ == "__main__":
    create_sample_jobs()
    create_sample_resumes()

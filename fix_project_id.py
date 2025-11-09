#!/usr/bin/env python3
"""
Script to check and fix project ID mismatch
"""

import os
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

print("Checking Project ID Configuration...")
print("=" * 60)

# Get project from env
env_project = os.getenv("VERTEX_PROJECT") or os.getenv("PROJECT_ID")
print(f"Current VERTEX_PROJECT in .env: {env_project}")

# Get project from credentials
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if creds_path and os.path.isfile(creds_path):
    with open(creds_path, 'r') as f:
        creds = json.load(f)
        creds_project = creds.get('project_id')
        print(f"Project ID in credentials file: {creds_project}")
        
        if env_project != creds_project:
            print("\n⚠️  MISMATCH DETECTED!")
            print(f"   .env has: {env_project}")
            print(f"   Credentials have: {creds_project}")
            print("\n📝 To fix, update your .env file:")
            print(f"   VERTEX_PROJECT={creds_project}")
        else:
            print("\n✓ Project IDs match!")
else:
    print("⚠️  Credentials file not found")

print("\n" + "=" * 60)
print("\nAlso verify:")
print(f"1. Vertex AI API is enabled for project: {creds_project if creds_path else 'UNKNOWN'}")
print(f"   https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project={creds_project if creds_path else 'YOUR_PROJECT_ID'}")
print(f"\n2. Service account has these roles:")
print(f"   - roles/aiplatform.user")
print(f"   - roles/serviceusage.serviceUsageConsumer")
print(f"\n   Service account email: google-application-credentials@{creds_project}.iam.gserviceaccount.com" if creds_path else "   (from your credentials file)")


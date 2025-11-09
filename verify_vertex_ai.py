#!/usr/bin/env python3
"""
Script to verify Vertex AI configuration
Run this to check if your Vertex AI setup is correct
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("Vertex AI Configuration Verification")
print("=" * 60)
print()

# Check 1: USE_VERTEX flag
use_vertex = os.getenv("USE_VERTEX", "false").lower() == "true"
print(f"1. USE_VERTEX enabled: {'✓ YES' if use_vertex else '✗ NO (using OpenAI)'}")
if not use_vertex:
    print("   → Set USE_VERTEX=true in .env to use Vertex AI")
    sys.exit(0)

print()

# Check 2: Google Application Credentials
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not credentials_path:
    print("2. GOOGLE_APPLICATION_CREDENTIALS: ✗ NOT SET")
    print("   → Set GOOGLE_APPLICATION_CREDENTIALS in .env")
    sys.exit(1)

print(f"2. GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")

if not os.path.isfile(credentials_path):
    print(f"   ✗ File not found at: {credentials_path}")
    sys.exit(1)

print(f"   ✓ File exists")

# Check if it's a valid JSON
try:
    import json
    with open(credentials_path, 'r') as f:
        creds = json.load(f)
        project_id_from_creds = creds.get('project_id', 'Not found')
        print(f"   ✓ Valid JSON file")
        print(f"   → Project ID in credentials: {project_id_from_creds}")
except Exception as e:
    print(f"   ✗ Invalid JSON file: {e}")
    sys.exit(1)

print()

# Check 3: Project ID
project = os.getenv("VERTEX_PROJECT") or os.getenv("PROJECT_ID")
if not project:
    print("3. VERTEX_PROJECT: ✗ NOT SET")
    print("   → Set VERTEX_PROJECT=titanium-portal-476620 (or your project ID) in .env")
    sys.exit(1)

print(f"3. VERTEX_PROJECT: {project}")
print("   ✓ Set")

# Verify project matches credentials
if project_id_from_creds and project_id_from_creds != project:
    print(f"   ⚠ Warning: Project in credentials ({project_id_from_creds}) doesn't match VERTEX_PROJECT ({project})")

print()

# Check 4: Location
location = os.getenv("VERTEX_LOCATION") or os.getenv("REGION") or "us-central1"
print(f"4. VERTEX_LOCATION: {location}")
print("   ✓ Set (default: us-central1)")

print()

# Check 5: Test Vertex AI Import
print("5. Testing Vertex AI imports...")
try:
    from vertexai import init as vertex_init
    from vertexai.language_models import TextEmbeddingModel
    from vertexai.generative_models import GenerativeModel
    print("   ✓ Imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    print("   → Install: pip install google-cloud-aiplatform")
    sys.exit(1)

print()

# Check 6: Test Vertex AI Initialization
print("6. Testing Vertex AI initialization...")
try:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    vertex_init(project=project, location=location)
    print("   ✓ Initialization successful")
except Exception as e:
    print(f"   ✗ Initialization failed: {e}")
    print()
    print("   Common issues:")
    print("   - Vertex AI API not enabled in Google Cloud Console")
    print("   - Service account lacks permissions")
    print("   - Wrong project ID or location")
    print("   - Insufficient permissions on the service account")
    sys.exit(1)

print()

# Check 7: Test Model Loading
print("7. Testing model loading...")
try:
    embedding_model = os.getenv("VERTEX_EMBEDDING_MODEL", "text-embedding-004")
    chat_model = os.getenv("VERTEX_CHAT_MODEL", "gemini-1.5-flash")
    
    print(f"   → Loading embedding model: {embedding_model}")
    emb_model = TextEmbeddingModel.from_pretrained(embedding_model)
    print("   ✓ Embedding model loaded")
    
    print(f"   → Loading chat model: {chat_model}")
    gen_model = GenerativeModel(chat_model)
    print("   ✓ Chat model loaded")
except Exception as e:
    print(f"   ✗ Model loading failed: {e}")
    print("   → Check if models are available in your region")
    sys.exit(1)

print()

# Check 8: Test API Access
print("8. Testing API access with sample call...")
try:
    test_text = "Hello, this is a test"
    print(f"   → Getting embedding for: '{test_text}'")
    embeddings = emb_model.get_embeddings([test_text])
    if embeddings and len(embeddings) > 0:
        print(f"   ✓ Embedding generated successfully (dimension: {len(embeddings[0].values)})")
    else:
        print("   ✗ No embeddings returned")
        sys.exit(1)
except Exception as e:
    error_msg = str(e)
    if "403" in error_msg or "Permission denied" in error_msg:
        print(f"   ✗ Permission denied: {e}")
        print()
        print("   → Enable Vertex AI API in Google Cloud Console:")
        print(f"     https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project={project}")
        print()
        print("   → Grant your service account these roles:")
        print("     - roles/aiplatform.user")
        print("     - roles/serviceusage.serviceUsageConsumer")
    else:
        print(f"   ✗ API call failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✓ All checks passed! Vertex AI is configured correctly.")
print("=" * 60)
print()
print("Configuration summary:")
print(f"  Project: {project}")
print(f"  Location: {location}")
print(f"  Credentials: {credentials_path}")
print(f"  Embedding Model: {os.getenv('VERTEX_EMBEDDING_MODEL', 'textembedding-gecko@001')}")
print(f"  Chat Model: {os.getenv('VERTEX_CHAT_MODEL', 'chat-bison@001')}")
print()


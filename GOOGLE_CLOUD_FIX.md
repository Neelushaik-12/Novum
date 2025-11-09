# Fixing Google Cloud Vertex AI 403 Permission Error

## What is this error?

The error `403 Permission denied on resource project titanium-portal-476620` means:
- Your code is trying to use **Google Cloud Vertex AI** (instead of OpenAI)
- The Google Cloud project either:
  - Doesn't have the Vertex AI API enabled
  - The service account doesn't have the right permissions
  - The credentials are not properly configured

## Solution 1: Use OpenAI Instead (RECOMMENDED - EASIEST)

By default, the app should use **OpenAI**, not Vertex AI. To ensure you're using OpenAI:

### Step 1: Check your `.env` file

Make sure you have:
```bash
# Use OpenAI (not Vertex AI)
USE_VERTEX=false

# Your OpenAI API key
OPENAI_API_KEY=sk-your-actual-openai-key-here

# If you have Vertex AI vars, comment them out or remove:
# USE_VERTEX=true  ← Don't set this to true unless you want Vertex AI
# GOOGLE_APPLICATION_CREDENTIALS=...  ← Only needed if USE_VERTEX=true
# VERTEX_PROJECT=...  ← Only needed if USE_VERTEX=true
```

### Step 2: Restart your Flask server

After updating `.env`, restart your server:
```bash
# Stop the current server (Ctrl+C)
# Then start it again
python app.py
```

You should see:
- `✓ Vertex AI initialized successfully` (if USE_VERTEX=true)
- Or it will silently use OpenAI (if USE_VERTEX=false or not set)

## Solution 2: Fix Vertex AI Permissions (If You Want to Use Vertex AI)

If you specifically want to use Google Cloud Vertex AI, you need to:

### 1. Enable Vertex AI API
Go to [Google Cloud Console](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=titanium-portal-476620) and enable:
- **Vertex AI API** (`aiplatform.googleapis.com`)

### 2. Grant Service Account Permissions
Your service account needs these roles:
- `roles/aiplatform.user` - To use Vertex AI models
- `roles/serviceusage.serviceUsageConsumer` - To consume the API

### 3. Verify Your `.env` File
```bash
USE_VERTEX=true
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your-service-account.json
VERTEX_PROJECT=titanium-portal-476620
VERTEX_LOCATION=us-central1  # or your preferred region
```

### 4. Test the Setup
The code will now automatically catch Vertex AI errors and fall back to OpenAI if setup fails.

## Which Should You Use?

- **OpenAI** (recommended): Easier setup, just needs API key
- **Vertex AI**: Requires Google Cloud project setup, but can be cheaper for high volume

## Verification

After fixing, check which backend is being used:
1. Start your Flask server
2. Look for initialization messages in the console
3. Or visit: `http://localhost:5001/api/debug`

The app will now automatically fall back to OpenAI if Vertex AI fails, so you shouldn't see this error anymore!


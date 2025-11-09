# Jobsearch AI - Setup Guide

## Creating a Virtual Environment

### Step 1: Navigate to the project directory
```bash
cd Code4Training/Jobsearch_AI
```

### Step 2: Create a virtual environment
On macOS/Linux:
```bash
python3 -m venv venv
```

On Windows:
```bash
python -m venv venv
```

### Step 3: Activate the virtual environment
On macOS/Linux:
```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

### Step 4: Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Create a .env file
Create a `.env` file in the `Jobsearch_AI` directory with your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
SENDGRID_API_KEY=your_sendgrid_api_key_here
SERPAPI_KEY=
JOB_LOCATION=United States
MATCH_THRESHOLD=0.8
PASS_THRESHOLD=60
```

**Important:** To enable job search from company websites:
1. Sign up for a free SerpAPI account at https://serpapi.com/
2. Get your API key from the dashboard
3. Add `SERPAPI_KEY=your_key_here` to your `.env` file
4. Optionally set `JOB_LOCATION` to filter jobs by location (e.g., "New York, NY", "San Francisco, CA")

### Step 6: Run the application
```bash
streamlit run app.py
```

## Deactivating the Virtual Environment
When you're done working, deactivate the environment:
```bash
deactivate
```


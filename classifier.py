import os
import numpy as np
import logging
from dotenv import load_dotenv
from vertexai import init as vertexai_init
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
from openai import OpenAI

# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)

# -----------------------------
# 🔹 Vertex AI Setup
# -----------------------------
try:
    from vertexai import init
    from vertexai.language_models import TextEmbeddingModel
    from vertexai.generative_models import GenerativeModel

    PROJECT_ID = os.getenv("PROJECT_ID") or os.getenv("VERTEX_PROJECT")
    REGION = os.getenv("REGION") or os.getenv("VERTEX_LOCATION", "us-central1")
    if PROJECT_ID:
        init(project=PROJECT_ID, location=REGION)
        logging.info(f"✓ Vertex AI initialized (project={PROJECT_ID}, region={REGION})")
    else:
        logging.warning("⚠️ PROJECT_ID not set; Vertex AI may fail.")
    USE_VERTEX = True
except Exception as e:
    logging.warning(f"⚠️ Vertex AI not available: {e}")
    USE_VERTEX = False

# -----------------------------
# 🔹 OpenAI Setup (Fallback)
# -----------------------------
openai_client = None

# Load .env first (if not already done in app.py)
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if api_key and api_key.strip():
    try:
        # Initialize OpenAI client with only api_key
        openai_client = OpenAI(api_key=api_key)
        logging.info("✓ OpenAI client initialized")
    except Exception as e:
        logging.warning(f"⚠️ OpenAI client initialization failed: {e}")
        openai_client = None
else:
    logging.warning("ℹ️ OPENAI_API_KEY not set; OpenAI will not be available")


# -----------------------------
# 🔹 Embedding Function
# -----------------------------
def get_embedding(text: str):
    """Generate embeddings using Vertex AI or OpenAI"""
    if not text or len(text.strip()) == 0:
        return np.zeros(768)

    # Try Vertex AI
    if USE_VERTEX:
        try:
            embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            embeddings = embedding_model.get_embeddings([text])
            return np.array(embeddings[0].values)
        except Exception as e:
            logging.warning(f"⚠️ Vertex embedding failed: {e}")

    # Fallback → OpenAI
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        logging.error(f"⚠️ OpenAI embedding failed: {e}")
        return np.zeros(1536)


# -----------------------------
# 🔹 Cosine Similarity
# -----------------------------
def cosine_similarities(vec1, vec2):
    """Compute cosine similarity between two vectors"""
    from sklearn.metrics.pairwise import cosine_similarity
    return float(cosine_similarity([vec1], [vec2])[0][0])


# -----------------------------
# 🔹 Resume vs Job Matching
# -----------------------------
def match_resume_to_job(resume_text, job_description):
    """Compute resume-job match percentage"""
    emb_resume = get_embedding(resume_text)
    emb_job = get_embedding(job_description)
    similarity = cosine_similarities(emb_resume, emb_job)
    return round(similarity * 100, 2)


# -----------------------------
# 🔹 LLM Text Completion
# -----------------------------
def chat_complete(prompt: str):
    """Generate AI text using Vertex AI (Gemini) or OpenAI with fallback."""
    # Initialize Vertex AI
    try:
        vertexai_init(project="titanium-portal-476620-s9", location="us-central1")
    except Exception as e:
        logging.warning(f"⚠️ Vertex initialization failed: {e}")

    # Try Vertex AI first
    if USE_VERTEX:
        try:
            # ✅ Updated model ID
            model = GenerativeModel("gemini-1.5-flash-001")  # or "gemini-1.5-pro-001"
            response = model.generate_content(prompt)
            if response and hasattr(response, "text") and response.text:
                return response.text.strip()
        except Exception as e:
            logging.warning(f"⚠️ Vertex chat_complete failed: {e}")
            # Optional: simple keyword fallback if model fails
            try:
                import re
                keywords = re.findall(r'\b[A-Z][a-zA-Z]+\b', prompt)
                return " ".join(keywords[:10]) or "general job search"
            except Exception:
                pass

    # Fallback → OpenAI
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"⚠️ OpenAI chat_complete failed: {e}")

    # Final fallback
    return "Sorry, AI response could not be generated at the moment."

def build_rag_search_prompt(resume_text: str, top_k: int = 10) -> str:
    return f"""
You are an AI assistant specialized in job matching.

Analyze the candidate's resume and create a highly relevant search query
to find matching job postings. The query should capture their **role**, **skills**, and **domain**,
but avoid personal details like name or location unless it’s part of the target market.
Only include technical or IT job roles if resume mentions software, programming, data, or AI-related skills.

### Example:
Resume → "Experienced Java developer with Spring Boot, SQL, and microservices"
Output → "Senior Java Backend Developer Spring Boot SQL jobs"

Now generate one best search query and up to 5 related keywords.

### Resume:
{resume_text}

### Output format (strict):
Search Query: <short query string>
Keywords: <comma-separated list of up to 5 key skills>
Limit to {top_k} results.
    """.strip()

      
def build_rag_search_prompt(resume_text: str, top_k: int = 10) -> str:
    prompt = build_rag_search_prompt(resume_text)
    query = chat_complete(prompt).strip()
    return query

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from classifier import get_embedding

# --- Create a simple in-memory vector index using numpy + sklearn ---

def build_index(job_descriptions):
    """Build in-memory embeddings index for all jobs"""
    embeddings = [get_embedding(job) for job in job_descriptions]
    return np.array(embeddings)

def search_index(query_text, job_descriptions, job_embeddings, top_k=5):
    """Search jobs using cosine similarity (no FAISS needed)"""
    query_emb = get_embedding(query_text)
    sims = cosine_similarity([query_emb], job_embeddings)[0]
    top_indices = sims.argsort()[::-1][:top_k]
    results = [
        {"job": job_descriptions[i], "score": round(float(sims[i]) * 100, 2)}
        for i in top_indices
    ]
    return results

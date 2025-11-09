# Vertex AI Model Update

## Issue Fixed

The old model names were causing 404 errors:
- ❌ `textembedding-gecko@001` (deprecated/not available)
- ❌ `chat-bison@001` (deprecated/not available)

## Updated Models

Updated to current Vertex AI models:
- ✅ `text-embedding-004` - Latest embedding model
- ✅ `gemini-1.5-flash` - Fast Gemini model for chat/completions

## Configuration

The models are now set as defaults in `classifier.py`. You can override them in your `.env` file:

```bash
# Optional: Override default models
VERTEX_EMBEDDING_MODEL=text-embedding-004
VERTEX_CHAT_MODEL=gemini-1.5-flash

# Or use other available models:
# VERTEX_CHAT_MODEL=gemini-1.5-pro  # More powerful, slower
# VERTEX_CHAT_MODEL=gemini-pro     # Older version
```

## Available Models

### Embedding Models
- `text-embedding-004` (recommended, 768 dimensions)
- `textembedding-gecko@003` (if available in your region)

### Chat/Generative Models
- `gemini-1.5-flash` (recommended, fast and efficient)
- `gemini-1.5-pro` (more powerful, slower)
- `gemini-pro` (older version)

## Testing

After updating, restart your Flask server and try the job matching again. The models should now work correctly!

To verify models are accessible, check:
```bash
venv/bin/python verify_vertex_ai.py
```


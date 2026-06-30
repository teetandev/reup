# Debug: Upload & AI pipeline

- Browser upload uses **FormData field `upload_token`** (NOT Authorization header) to avoid
  CORS preflight. Worker falls back to `Authorization: Bearer` for non-browser clients.
- Missing token on upload/start → 401.
- Chunk path: chunks are `audio/chunks/chunk_000.mp3` **relative to job work_dir**;
  transcribe rebuilds via `work_dir / chunk["path"]`.
- Transcribe failures log chunk_path, exists, size_bytes, model, status (never the API key).
- Test with `MOCK_AI=true` to bypass Groq/Gemini.
- Groq: GROQ_API_KEY + GROQ_MODEL (whisper-large-v3). Gemini: GEMINI_API_KEY + GEMINI_MODEL.

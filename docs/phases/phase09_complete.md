# Phase 09 — Video Pipeline

## Changed files

**Created:**
- `packages/video-pipeline/video_pipeline/__init__.py`
- `packages/video-pipeline/video_pipeline/config.py`
- `packages/video-pipeline/video_pipeline/errors.py`
- `packages/video-pipeline/video_pipeline/progress.py`
- `packages/video-pipeline/video_pipeline/probe.py`
- `packages/video-pipeline/video_pipeline/extract_audio.py`
- `packages/video-pipeline/video_pipeline/chunk_audio.py`
- `packages/video-pipeline/video_pipeline/transcribe.py`
- `packages/video-pipeline/video_pipeline/translate.py`
- `packages/video-pipeline/video_pipeline/subtitle.py`
- `packages/video-pipeline/video_pipeline/render.py`
- `packages/video-pipeline/video_pipeline/pipeline.py`
- `packages/video-pipeline/test_pipeline.py`

**Updated:**
- `packages/video-pipeline/requirements.txt` (added pydantic, openai, google-genai, python-dotenv)
- `packages/video-pipeline/.env.example` (added all required env vars)
- `AI_HANDOFF.md` (Phase 09 marked done, added Phase 09 notes)

## How to run/test

```powershell
cd packages\video-pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
```

Run test:
```powershell
python test_pipeline.py path\to\sample_video.mp4
```

Output artifacts saved to `./test_output/`:
- `metadata.json` — video probe results
- `audio/full_audio.mp3` — extracted audio
- `audio/chunks/chunk_*.mp3` — audio chunks
- `transcript/chunk_*.json` — per-chunk transcripts
- `transcript/transcript.json` — merged transcript
- `translation/checkpoint.json` — translation checkpoint
- `translation/translated.json` — translated segments
- `subtitle/subtitle.srt` — SRT subtitle file
- `output/output.mp4` — final hardsub video

## Required env vars

**Required:**
- `GROQ_API_KEY` — Groq API key for Whisper transcription
- `GEMINI_API_KEY` — Google Gemini API key for translation

**Optional (with defaults):**
- `FFMPEG_BIN=ffmpeg` — FFmpeg binary path
- `FFPROBE_BIN=ffprobe` — FFprobe binary path
- `FFMPEG_THREADS=1` — FFmpeg thread count
- `FFMPEG_PRESET=ultrafast` — FFmpeg encoding preset
- `FFMPEG_CRF=28` — FFmpeg quality (higher = lower quality/size)
- `GROQ_MODEL=whisper-large-v3` — Whisper model
- `GEMINI_MODEL=gemini-2.5-flash` — Gemini model
- `TRANSLATION_BATCH_SIZE=50` — Segments per batch
- `MAX_CHUNK_DURATION_SEC=300` — Audio chunk duration (5 min)
- `MAX_CHUNK_SIZE_MB=20` — Max chunk file size

## Security notes

- **No hard-coded secrets:** All API keys from environment only
- **No hard-coded paths:** FFmpeg binaries configurable via env
- **API keys never logged:** Not in logs, errors, or debug output
- **Checkpoint files safe:** Translation checkpoints contain translations only, no secrets
- **Path handling:** All paths use pathlib.Path, relative to work_dir
- **Subprocess safety:** All subprocess calls use list format (no shell injection)
- **Error details limited:** stderr truncated to 500-1000 chars in error details

## Known limitations

- **No resume support yet:** Failed jobs cannot resume from checkpoint (Phase 10 may add)
- **No cleanup:** Intermediate files (chunks, audio) kept after completion (cleanup in Phase 10 or 14)
- **No file size validation in chunker:** Assumes chunk duration limits file size (works for 16kHz mono MP3)
- **No progress granularity in long steps:** Transcription/translation show single progress value for entire step
- **No concurrent chunk transcription:** Chunks transcribed sequentially (OK for MVP, could parallelize later)
- **Gemini rate limiting:** 5-second sleep between batches (free tier conservative, may be too slow for production)
- **SRT wrapping:** Long translations not wrapped (may overflow subtitle area)
- **No audio stream selection:** Uses first audio stream found (OK for MVP single-audio files)

## Next prompt

```
Implement Phase 10 — Agent–Pipeline Integration only. Read AI_HANDOFF.md, prompts/phases/10-agent-pipeline-integration.md, docs/specs/ACCEPTANCE_CRITERIA.md. Wire packages/video-pipeline into services/vps-agent. Create services/vps-agent/app/pipeline_runner.py that: (1) imports run_pipeline from video_pipeline, (2) wraps it with progress reporting to Control API via POST /jobs/{job_id}/agent-status, (3) handles all PipelineError types and maps to job FAILED status with error details, (4) runs pipeline in background task on POST /jobs/{job_id}/start, (5) releases node slot on completion (DONE/FAILED). Add POST /jobs/{job_id}/download endpoint to serve output/output.mp4. Update job statuses: EXTRACTING_AUDIO → CHUNKING_AUDIO → TRANSCRIBING → TRANSLATING → GENERATING_SRT → RENDERING → DONE. Ensure node releases on error. Test end-to-end: upload → start → poll status → download. Do NOT implement frontend yet (Phase 11). Update AI_HANDOFF.md.
```

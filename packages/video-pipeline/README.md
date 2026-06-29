# packages/video-pipeline

Reusable Python pipeline modules consumed by `services/vps-agent`.

Steps (see `docs/specs/PIPELINE_SPEC.md`):
1. Validate input (ffprobe)
2. Extract audio
3. Chunk audio
4. Transcribe Chinese
5. Merge transcript (apply chunk offsets)
6. Translate to Vietnamese
7. Generate SRT
8. Burn hardsub
9. Verify output
10. Cleanup

Reuses legacy `translate.py` (Gemini batch + checkpoint/retry) and `main.py`
(audio extract + Whisper) logic — to be made importable and configurable.

Implemented in Phase 09. This is a Phase 01 placeholder.

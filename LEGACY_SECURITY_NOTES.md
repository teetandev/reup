# Legacy Files Security Notes

## main.py (root directory)

**Status:** Legacy prototype code, NOT used in production.

**Security issues:**
1. Hardcoded API key: `***REDACTED***`
2. Hardcoded Windows FFmpeg path: `C:\Users\Admin\AppData\Local\...`
3. Not part of the monorepo architecture

**Action required before public release:**
- Delete `main.py` from the repository, OR
- Move to `legacy/` directory with clear warning, OR
- Replace hardcoded key with placeholder and add warning comment

**Current status:** File exists at repo root but is not imported or referenced by any production code.

## vps_server.py

**Status:** Legacy prototype, superseded by `services/vps-agent`.

**Note:** Needs same treatment as `main.py` if it contains secrets.

## translate.py

**Status:** Legacy prototype, logic reused in `packages/video-pipeline/video_pipeline/translate.py`.

**Note:** Check for hardcoded API keys before public release.

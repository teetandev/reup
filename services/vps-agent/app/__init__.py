"""Reup Vietsub VPS Agent.

FastAPI service running on each Ubuntu VPS node. Phase 05 provides the base:
config, structured errors, health/status endpoints, and a single-job guard
(``MAX_JOBS=1``). Upload, heartbeat, and the video pipeline arrive in later phases.
"""

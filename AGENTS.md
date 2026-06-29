# AGENTS.md — Rules for Any Coding Agent

## Summary

This repo builds a low-cost distributed video processing web app. The key design is a lightweight control web plus multiple VPS processing agents.

## Do

- Keep control API lightweight.
- Keep video processing inside VPS agent.
- Use DB state for jobs and nodes.
- Use heartbeat for liveness.
- Use transaction/lock for node assignment.
- Use short-lived upload tokens.
- Use environment variables.
- Write useful logs.
- Update docs.

## Do Not

- Do not place FFmpeg in web frontend.
- Do not process 500MB uploads in serverless.
- Do not use in-memory job state for production.
- Do not store plaintext keys/passwords.
- Do not trust file extensions only.
- Do not add paid services by default.
- Do not implement platform scraping in MVP.

## When Unsure

Prefer the safest, cheapest, simplest implementation that preserves the architecture.

# Security Checklist

```text
[ ] No secrets in source
[ ] .env ignored
[ ] .env.example complete
[ ] Secret keys hashed
[ ] Node tokens not exposed
[ ] Upload tokens expire
[ ] Upload token scoped to job/node/user
[ ] Path traversal prevented
[ ] File size enforced while streaming
[ ] FFmpeg command uses internal paths only
[ ] Logs redact tokens
[ ] Node lock is atomic
[ ] Failed jobs release nodes
[ ] Cleanup implemented
```

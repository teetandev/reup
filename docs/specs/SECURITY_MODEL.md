# Security Model

## Actors

```text
Anonymous browser
Authenticated user
Admin
VPS agent
Control API
```

## Trust Boundaries

```text
Browser is untrusted.
VPS agent is semi-trusted only if node token is valid.
Control API is trusted coordinator.
Database is private.
```

## Authentication Types

### User Secret Key

Used only for login.

Storage:
```text
hash only
prefix for display
```

### JWT / Session Token

Used by frontend after login.

### Node Token

Used by VPS agent to call control API.

### Upload Token

Short-lived token for direct upload to a specific node/job.

Must bind:

```text
job_id
user_id
node_id
expiry
purpose=upload
```

## Forbidden Storage

```text
plaintext user secret key
plaintext VPS password
provider API key in source code
upload token in logs
node token in frontend
```

## File Safety

All files must stay under:

```text
WORK_DIR/jobs/{job_id}
```

Never accept arbitrary file paths.

## Admin Provisioning Security

MVP:
```text
Use install command, not stored VPS password.
```

Later:
```text
If password-based SSH is implemented, password is used once and discarded.
```

"""Canonical status enums — must match docs/specs/DATABASE_SCHEMA.md and CLAUDE.md.

Mirror these in packages/shared when that package is implemented.
"""

import enum


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class ApiKeyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class NodeStatus(str, enum.Enum):
    PROVISIONING = "PROVISIONING"
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class JobStatus(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED_NODE = "ASSIGNED_NODE"
    WAITING_UPLOAD = "WAITING_UPLOAD"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    EXTRACTING_AUDIO = "EXTRACTING_AUDIO"
    CHUNKING_AUDIO = "CHUNKING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSLATING = "TRANSLATING"
    GENERATING_SRT = "GENERATING_SRT"
    RENDERING = "RENDERING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

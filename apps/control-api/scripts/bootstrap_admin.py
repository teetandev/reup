"""Bootstrap script to safely create the first admin user and their secret key.

Usage (from apps/control-api/):
    python scripts/bootstrap_admin.py
"""

import os
import sys

# Ensure `app` is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _APP_ROOT)

from sqlalchemy import select

from app.config import get_settings
from app.db.enums import UserRole, UserStatus
from app.db.models import ApiKey, User
from app.db.session import SessionLocal, engine
from app.auth.keys import generate_secret_key, hash_key, key_prefix


def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        print("[ERROR] DATABASE_URL is not set in environment or .env file.")
        print("Set it using: $env:DATABASE_URL=\"postgresql://...\"")
        sys.exit(1)

    if engine is None:
        print("[ERROR] Failed to initialize database engine.")
        sys.exit(1)

    with SessionLocal() as db:
        # Check if an admin already exists
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))
        
        if admin is None:
            print("==> No admin user found. Creating 'Root Admin'...")
            admin = User(
                display_name="Root Admin",
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                max_file_mb=500,
                max_concurrent_jobs=5,
                daily_job_limit=100
            )
            db.add(admin)
            db.flush()  # to get admin.id
        else:
            print(f"==> Found existing admin user: {admin.display_name} (ID: {admin.id})")

        print("==> Generating new API Key...")
        plaintext_key = generate_secret_key()
        prefix = key_prefix(plaintext_key)
        hashed = hash_key(plaintext_key)

        api_key = ApiKey(
            user_id=admin.id,
            key_prefix=prefix,
            key_hash=hashed,
            name="Bootstrap Admin Key"
        )
        db.add(api_key)
        db.commit()

        print("\n" + "=" * 70)
        print(" SUCCESS! ADMIN USER AND KEY CONFIGURED")
        print("=" * 70)
        print("  Admin User ID :", admin.id)
        print("  Key Prefix    :", prefix)
        print("\n  [!!! CRITICAL WARNING !!!]")
        print("  Here is your plaintext secret key. It is NOT stored in the database.")
        print("  You will NEVER be able to see it again after you close this terminal.")
        print("\n  SECRET KEY:  ", plaintext_key)
        print("\n  Save it immediately to your password manager!")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    main()

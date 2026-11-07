"""Create the first institution and admin using environment variables, without demo data."""
import asyncio
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def bootstrap():
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal, engine
    from app.core.security import hash_password
    from app.application.schemas.auth import LoginRequest
    from app.infrastructure.models.models import Organization, Branch, User
    names = ("BOOTSTRAP_ORGANIZATION_NAME", "BOOTSTRAP_BRANCH_NAME", "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_PASSWORD")
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise SystemExit("Required environment variables: " + ", ".join(missing))
    values = {name: os.environ[name] for name in names}
    LoginRequest(email=values["BOOTSTRAP_ADMIN_EMAIL"], password=values["BOOTSTRAP_ADMIN_PASSWORD"])
    if len(values["BOOTSTRAP_ADMIN_PASSWORD"]) < 16:
        raise SystemExit("Initial admin password must have at least 16 characters")
    try:
        async with AsyncSessionLocal() as db:
            if (await db.execute(select(func.count()).select_from(User))).scalar_one() != 0:
                raise SystemExit("Bootstrap requires an empty installation; existing accounts will not be changed")
            org = Organization(name=values["BOOTSTRAP_ORGANIZATION_NAME"])
            db.add(org); await db.flush()
            branch = Branch(organization_id=org.id, name=values["BOOTSTRAP_BRANCH_NAME"])
            db.add(branch); await db.flush()
            db.add(User(organization_id=org.id, email=values["BOOTSTRAP_ADMIN_EMAIL"].lower(),
                first_name="Sistem", last_name="Yöneticisi", password_hash=hash_password(values["BOOTSTRAP_ADMIN_PASSWORD"]),
                is_super_admin=True, branches=[branch]))
            await db.commit()
            print("Initial institution, branch and admin created. No demo records were installed.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap())

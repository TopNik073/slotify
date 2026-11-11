"""
Create the first administrator, or promote an existing user.

There is no way to become an admin through the API by design, so a fresh installation needs
exactly one out-of-band step:

    uv run python -m src.scripts.create_admin --email you@example.com --password secret123
"""

import argparse
import asyncio
import sys

from argon2 import PasswordHasher

from src.core.config import config
from src.database.connection import AsyncSessionLocal
from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.database.repository import User
from src.database.repository import UserRepository


async def create_admin(email: str, password: str | None, full_name: str | None) -> str:
    async with AsyncSessionLocal() as session:
        users = UserRepository(session)
        existing = await users.get_by_email(email)

        password_hash = PasswordHasher().hash(password) if password else None

        if existing is not None:
            existing.role = UserRole.admin
            existing.status = UserStatus.active
            existing.full_name = full_name or existing.full_name

            # Keep the current password when none is given: this is also how an account that
            # only ever signed in with Google gets promoted without being handed a password.
            if password_hash is not None:
                existing.password_hash = password_hash

            await users.update(existing)
            await session.commit()

            return f'Promoted {email} to administrator'

        if password_hash is None:
            return 'A new account needs --password'

        await users.create(
            User(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=UserRole.admin,
                status=UserStatus.active,
            )
        )
        await session.commit()

        return f'Created administrator {email}'


def main() -> None:
    parser = argparse.ArgumentParser(description='Create or promote a Slotify administrator')
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', default=None, help='required for a new account')
    parser.add_argument('--name', default=None)
    arguments = parser.parse_args()

    if arguments.password is not None and len(arguments.password) < 6:  # noqa: PLR2004
        sys.exit('Password must be at least 6 characters long')

    try:
        result = asyncio.run(create_admin(arguments.email.strip().lower(), arguments.password, arguments.name))
    except OSError as exc:
        # The usual cause is the database not running, which does not deserve a traceback.
        sys.exit(f'Cannot reach the database at {config.DB_HOST}:{config.DB_PORT} ({exc})')

    print(result)  # noqa: T201


if __name__ == '__main__':
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiro_app import create_app
from chiro_app.db import get_db
from chiro_app.intake import iso_now


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a staff user for the local portal.")
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="clinician", choices=["clinician", "admin"])
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (args.email.lower(),)).fetchone()
        password_hash = generate_password_hash(args.password, method="pbkdf2:sha256")
        if existing is None:
            db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    args.first_name.strip(),
                    args.last_name.strip(),
                    args.email.lower().strip(),
                    password_hash,
                    args.role,
                    iso_now(),
                ),
            )
            action = "created"
        else:
            db.execute(
                """
                UPDATE users
                SET first_name = ?, last_name = ?, password_hash = ?, role = ?
                WHERE id = ?
                """,
                (
                    args.first_name.strip(),
                    args.last_name.strip(),
                    password_hash,
                    args.role,
                    existing["id"],
                ),
            )
            action = "updated"
        db.commit()

    print(f"Staff account {action}: {args.email.lower().strip()} ({args.role})")


if __name__ == "__main__":
    main()

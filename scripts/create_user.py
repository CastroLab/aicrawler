#!/usr/bin/env python3
"""Create a user account. Usage: python -m scripts.create_user <username> [--admin]"""
import argparse
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.hash import bcrypt

from app.database import SessionLocal, engine, Base
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="Create a user")
    parser.add_argument("username")
    parser.add_argument("--password", required=True)
    parser.add_argument("--display-name", default="")
    parser.add_argument("--admin", action="store_true")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = db.query(User).filter(User.username == args.username).first()
    if existing:
        print(f"User '{args.username}' already exists.")
        db.close()
        return

    user = User(
        username=args.username,
        password_hash=bcrypt.hash(args.password),
        display_name=args.display_name or args.username,
        role="admin" if args.admin else "member",
    )
    db.add(user)
    db.commit()
    print(f"Created {'admin' if args.admin else 'member'} user: {args.username}")
    db.close()


if __name__ == "__main__":
    main()

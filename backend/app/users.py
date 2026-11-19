"""Manage login accounts from the command line (run from the backend folder).

    python -m app.users list
    python -m app.users create-hr --email hr@company.com --name "Priya HR"
    python -m app.users set-password --email hr@company.com
    python -m app.users delete --email old@company.com

Passwords are always typed at a hidden prompt, never passed on the command line.
Candidates create their own accounts at /register in the app.
"""
import argparse
import getpass
import os
import sys

from . import settings
from .auth import create_user, hash_password
from .database import SessionLocal
from .main import migrate
from .models import User


def _ask_password() -> str:
    pw = getpass.getpass("New password (min 8 chars): ")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters.")
    if pw != getpass.getpass("Repeat password: "):
        sys.exit("Passwords did not match.")
    return pw


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.users", description="Manage MatchPoint login accounts.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list all accounts")
    c = sub.add_parser("create-hr", help="create an HR (recruiter) account")
    c.add_argument("--email", required=True)
    c.add_argument("--name", required=True)
    s = sub.add_parser("set-password", help="reset the password of any account")
    s.add_argument("--email", required=True)
    d = sub.add_parser("delete", help="delete an account (candidate profile and resume data are kept)")
    d.add_argument("--email", required=True)
    d.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = p.parse_args()

    migrate()
    with SessionLocal() as db:
        if args.cmd == "list":
            users = db.query(User).order_by(User.role, User.email).all()
            if not users:
                print("No accounts yet.")
            for u in users:
                print(f"{u.role:10} {u.email:38} {u.name}")
            return

        email = args.email.strip().lower()
        user = db.query(User).filter(User.email == email).first()

        if args.cmd == "create-hr":
            if user:
                sys.exit("An account with that email already exists.")
            create_user(db, email=email, name=args.name.strip(), password=_ask_password(), role="hr")
            print(f"HR account created for {email}. Sign in at /hr/login.")
            return

        if not user:
            sys.exit(f"No account with email {email}.")

        if args.cmd == "set-password":
            user.password_hash = hash_password(_ask_password())
            db.commit()
            print(f"Password updated for {email}.")
            return

        if args.cmd == "delete":
            if user.role == "hr" and db.query(User).filter(User.role == "hr").count() == 1:
                sys.exit("Refusing to delete the last HR account. Create another HR account first.")
            if not args.yes and input(f"Delete {user.role} account {email}? Type 'yes': ").strip().lower() != "yes":
                sys.exit("Cancelled.")
            db.delete(user)
            db.commit()
            print(f"Deleted account {email}.")
            if settings.SEED_DEMO and email.endswith(("@matchpoint.test", "rahul.kumar@example.com")):
                print("Note: demo mode is on, so demo accounts are re-created on the next start. Set SEED_DEMO=0 in backend/.env.")


if __name__ == "__main__":
    main()

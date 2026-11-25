import argparse
from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password

def main():
    parser = argparse.ArgumentParser(description="Create the first admin account.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--first-name", default="Clinic")
    parser.add_argument("--last-name", default="Administrator")
    args = parser.parse_args()
    if len(args.password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter((User.username == args.username) | (User.email == args.email)).first():
            raise SystemExit("That username or email is already registered.")
        user = User(role="admin", username=args.username, email=args.email,
                    hashed_password=hash_password(args.password),
                    first_name=args.first_name, last_name=args.last_name)
        db.add(user); db.commit()
        print(f"Administrator '{args.username}' created.")
    finally:
        db.close()

if __name__ == "__main__":
    main()

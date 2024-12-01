# import logging
# from sqlalchemy.orm import Session
# from app.core.config import settings
# from app.core.security import get_password_hash
# from app.models.user import User
# from app.core.database import SessionLocal

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def init_db(db: Session) -> None:
#     """Initial database setup."""
#     user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
#     if not user:
#         user = User(
#             email=settings.FIRST_SUPERUSER,
#             hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
#             full_name="Initial Super User",
#             is_superuser=True,
#         )
#         db.add(user)
#         db.commit()
#         logger.info("Created first superuser")

# def main() -> None:
#     logger.info("Creating initial data")
#     db = SessionLocal()
#     init_db(db)
#     logger.info("Initial data created")

# if __name__ == "__main__":
#     main()
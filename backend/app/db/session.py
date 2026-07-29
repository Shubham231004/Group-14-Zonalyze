from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL, DEBUG

# echo is driven by DEBUG (default off) so SQL statements and their parameter
# values are not logged to the console in normal operation.
engine = create_engine(DATABASE_URL, echo=DEBUG)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
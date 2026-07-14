from sqlalchemy import create_engine,Column,Integer,String,JSON
from sqlalchemy.orm import sessionmaker,declarative_base
#  Define the SQLite database file path
SQLALCHEMY_DATABASE_URL="sqlite:////app/data/briefings.db"
# Create the engine (the core interface to the database)
# The check_same_thread=False argument is required for SQLite in FastAPI
engine=create_engine(SQLALCHEMY_DATABASE_URL,connect_args={"check_same_thread":False})
# Create a Session factory
SessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)
# Create the Base class for our models
Base = declarative_base()
# Define our Data Model (The Database Table)
class BriefingCache(Base):
    __tablename__ = "briefing_cache"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    time = Column(String, index=True)
    attendees = Column(JSON)      # SQLite supports JSON columns via SQLAlchemy
    ai_briefing = Column(String)  # The actual markdown text

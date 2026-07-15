import os
from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# 1. Dynamically pull the Render DB URL, fallback to your original local SQLite path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/briefings.db")

# 2. Fix Render's legacy Postgres prefix for modern SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Configure the engine dynamically based on the dialect
if DATABASE_URL.startswith("sqlite"):
    # SQLite requires this for local FastAPI multithreading
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Production PostgreSQL connection
    engine = create_engine(DATABASE_URL)

# Create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the Base class for our models
Base = declarative_base()

# ---------------------------------------------------------
# NEW: User Model for Multi-Tenant OAuth
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True)
    
    # OAuth Credentials stored securely per user
    access_token = Column(String)
    refresh_token = Column(String)
    token_expiry = Column(DateTime)
    
    # Establishes a one-to-many relationship with BriefingCache
    briefings = relationship("BriefingCache", back_populates="owner", cascade="all, delete-orphan")

# ---------------------------------------------------------
# UPDATED: Cache Model Linked to Users
# ---------------------------------------------------------
class BriefingCache(Base):
    __tablename__ = "briefing_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # The Tenant ID link
    title = Column(String, index=True)
    time = Column(String, index=True)
    attendees = Column(JSON)      
    ai_briefing = Column(String)  
    
    # Establishes the reverse relationship back to the User
    owner = relationship("User", back_populates="briefings")
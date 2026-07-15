from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# Define the database file path
SQLALCHEMY_DATABASE_URL = "sqlite:////app/data/briefings.db"

# Create the engine. The check_same_thread=False argument is required for SQLite in FastAPI
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

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
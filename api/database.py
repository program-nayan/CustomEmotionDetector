"""
Database setup for the Emotion Wellness Assistant.
Uses SQLite for simplicity. All user data is stored locally.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone

DATABASE_URL = "sqlite:///./wellness_assistant.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    mood_logs = relationship("MoodLog", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_title = Column(String, default="Evening Check-in")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    mood_log = relationship("MoodLog", back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Emotion scores stored as JSON string
    dominant_emotion = Column(String, nullable=True)
    emotion_confidence = Column(Float, nullable=True)
    neutral_score = Column(Float, nullable=True)
    anger_score = Column(Float, nullable=True)
    disgust_score = Column(Float, nullable=True)
    fear_score = Column(Float, nullable=True)
    happiness_score = Column(Float, nullable=True)
    sadness_score = Column(Float, nullable=True)
    surprise_score = Column(Float, nullable=True)

    session = relationship("ChatSession", back_populates="messages")


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Aggregated emotion scores for the session
    dominant_emotion = Column(String, nullable=True)
    neutral_score = Column(Float, default=0.0)
    anger_score = Column(Float, default=0.0)
    disgust_score = Column(Float, default=0.0)
    fear_score = Column(Float, default=0.0)
    happiness_score = Column(Float, default=0.0)
    sadness_score = Column(Float, default=0.0)
    surprise_score = Column(Float, default=0.0)

    # Wellness suggestions given
    wellness_suggestion = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="mood_logs")
    session = relationship("ChatSession", back_populates="mood_log")


from api.core.logger import logger

def create_db_tables():
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    email: Optional[str] = None
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    is_anonymous: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    content: str
    session_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime
    dominant_emotion: Optional[str]
    emotion_confidence: Optional[float]

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    message: str
    session_id: int
    emotion_scores: Dict[str, float]
    dominant_emotion: str
    wellness_tip: Optional[str]
    crisis_alert: bool = False
    message_id: int


class SessionOut(BaseModel):
    id: int
    session_title: str
    started_at: datetime
    ended_at: Optional[datetime]
    summary: Optional[str]

    class Config:
        from_attributes = True


class SessionDetail(SessionOut):
    messages: List[MessageOut]

    class Config:
        from_attributes = True


# ─── Dashboard ───────────────────────────────────────────────────────────────

class MoodLogOut(BaseModel):
    id: int
    logged_at: datetime
    dominant_emotion: Optional[str]
    neutral_score: float
    anger_score: float
    disgust_score: float
    fear_score: float
    happiness_score: float
    sadness_score: float
    surprise_score: float
    wellness_suggestion: Optional[str]

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    dominant_emotion: Optional[str] = None

    class Config:
        from_attributes = True


class DailyDashboard(BaseModel):
    date: str
    total_messages: int
    dominant_emotion: str
    emotion_breakdown: Dict[str, float]
    session_count: int
    wellness_tips: List[str]
    mood_trend: str   # "improving", "stable", "declining"
    sessions: List[SessionSummary]


class WeeklyDashboard(BaseModel):
    week_start: str
    week_end: str
    daily_summaries: List[Dict]
    overall_dominant_emotion: str
    emotion_averages: Dict[str, float]
    mood_trend: str
    total_sessions: int
    insights: List[str]

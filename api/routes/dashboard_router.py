"""
FastAPI router: Dashboard endpoints — daily and weekly emotional analytics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone, date
from typing import List, Dict
from collections import defaultdict

from api.database import get_db, MoodLog, Message, ChatSession, User
from api.schemas import DailyDashboard, WeeklyDashboard, MoodLogOut
from api.auth import get_required_user
from api.wellness import compute_mood_trend, generate_weekly_insights, EMO_MAP
from api.core.logger import logger

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

EMOTION_FIELDS = ["neutral", "anger", "disgust", "fear", "happiness", "sadness", "surprise"]


def _get_emotion_scores_from_log(log: MoodLog) -> Dict[str, float]:
    return {
        "neutral": log.neutral_score or 0.0,
        "anger": log.anger_score or 0.0,
        "disgust": log.disgust_score or 0.0,
        "fear": log.fear_score or 0.0,
        "happiness": log.happiness_score or 0.0,
        "sadness": log.sadness_score or 0.0,
        "surprise": log.surprise_score or 0.0,
    }


# ─── Daily Dashboard ──────────────────────────────────────────────────────────

@router.get("/daily", response_model=DailyDashboard)
def daily_dashboard(
    target_date: str = None,  # YYYY-MM-DD, defaults to today
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Get the daily emotional summary dashboard."""
    if target_date:
        try:
            day = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        day = datetime.now().date()

    day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    # Get all user messages for the day
    messages = db.query(Message).join(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        Message.role == "user",
        Message.timestamp >= day_start,
        Message.timestamp < day_end,
        Message.dominant_emotion.isnot(None)
    ).all()

    # Get sessions for the day
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.started_at >= day_start,
        ChatSession.started_at < day_end
    ).all()

    if not messages:
        logger.debug(f"Daily dashboard: No messages found for user {current_user.id} on {day}")
        return DailyDashboard(
            date=str(day),
            total_messages=0,
            dominant_emotion="neutral",
            emotion_breakdown={e: 0.0 for e in EMOTION_FIELDS},
            session_count=len(sessions),
            wellness_tips=[],
            mood_trend="stable",
            sessions=[
                {
                    "id": s.id,
                    "title": s.session_title,
                    "summary": s.summary,
                    "dominant_emotion": "neutral"
                } for s in sessions
            ]
        )

    # Aggregate emotion scores
    totals = defaultdict(float)
    for msg in messages:
        totals["neutral"] += msg.neutral_score or 0.0
        totals["anger"] += msg.anger_score or 0.0
        totals["disgust"] += msg.disgust_score or 0.0
        totals["fear"] += msg.fear_score or 0.0
        totals["happiness"] += msg.happiness_score or 0.0
        totals["sadness"] += msg.sadness_score or 0.0
        totals["surprise"] += msg.surprise_score or 0.0

    n = len(messages)
    emotion_breakdown = {k: round(v / n, 4) for k, v in totals.items()}
    dominant_emotion = max(emotion_breakdown, key=emotion_breakdown.get)

    # Mood trend from the day's emotion sequence
    emotion_sequence = [m.dominant_emotion for m in messages if m.dominant_emotion]
    mood_trend = compute_mood_trend(emotion_sequence)

    # Collect wellness tips from mood logs
    logs = db.query(MoodLog).filter(
        MoodLog.user_id == current_user.id,
        MoodLog.logged_at >= day_start,
        MoodLog.logged_at < day_end
    ).all()
    wellness_tips = list({log.wellness_suggestion for log in logs if log.wellness_suggestion})

    # Get sessions for the day with their summaries and dominant emotions
    sessions_data = []
    for s in sessions:
        # Get the dominant emotion for this specific session from MoodLog
        ml = db.query(MoodLog).filter(MoodLog.session_id == s.id).first()
        sessions_data.append({
            "id": s.id,
            "title": s.session_title,
            "summary": s.summary,
            "dominant_emotion": ml.dominant_emotion if ml else "neutral"
        })

    logger.info(f"Daily dashboard generated for user {current_user.id} on {day}")
    return DailyDashboard(
        date=str(day),
        total_messages=n,
        dominant_emotion=dominant_emotion,
        emotion_breakdown=emotion_breakdown,
        session_count=len(sessions),
        wellness_tips=wellness_tips[:3],
        mood_trend=mood_trend,
        sessions=sessions_data
    )


# ─── Weekly Dashboard ─────────────────────────────────────────────────────────

@router.get("/weekly", response_model=WeeklyDashboard)
def weekly_dashboard(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Get the weekly emotional trend dashboard."""
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)              # Sunday

    start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Get all user messages for the week
    messages = db.query(Message).join(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        Message.role == "user",
        Message.timestamp >= start_dt,
        Message.timestamp <= end_dt,
        Message.dominant_emotion.isnot(None)
    ).order_by(Message.timestamp).all()

    # Get sessions for the week
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.started_at >= start_dt,
        ChatSession.started_at <= end_dt,
    ).all()

    # Group by day for daily summaries
    daily_data: Dict[str, List] = defaultdict(list)
    for msg in messages:
        day_key = msg.timestamp.date().strftime("%Y-%m-%d")
        daily_data[day_key].append(msg)

    daily_summaries = []
    all_emotion_sequences = []
    week_totals = defaultdict(float)
    total_msg_count = 0

    for day_key in sorted(daily_data.keys()):
        day_msgs = daily_data[day_key]
        day_totals = defaultdict(float)
        for msg in day_msgs:
            for field in EMOTION_FIELDS:
                day_totals[field] += getattr(msg, f"{field}_score", 0.0) or 0.0
                week_totals[field] += getattr(msg, f"{field}_score", 0.0) or 0.0
        n = len(day_msgs)
        total_msg_count += n
        day_breakdown = {k: round(v / n, 4) for k, v in day_totals.items()}
        dominant = max(day_breakdown, key=day_breakdown.get)
        all_emotion_sequences.append(dominant)
        daily_summaries.append({
            "date": day_key,
            "message_count": n,
            "dominant_emotion": dominant,
            "emotion_breakdown": day_breakdown,
        })

    # Overall week averages
    if total_msg_count > 0:
        emotion_averages = {k: round(v / total_msg_count, 4) for k, v in week_totals.items()}
    else:
        emotion_averages = {e: 0.0 for e in EMOTION_FIELDS}

    overall_dominant = max(emotion_averages, key=emotion_averages.get) if emotion_averages else "neutral"
    mood_trend = compute_mood_trend(all_emotion_sequences)
    insights = generate_weekly_insights(emotion_averages, mood_trend)

    return WeeklyDashboard(
        week_start=str(week_start),
        week_end=str(week_end),
        daily_summaries=daily_summaries,
        overall_dominant_emotion=overall_dominant,
        emotion_averages=emotion_averages,
        mood_trend=mood_trend,
        total_sessions=len(sessions),
        insights=insights
    )


@router.get("/mood-history", response_model=List[MoodLogOut])
def mood_history(
    days: int = 30,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Get the last N days of mood logs (aggregated by session)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    logs = db.query(MoodLog).filter(
        MoodLog.user_id == current_user.id,
        MoodLog.logged_at >= cutoff
    ).order_by(MoodLog.logged_at.desc()).all()
    return logs


@router.get("/timeline")
def get_daily_timeline(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Get turn-by-turn emotion scores for all user messages today."""
    today = datetime.now(timezone.utc).date()
    start_dt = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    messages = db.query(Message).join(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        Message.role == "user",
        Message.timestamp >= start_dt,
        Message.dominant_emotion.isnot(None)
    ).order_by(Message.timestamp.asc()).all()
    
    return [{
        "timestamp": m.timestamp,
        "happiness_score": m.happiness_score or 0.0,
        "sadness_score": m.sadness_score or 0.0,
        "dominant_emotion": m.dominant_emotion
    } for m in messages]

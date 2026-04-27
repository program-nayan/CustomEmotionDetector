"""
FastAPI router: Chat endpoints — message sending, session management.
Uses FusionPredictor for emotion detection, Gemini for empathetic responses.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from api.database import get_db, ChatSession, Message, MoodLog, User
from api.schemas import ChatMessage, ChatResponse, SessionOut, SessionDetail, MessageOut
from api.auth import get_current_user, get_required_user
from api.wellness import (
    detect_crisis, get_dominant_emotion, get_wellness_tip,
    normalize_scores, CRISIS_RESOURCES
)
from api.chatbot import WellnessChatbot

# Import the fusion predictor from the existing codebase (no changes to logic)
from src.predictor.fusion_prediction_engine import FusionPredictor
from api.core.logger import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Module-level singletons (loaded once at startup)
_fusion_predictor: Optional[FusionPredictor] = None
_chatbot: Optional[WellnessChatbot] = None


def get_fusion_predictor() -> FusionPredictor:
    global _fusion_predictor
    if _fusion_predictor is None:
        _fusion_predictor = FusionPredictor()
    return _fusion_predictor


def get_chatbot() -> WellnessChatbot:
    global _chatbot
    if _chatbot is None:
        _chatbot = WellnessChatbot()
    return _chatbot


def _save_mood_log(db: Session, user_id: int, session_id: int, emotion_scores: dict, dominant: str, tip: str):
    """Background task to aggregate and save session mood log."""
    existing = db.query(MoodLog).filter(MoodLog.session_id == session_id).first()
    scores = emotion_scores

    if existing:
        # Rolling average update
        for key in ["neutral", "anger", "disgust", "fear", "happiness", "sadness", "surprise"]:
            old_val = getattr(existing, f"{key}_score", 0.0)
            new_val = scores.get(key, 0.0)
            setattr(existing, f"{key}_score", round((old_val + new_val) / 2, 4))
        existing.dominant_emotion = dominant
        existing.wellness_suggestion = tip
    else:
        log = MoodLog(
            user_id=user_id,
            session_id=session_id,
            dominant_emotion=dominant,
            neutral_score=scores.get("neutral", 0.0),
            anger_score=scores.get("anger", 0.0),
            disgust_score=scores.get("disgust", 0.0),
            fear_score=scores.get("fear", 0.0),
            happiness_score=scores.get("happiness", 0.0),
            sadness_score=scores.get("sadness", 0.0),
            surprise_score=scores.get("surprise", 0.0),
            wellness_suggestion=tip,
        )
        db.add(log)

    db.commit()


# ─── Session Management ───────────────────────────────────────────────────────

@router.post("/session/start", response_model=SessionOut, status_code=201)
def start_session(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Start a new evening check-in session."""
    session = ChatSession(
        user_id=current_user.id,
        session_title=f"Evening Check-in — {datetime.now().strftime('%B %d, %Y')}"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"New session started: ID {session.id} for user {current_user.username}")
    return session


@router.post("/session/{session_id}/end", response_model=SessionOut)
def end_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """End a session and generate a summary."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.now(timezone.utc)

    # Generate session summary
    msgs = db.query(Message).filter(Message.session_id == session_id).all()
    history = [{"role": m.role, "content": m.content} for m in msgs]
    chatbot = get_chatbot()
    session.summary = chatbot.generate_session_summary(history)

    db.commit()
    db.refresh(session)
    logger.info(f"Session ended: ID {session_id} for user {current_user.username}")
    return session


@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.started_at.desc()).limit(30).all()
    return sessions


@router.get("/session/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/session/{session_id}")
def delete_session(
    session_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Delete a session and its associated messages."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Associated messages and mood logs will be deleted if cascade is set, 
    # but let's be explicit if needed. 
    # In api/database.py, we should check cascade settings.
    db.delete(session)
    db.commit()
    return {"status": "success", "message": "Session deleted"}


# ─── Messaging ────────────────────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
def send_message(
    payload: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """
    Process a user message:
    1. Detect emotion via FusionPredictor
    2. Generate empathetic Gemini response
    3. Check for crisis signals
    4. Return response with wellness tip
    """
    logger.info(f"Message received from user {current_user.username}: {payload.content[:50]}...")
    # ── 1. Get or create session ──────────────────────────────────────────────
    session_id = payload.session_id
    if session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(
            user_id=current_user.id,
            session_title=f"Evening Check-in — {datetime.now().strftime('%B %d, %Y')}"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ── 2. Load conversation history for context ──────────────────────────────
    history_msgs = db.query(Message).filter(
        Message.session_id == session.id
    ).order_by(Message.timestamp).all()
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    # Build context string (last 3 user messages as context for RoBERTa)
    recent_context = " ".join(
        m.content for m in history_msgs[-3:] if m.role == "user"
    )

    # ── 3. Run Fusion Prediction ──────────────────────────────────────────────
    try:
        predictor = get_fusion_predictor()
        raw_emo_scores, raw_act_scores = predictor.fuse_scores(
            text=payload.content,
            context=recent_context
        )
        emotion_scores = normalize_scores(raw_emo_scores)
        dominant_emotion, confidence = get_dominant_emotion(emotion_scores)
        logger.debug(f"Emotion detected: {dominant_emotion} (conf: {confidence:.2f})")
    except Exception as e:
        logger.error(f"Fusion predictor error: {e}", exc_info=True)
        emotion_scores = {
            "neutral": 1.0, "anger": 0.0, "disgust": 0.0,
            "fear": 0.0, "happiness": 0.0, "sadness": 0.0, "surprise": 0.0
        }
        dominant_emotion, confidence = "neutral", 1.0

    # ── 4. Crisis detection ───────────────────────────────────────────────────
    is_crisis = detect_crisis(payload.content)
    if is_crisis:
        logger.warning(f"CRISIS DETECTED for user {current_user.username}: {payload.content}")

    # ── 5. Wellness tip ───────────────────────────────────────────────────────
    wellness_tip = get_wellness_tip(dominant_emotion)

    # ── 6. Generate chatbot response ──────────────────────────────────────────
    chatbot = get_chatbot()
    bot_response = chatbot.generate_response(
        history=history,
        new_user_message=payload.content,
        detected_emotion=dominant_emotion,
        wellness_tip=wellness_tip,
        is_crisis=is_crisis,
    )

    if is_crisis:
        bot_response = bot_response + "\n\n" + CRISIS_RESOURCES

    # ── 7. Persist user message ───────────────────────────────────────────────
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=payload.content,
        dominant_emotion=dominant_emotion,
        emotion_confidence=round(confidence, 4),
        neutral_score=emotion_scores.get("neutral", 0.0),
        anger_score=emotion_scores.get("anger", 0.0),
        disgust_score=emotion_scores.get("disgust", 0.0),
        fear_score=emotion_scores.get("fear", 0.0),
        happiness_score=emotion_scores.get("happiness", 0.0),
        sadness_score=emotion_scores.get("sadness", 0.0),
        surprise_score=emotion_scores.get("surprise", 0.0),
    )
    db.add(user_msg)

    # ── 8. Persist assistant message ──────────────────────────────────────────
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=bot_response,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # ── 9. Background: update mood log ───────────────────────────────────────
    background_tasks.add_task(
        _save_mood_log, db, current_user.id, session.id,
        emotion_scores, dominant_emotion, wellness_tip
    )

    return ChatResponse(
        message=bot_response,
        session_id=session.id,
        emotion_scores=emotion_scores,
        dominant_emotion=dominant_emotion,
        wellness_tip=wellness_tip,
        crisis_alert=is_crisis,
        message_id=assistant_msg.id,
    )


@router.get("/opening/{session_id}")
def get_opening_message(
    session_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Get the opening check-in message for a new session."""
    chatbot = get_chatbot()
    opening = chatbot.get_opening_message(
        username=current_user.username if not current_user.is_anonymous else "friend"
    )
    return {"message": opening, "session_id": session_id}

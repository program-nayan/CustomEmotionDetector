"""
Wellness engine: maps detected emotions to CBT/DBT-informed interventions,
crisis detection, and wellness suggestions.
"""

from typing import Dict, List, Tuple, Optional

EMO_MAP = {0: "neutral", 1: "anger", 2: "disgust", 3: "fear", 4: "happiness", 5: "sadness", 6: "surprise"}

# ─── Wellness Interventions ───────────────────────────────────────────────────

WELLNESS_INTERVENTIONS = {
    "neutral": [
        "Try a 5-minute mindful body scan to deepen your awareness of the present moment.",
        "Consider journaling 3 things you're grateful for today.",
        "A short walk in nature can help maintain your balanced state.",
    ],
    "anger": [
        "Try the 4-7-8 breathing technique: inhale for 4s, hold for 7s, exhale for 8s.",
        "CBT tip: Challenge the thought driving your anger — is it a fact or an assumption?",
        "Progressive muscle relaxation: tense and release each muscle group for 5 seconds.",
        "Write down what triggered this feeling, then reframe it from a different perspective.",
    ],
    "disgust": [
        "Practice the DBT 'Opposite Action' skill: do something kind when feeling repelled.",
        "Grounding exercise: name 5 things you can see, 4 you can touch, 3 you can hear.",
        "Consider whether this feeling is about a boundary being crossed — validate that.",
    ],
    "fear": [
        "Box breathing: inhale 4s, hold 4s, exhale 4s, hold 4s. Repeat 4 times.",
        "CBT: Identify the worst-case scenario, then ask — how likely is it, really?",
        "Try the 5-4-3-2-1 grounding technique to anchor yourself in the present.",
        "Write down your fear and break it into small, manageable steps.",
    ],
    "happiness": [
        "Savor this moment! Write down what made you feel this way to remember it.",
        "Share your joy — reach out to someone you care about.",
        "Use this positive energy to tackle something you've been putting off.",
        "Practice gratitude journaling to amplify and sustain this positive state.",
    ],
    "sadness": [
        "Be gentle with yourself. Practice self-compassion — speak to yourself like a friend.",
        "DBT TIPP skill: Temperature, Intense exercise, Paced breathing, Progressive relaxation.",
        "Allow yourself to feel this. Write freely in a journal for 10 minutes.",
        "Reach out to someone you trust. Connection is a powerful antidote to sadness.",
    ],
    "surprise": [
        "Take a moment to process. Deep breathing helps your nervous system settle.",
        "Journal about what surprised you — is it pleasant or unsettling?",
        "Give yourself permission to sit with uncertainty for a moment before reacting.",
    ],
}

# ─── Crisis Keywords ──────────────────────────────────────────────────────────

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "don't want to live",
    "want to die", "self harm", "hurt myself", "no reason to live",
    "can't go on", "better off dead", "hopeless", "worthless",
    "can't take it anymore", "give up on life", "end it all",
]

CRISIS_RESOURCES = """
🆘 **You're not alone. Please reach out:**
- **iCall (India):** 9152987821
- **Vandrevala Foundation:** 1860-2662-345 (24/7)
- **Crisis Text Line:** Text HOME to 741741
- **International Association for Suicide Prevention:** https://www.iasp.info/resources/Crisis_Centres/

A trained counselor is ready to listen right now. You matter. 💙
"""


def detect_crisis(text: str) -> bool:
    """Check if the text contains crisis signals."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in CRISIS_KEYWORDS)


def get_dominant_emotion(emotion_scores: Dict) -> Tuple[str, float]:
    """Return (emotion_name, confidence) for the highest-scoring emotion."""
    best_key = max(emotion_scores, key=emotion_scores.get)
    # Handle both int and string keys
    if isinstance(best_key, int):
        name = EMO_MAP.get(best_key, "neutral")
    else:
        name = str(best_key)
    return name, emotion_scores[best_key]


def get_wellness_tip(emotion: str) -> str:
    """Return a single wellness tip for the given emotion."""
    import random
    tips = WELLNESS_INTERVENTIONS.get(emotion, WELLNESS_INTERVENTIONS["neutral"])
    return random.choice(tips)


def compute_mood_trend(recent_emotions: List[str]) -> str:
    """
    Compute a simple mood trend from a list of recent dominant emotions.
    Returns 'improving', 'stable', or 'declining'.
    """
    positive = {"happiness", "surprise"}
    negative = {"anger", "disgust", "fear", "sadness"}

    if len(recent_emotions) < 2:
        return "stable"

    half = len(recent_emotions) // 2
    earlier = recent_emotions[:half]
    later = recent_emotions[half:]

    def valence(emos):
        pos = sum(1 for e in emos if e in positive)
        neg = sum(1 for e in emos if e in negative)
        return pos - neg

    earlier_v = valence(earlier)
    later_v = valence(later)

    if later_v > earlier_v:
        return "improving"
    elif later_v < earlier_v:
        return "declining"
    return "stable"


def normalize_scores(raw_scores: Dict) -> Dict[str, float]:
    """Normalize fusion engine scores to string-keyed dict with friendly labels."""
    result = {}
    for key, val in raw_scores.items():
        if isinstance(key, int):
            label = EMO_MAP.get(key, str(key))
        else:
            label = str(key)
        result[label] = round(float(val), 4)
    return result


def generate_weekly_insights(emotion_averages: Dict[str, float], trend: str) -> List[str]:
    """Generate textual insights for the weekly dashboard."""
    insights = []
    dominant = max(emotion_averages, key=emotion_averages.get)

    if dominant == "sadness":
        insights.append("You've been carrying a heavy emotional load this week. Consider scheduling time for rest and self-care.")
    elif dominant == "happiness":
        insights.append("What a positive week! Reflect on what brought you joy — replicate those conditions.")
    elif dominant == "anger":
        insights.append("Frustration has been a theme this week. Identifying recurring triggers could help you plan responses.")
    elif dominant == "fear":
        insights.append("Anxiety seems present. Breaking big worries into small, actionable steps may help.")
    elif dominant == "neutral":
        insights.append("Your emotional baseline has been steady. Mindfulness can help you stay tuned in.")
    else:
        insights.append(f"Your dominant emotion this week was {dominant}. Journaling about patterns might reveal useful insights.")

    if trend == "improving":
        insights.append("Your mood has been trending upward — keep doing what's working! 🌱")
    elif trend == "declining":
        insights.append("Your mood has dipped this week. Be gentle with yourself and consider reaching out for support.")
    else:
        insights.append("Your emotional state has been stable — consistency is a strength.")

    return insights

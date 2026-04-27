"""
Chatbot engine: Gemini-powered empathetic end-of-day emotional assistant.
Wraps the FusionPredictor for emotion detection and Gemini for natural conversation.
"""

import os
import re
import ast
import json
from dotenv import load_dotenv
from google import genai
from typing import List, Dict, Optional, Tuple

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHAT_MODEL = "models/gemma-3-27b-it"

# Conversation flow questions for guided end-of-day check-in
CHECKIN_FLOW = [
    "How was your day overall? I'm here to listen — take your time. 🌙",
    "What was the highlight of your day? Even small wins count. ✨",
    "Was there anything that felt difficult or weighed on you today?",
    "How are you feeling in your body right now — any tension, fatigue, or restlessness?",
    "Is there anything else on your mind that you'd like to talk about or let go of before we wrap up?",
]

SYSTEM_PROMPT = """You are Serenity, a world-class, empathetic wellness companion with a PhD-level grasp of emotional intelligence and therapeutic communication. 

Your mission: Transform a simple evening check-in into a profound moment of self-reflection.

CORE PHILOSOPHY:
1. **Validation First**: Always acknowledge the user's emotional state with depth. Don't just say "I understand." Reflect back the nuance of what they shared.
2. **Dynamic Adaptation**: Use the [DETECTED EMOTION] tags to shift your entire persona. If it's SURPRISE, be curious. If it's FEAR, be a calming anchor.
3. **The "Coping + Connection" Rule**: When distress is high, suggest ONE specific, low-friction wellness technique (box breathing, 5-4-3-2-1, cognitive reframing) AND immediately follow it with a question that bridges back to their story.
4. **Contextual Continuity**: Reference specific details from earlier in the session to build a narrative of being truly "present" with them.

CONVERSATION STYLE:
- Tone: Soothing, poetic but grounded, warm, and highly observant.
- Length: Concise (2-4 sentences). Depth over volume.
- Emojis: Use sparingly as emotional punctuation (e.g., 🌱 to signify growth, 🌊 for calm).

SAFETY PROTOCOL:
- Never diagnose. If crisis signals are high, stay calm, validate, and prioritize the crisis resources provided in the UI.
- Gently redirect non-wellness topics back to the user's internal world."""


class WellnessChatbot:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def build_conversation_context(
        self,
        history: List[Dict],
        new_user_message: str,
        detected_emotion: Optional[str] = None,
        wellness_tip: Optional[str] = None,
        is_crisis: bool = False,
    ) -> List[Dict]:
        """Build the message list for Gemma multi-turn conversation."""
        messages = []

        # Gemma 3 27B doesn't support system_instruction/developer_instruction.
        # We prepend the system prompt to the very first user message or as a separate user message.
        # Here we'll start with a system message role if possible, or just a user message with instructions.
        
        system_context = f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\n---"
        
        # Add conversation history (last 12 messages)
        # If history is empty, the first message will carry the system context
        processed_history = history[-12:]
        
        for i, msg in enumerate(processed_history):
            content = msg["content"]
            if i == 0:
                content = f"{system_context}\n\n{content}"
            
            # Map role names: Gemini SDK expects 'user' and 'model'
            role = "model" if msg["role"] == "assistant" else "user"
            
            messages.append({
                "role": role,
                "parts": [{"text": content}]
            })

        # Enrich current user message
        enriched_message = new_user_message
        if detected_emotion and detected_emotion != "neutral":
            enriched_message = f"[DETECTED EMOTION: {detected_emotion.upper()}]\n{new_user_message}"

        if is_crisis:
            enriched_message = f"[⚠️ CRISIS SIGNALS DETECTED — RESPOND WITH MAXIMUM EMPATHY AND URGENCY]\n{new_user_message}"

        # If no history, this is the first message; attach system context
        if not messages:
            enriched_message = f"{system_context}\n\n{enriched_message}"

        messages.append({
            "role": "user",
            "parts": [{"text": enriched_message}]
        })

        return messages

    def get_opening_message(self, username: str = "friend") -> str:
        """Generate personalized opening message for a new session."""
        hour = __import__("datetime").datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
            time_context = "starting your day"
        elif hour < 17:
            greeting = "Good afternoon"
            time_context = "checking in midday"
        else:
            greeting = "Good evening"
            time_context = "winding down for the evening"

        return (
            f"{greeting}, {username}! 🌙 I'm Serenity, your wellness companion. "
            f"I'm glad you're {time_context} with me. "
            f"This is your safe space — no judgment, just honest reflection. "
            f"\n\n{CHECKIN_FLOW[0]}"
        )

    def generate_response(
        self,
        history: List[Dict],
        new_user_message: str,
        detected_emotion: Optional[str] = None,
        wellness_tip: Optional[str] = None,
        is_crisis: bool = False,
    ) -> str:
        """Generate an empathetic response using Gemma 3 27B."""
        messages = self.build_conversation_context(
            history, new_user_message, detected_emotion, wellness_tip, is_crisis
        )

        from api.core.logger import logger
        try:
            logger.debug(f"Generating Gemma response for model: {CHAT_MODEL}")
            response = self.client.models.generate_content(
                model=CHAT_MODEL,
                contents=messages,
                config={
                    "temperature": 0.75,
                    "max_output_tokens": 500,
                }
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemma chat error: {e}", exc_info=True)
            return (
                "I'm here with you. Sometimes words are hard to find — that's okay. "
                "Take a breath, and share whatever feels right. 💙"
            )

    def generate_session_summary(self, messages: List[Dict]) -> str:
        """Generate a brief summary of the session's emotional journey."""
        if not messages:
            return "A quiet evening check-in."

        conversation_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}"
            for m in messages[-20:]  # last 20 messages
        )

        summary_prompt = f"""Based on this wellness conversation, write a brief, warm 2-3 sentence summary 
        of the user's emotional state and what was discussed. Focus on what they shared about their day 
        and any emotional themes that emerged. Be empathetic and non-clinical.
        
        Conversation:
        {conversation_text}
        
        Summary:"""

        try:
            response = self.client.models.generate_content(
                model=CHAT_MODEL,
                contents=summary_prompt,
            )
            return response.text.strip()
        except Exception as e:
            return "A meaningful evening check-in session."

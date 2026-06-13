"""
models.py — Pydantic Models for Healthians AI
Request/response validation and type safety.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """A single chat message (user or assistant)."""
    role: Literal["user", "assistant"]
    content: str


class ReportExplanation(BaseModel):
    """Structured breakdown of a lab test result."""
    test_name: str
    value: float
    unit: str
    reference_range: str
    status: Literal["normal", "low", "high", "borderline", "critical"]
    explanation: str
    recommendation: str
    disclaimer: str = "This is for informational purposes only. Please consult your doctor for medical advice."


class AppointmentDetails(BaseModel):
    """Confirmation details for a booked appointment."""
    booking_id: str
    patient_name: str
    phone: str
    city: str
    date: str
    test_or_package: str
    status: Literal["confirmed", "pending", "failed"]
    message: str


class EscalationDetails(BaseModel):
    """Details when a case is escalated to a doctor."""
    ticket_id: str
    patient_name: str
    phone: str
    reason: str
    priority: Literal["normal", "urgent", "emergency"]
    estimated_callback: str
    message: str


# ---------------------------------------------------------------------------
# API Request / Response
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming request from the user / frontend."""
    user_message: str = Field(..., min_length=1, max_length=2000, description="User's chat message")
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    phone_number: Optional[str] = Field(None, pattern=r"^\d{10}$", description="10-digit Indian mobile number")
    language: Literal["en", "hi", "auto"] = Field("auto", description="Preferred response language")


class ChatResponse(BaseModel):
    """Outgoing response to the user / frontend."""
    reply: str = Field(..., description="User-friendly response text")
    intent: str = Field(
        "general_chat",
        description="Detected intent: explain_report | book_appointment | fetch_reports | answer_faq | escalate_to_doctor | test_suggestion | general_chat",
    )
    data: Optional[dict[str, Any]] = Field(None, description="Structured data (report explanation, booking details, etc.)")
    suggested_followups: list[str] = Field(default_factory=list, description="Suggested next questions for the user")
    session_id: str = Field(..., description="Session identifier echoed back")

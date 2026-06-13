"""
tools.py — Mock Functions for Healthians AI (Async SQLAlchemy)
"""

from __future__ import annotations

import random
import string
from datetime import datetime
import json
from sqlalchemy.future import select

from config import settings
from langchain_core.tools import tool
from database import AsyncSessionLocal, ReferenceRange, City, Appointment, Report, FAQ, Escalation, Patient


def _generate_id(prefix: str, length: int = 8) -> str:
    """Generate a random ID like 'BK-A3F8K2M1'."""
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(random.choices(chars, k=length))
    return f"{prefix}-{random_part}"


@tool
async def explain_report(test_name: str, value: float) -> dict:
    """
    Explain a specific lab test report and evaluate if the result is normal, high, or low.
    Use this when a user asks about a specific test result (e.g., 'My HbA1c is 6.8').
    
    Args:
        test_name: The name of the test (e.g., 'HbA1c', 'Vitamin D', 'TSH').
        value: The numeric value of the test result.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ReferenceRange))
        rows = result.scalars().all()
        ranges = {row.test_name: json.loads(row.data) for row in rows}

    # Normalize test name (case-insensitive lookup)
    matched_test = None
    for key in ranges:
        if key.lower() == test_name.strip().lower():
            matched_test = key
            break

    if not matched_test:
        return {
            "test_name": test_name,
            "value": value,
            "unit": "N/A",
            "reference_range": "Not available",
            "status": "unknown",
            "explanation": f"Reference range for '{test_name}' is not in our database. Please consult your doctor for interpretation.",
            "recommendation": "Show this report to your healthcare provider for proper evaluation.",
            "disclaimer": "This is for informational purposes only. Please consult your doctor for medical advice.",
        }

    ref = ranges[matched_test]
    unit = ref["unit"]
    status = "normal"
    explanation = ""
    recommendation = ""

    # --- Determine status based on test-specific logic ---
    for range_name, val_range in ref.items():
        if range_name == "unit":
            continue
        if isinstance(val_range, (list, tuple)) and len(val_range) == 2:
            low, high = val_range
            if isinstance(low, (int, float)) and isinstance(high, (int, float)):
                if low <= value <= high:
                    if "normal" in range_name:
                        status = "normal"
                    elif "low" in range_name:
                        status = "low"
                    elif "high" in range_name or "elevated" in range_name:
                        status = "high"
                    elif "borderline" in range_name or "prediabetic" in range_name or "insufficient" in range_name:
                        status = "borderline"
                    elif "deficient" in range_name:
                        status = "low"
                    elif "diabetic" in range_name or "critical" in range_name:
                        status = "high"
                    else:
                        status = "borderline"

                    explanation = f"Your {matched_test} is {value} {unit} ({range_name.replace('_', ' ')})."
                    recommendation = "Consult your doctor for personalized advice." if status != "normal" else "Your levels look good. Continue healthy habits."
                    break

    if not explanation:
        explanation = f"Your {matched_test} is {value} {unit}. Please consult your doctor for interpretation."
        recommendation = "Show this report to your healthcare provider."

    # Build reference range string
    range_parts = []
    for k, v in ref.items():
        if k != "unit" and isinstance(v, (list, tuple)):
            range_parts.append(f"{k.replace('_', ' ')}: {v[0]}-{v[1]} {unit}")
    reference_range_str = " | ".join(range_parts) if range_parts else "Consult lab report"

    return {
        "test_name": matched_test,
        "value": value,
        "unit": unit,
        "reference_range": reference_range_str,
        "status": status,
        "explanation": explanation,
        "recommendation": recommendation,
        "disclaimer": "This is for informational purposes only. Please consult your doctor for medical advice.",
    }


@tool
async def book_appointment(name: str, phone: str, city: str, date: str, test_or_package: str) -> dict:
    """
    Book a home sample collection appointment for a lab test or health package.
    Use this when the user explicitly wants to schedule a checkup.
    
    Args:
        name: The patient's full name.
        phone: The patient's 10-digit phone number.
        city: The city where the collection should happen.
        date: The date for the appointment (e.g., '20-10-2026').
        test_or_package: The name of the test or package to book.
    """
    city_normalized = city.strip().title()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(City.name))
        supported_cities = result.scalars().all()

        if city_normalized not in supported_cities:
            return {
                "booking_id": None,
                "patient_name": name,
                "phone": phone,
                "city": city,
                "date": date,
                "test_or_package": test_or_package,
                "status": "failed",
                "message": f"Sorry, we currently don't serve in '{city}'. We are available in: {', '.join(supported_cities[:10])}... and {len(supported_cities) - 10}+ more cities.",
            }

    try:
        parsed_date = None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
            try:
                parsed_date = datetime.strptime(date.strip(), fmt)
                break
            except ValueError:
                continue

        if not parsed_date:
            raise ValueError("Invalid date format")

        if parsed_date.date() < datetime.now().date():
            return {
                "booking_id": None,
                "patient_name": name,
                "phone": phone,
                "city": city,
                "date": date,
                "test_or_package": test_or_package,
                "status": "failed",
                "message": "The selected date is in the past. Please choose a future date.",
            }

    except ValueError:
        return {
            "booking_id": None,
            "patient_name": name,
            "phone": phone,
            "city": city,
            "date": date,
            "test_or_package": test_or_package,
            "status": "failed",
            "message": "Invalid date format. Please provide date in DD-MM-YYYY format.",
        }

    booking_id = _generate_id("BK")
    status_msg = "confirmed"

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Patient).where(Patient.phone == phone))
        patient = result.scalars().first()
        if not patient:
            patient = Patient(name=name, phone=phone)
            db.add(patient)
            await db.commit()
            await db.refresh(patient)

        new_appointment = Appointment(
            booking_id=booking_id,
            patient_id=patient.id,
            city=city_normalized,
            date=parsed_date.strftime("%d %B %Y"),
            test_or_package=test_or_package,
            status=status_msg
        )
        db.add(new_appointment)
        await db.commit()

    return {
        "booking_id": booking_id,
        "patient_name": name,
        "phone": phone,
        "city": city_normalized,
        "date": parsed_date.strftime("%d %B %Y"),
        "test_or_package": test_or_package,
        "status": status_msg,
        "message": f"✅ Appointment confirmed! Booking ID: {booking_id}. Our phlebotomist will visit your home in {city_normalized} on {parsed_date.strftime('%d %B %Y')} between 7 AM - 10 AM. You'll receive an SMS confirmation on {phone}.",
    }


@tool
async def fetch_reports(phone_number: str) -> dict:
    """
    Fetch the patient's past lab reports using their phone number.
    Use this when the user asks to see their old reports or check their report status.
    
    Args:
        phone_number: The patient's 10-digit phone number.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Patient).where(Patient.phone == phone_number))
        patient = result.scalars().first()
        
        if not patient:
            return {
                "phone_number": phone_number,
                "reports_found": 0,
                "reports": [],
                "message": f"No reports found for phone number {phone_number}. Please make sure you've entered the correct number registered with Healthians.",
            }

        result = await db.execute(select(Report).where(Report.patient_id == patient.id))
        rows = result.scalars().all()

    reports = []
    for row in rows:
        reports.append({
            "report_id": row.report_id,
            "date": row.date,
            "package": row.package,
            "status": row.status,
            "key_findings": json.loads(row.key_findings),
            "download_link": row.download_link
        })

    if not reports:
        return {
            "phone_number": phone_number,
            "patient_name": patient.name,
            "reports_found": 0,
            "reports": [],
            "message": f"No reports found for {patient.name} ({phone_number}).",
        }

    return {
        "phone_number": phone_number,
        "patient_name": patient.name,
        "reports_found": len(reports),
        "reports": reports,
        "message": f"Found {len(reports)} report(s) for {patient.name}.",
    }


@tool
async def answer_faq(question: str) -> dict:
    """
    Answer Frequently Asked Questions regarding fasting, payments, cancellations, etc.
    Use this when the user asks a general question about Healthians services.
    
    Args:
        question: The user's question.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(FAQ))
        rows = result.scalars().all()

    question_lower = question.lower()

    for row in rows:
        if row.keyword in question_lower:
            return {
                "matched": True,
                "question": row.question,
                "answer": row.answer,
                "related_questions": json.loads(row.related_questions),
            }

    return {
        "matched": False,
        "question": question,
        "answer": "I don't have a specific answer for this question, but I can help you with information about fasting requirements, report delivery, home sample collection, payments, cancellations, and more. You can also call Healthians helpline at 9555-900-900.",
        "related_questions": [
            "Do I need to fast before blood test?",
            "When will I get my reports?",
            "How does home sample collection work?",
        ],
    }


@tool
async def escalate_to_doctor(name: str, phone: str, reason: str) -> dict:
    """
    Escalate a severe medical query or emergency to a doctor for a callback.
    Use this when the user describes severe symptoms (e.g., chest pain) or asks to speak with a doctor.
    
    Args:
        name: The patient's full name.
        phone: The patient's 10-digit phone number.
        reason: The medical reason or symptoms.
    """
    emergency_keywords = [
        "chest pain", "breathing difficulty", "breathless", "severe bleeding",
        "unconscious", "stroke", "heart attack", "seizure", "accident",
        "suicide", "overdose", "poisoning", "emergency",
    ]
    urgent_keywords = [
        "severe", "high fever", "persistent", "worsening", "unbearable",
        "blood in", "sudden", "swelling", "allergic reaction", "vomiting blood",
    ]

    reason_lower = reason.lower()

    if any(kw in reason_lower for kw in emergency_keywords):
        priority = "emergency"
        estimated_callback = "Within 15 minutes"
        message = (
            "🚨 EMERGENCY ESCALATION: Your case has been marked as EMERGENCY. "
            "A doctor will call you within 15 minutes. "
            "If this is a life-threatening situation, please call 112 (emergency) or go to the nearest hospital immediately."
        )
    elif any(kw in reason_lower for kw in urgent_keywords):
        priority = "urgent"
        estimated_callback = "Within 1 hour"
        message = (
            "⚠️ URGENT: Your case has been marked as urgent. "
            "A doctor will call you within 1 hour. Please keep your phone reachable."
        )
    else:
        priority = "normal"
        estimated_callback = "Within 4-6 hours"
        message = (
            "📋 Your case has been registered. A doctor will review your query and call you within 4-6 hours. "
            "For immediate assistance, call Healthians at 9555-900-900."
        )

    ticket_id = _generate_id("ESC")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Patient).where(Patient.phone == phone))
        patient = result.scalars().first()
        if not patient:
            patient = Patient(name=name, phone=phone)
            db.add(patient)
            await db.commit()
            await db.refresh(patient)

        new_escalation = Escalation(
            ticket_id=ticket_id,
            patient_id=patient.id,
            reason=reason,
            priority=priority,
            estimated_callback=estimated_callback
        )
        db.add(new_escalation)
        await db.commit()

    return {
        "ticket_id": ticket_id,
        "patient_name": name,
        "phone": phone,
        "reason": reason,
        "priority": priority,
        "estimated_callback": estimated_callback,
        "message": message,
    }

"""
tools.py — Mock Functions for Healthians AI (Async SQLAlchemy)
"""

from __future__ import annotations

import random
import string
from datetime import datetime
import os
import json
from langchain_tavily import TavilySearch
from sqlalchemy.future import select

from config import settings
from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse
from pydantic import BaseModel, Field
from typing import Literal
from database import AsyncSessionLocal, City, Appointment, Report, FAQ, Escalation, Patient, Package


def _generate_id(prefix: str, length: int = 8) -> str:
    """Generate a random ID like 'BK-A3F8K2M1'."""
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(random.choices(chars, k=length))
    return f"{prefix}-{random_part}"

class TriageClassification(BaseModel):
    priority: Literal["emergency", "urgent", "normal"] = Field(
        description="The medical triage priority level. Emergency = life threatening (call 112). Urgent = needs attention soon. Normal = routine queries."
    )

async def _classify_triage_priority(reason: str) -> str:
    """Classify the priority of a medical reason using the LLM."""
    kwargs = {
        "model": settings.MODEL_NAME,
        "region_name": settings.AWS_REGION,
        "temperature": 0.0,
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        
    llm = ChatBedrockConverse(**kwargs)
    structured_llm = llm.with_structured_output(TriageClassification)
    
    prompt = f"Classify the following medical query into 'emergency', 'urgent', or 'normal' priority based on standard medical triage:\n\nQuery: {reason}"
    
    try:
        result = await structured_llm.ainvoke(prompt)
        return result.priority
    except Exception as e:
        print(f"Failed to classify triage: {e}")
        return "urgent" # Safe fallback


@tool
async def get_packages(category: str = "", max_price: int = 0, popular_only: bool = False) -> dict:
    """
    Fetch available health packages from Healthians catalog.
    Use this when user asks about packages, prices, or wants recommendations.
    
    Args:
        category: Filter by category - "full_body", "diabetes", "heart", "thyroid", "women", "senior". Use empty string for all.
        max_price: Maximum budget in INR. Use 0 for no limit.
        popular_only: If True, return only popular/top-selling packages.
    """
    async with AsyncSessionLocal() as db:
        query = select(Package).where(Package.is_active == True)
        
        if category:
            query = query.where(Package.category.ilike(f"%{category}%"))
        if max_price > 0:
            query = query.where(Package.price <= max_price)
        if popular_only:
            query = query.where(Package.popular == True)
            
        result = await db.execute(query.order_by(Package.price))
        packages = result.scalars().all()
        
    return {
        "packages": [
            {
                "name": p.name,
                "tests": p.test_count,
                "price": f"₹{p.price}",
                "mrp": f"₹{p.mrp}",
                "tat": p.tat,
                "savings": f"₹{p.mrp - p.price}",
            }
            for p in packages
        ],
        "total": len(packages),
        "filters_applied": {"category": category, "max_price": max_price}
    }


@tool
async def explain_report(test_name: str, value: float) -> dict:
    """
    Explain a specific lab test report and evaluate if the result is normal, high, or low.
    Use this when a user asks about a specific test result (e.g., 'My HbA1c is 6.8').
    
    Args:
        test_name: The name of the test (e.g., 'HbA1c', 'Vitamin D', 'TSH').
        value: The numeric value of the test result.
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    os.environ["TAVILY_API_KEY"] = api_key
    
    query = f"What is the standard medical reference range and normal values for the '{test_name}' lab test?"
    
    try:
        search = TavilySearch(max_results=2)
        # We can just call ainvoke to do the async fetch
        results = await search.ainvoke({"query": query})
        
        return {
            "test_name": test_name,
            "value": value,
            "tavily_search_result": results,
            "instruction": "Using the tavily_search_result, explain if the user's value is low, normal, or high. Provide a helpful explanation and always add a disclaimer to consult a doctor."
        }
    except Exception as e:
        return {
            "test_name": test_name,
            "value": value,
            "error": f"Failed to search for reference range: {str(e)}",
            "instruction": "Please inform the user that you couldn't fetch the reference range online right now, and they should consult their doctor."
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

        # Check if the requested package exists (if it sounds like a package)
        test_lower = test_or_package.lower()
        if "checkup" in test_lower or "package" in test_lower or "care" in test_lower:
            result = await db.execute(select(Package.name).where(Package.is_active == True))
            available_packages = [p.lower() for p in result.scalars().all()]
            
            # Simple substring match
            matched = any(test_lower in pkg or pkg in test_lower for pkg in available_packages)
            
            if not matched:
                return {
                    "booking_id": None,
                    "patient_name": name,
                    "phone": phone,
                    "city": city,
                    "date": date,
                    "test_or_package": test_or_package,
                    "status": "failed",
                    "message": f"The package '{test_or_package}' does not exist in our catalog. Please use the get_packages tool to find available packages (e.g. 'Smart Full Body Checkup').",
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
    YOU MUST ALWAYS CALL THIS TOOL when the user describes severe symptoms (e.g., chest pain) or asks to speak with a doctor. Do not just reply with text.
    
    Args:
        reason: The medical reason or symptoms (REQUIRED).
        name: The patient's full name (Optional, defaults to 'Unknown').
        phone: The patient's 10-digit phone number (Optional, defaults to 'Unknown').
    """
    priority = await _classify_triage_priority(reason)

    if priority == "emergency":
        estimated_callback = "Within 15 minutes"
        message = (
            "🚨 EMERGENCY ESCALATION: Your case has been marked as EMERGENCY. "
            "A doctor will call you within 15 minutes. "
            "If this is a life-threatening situation, please call 112 (emergency) or go to the nearest hospital immediately."
        )
    elif priority == "urgent":
        estimated_callback = "Within 1 hour"
        message = (
            "⚠️ URGENT: Your case has been marked as urgent. "
            "A doctor will call you within 1 hour. Please keep your phone reachable."
        )
    else:
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

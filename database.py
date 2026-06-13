"""
database.py — Async SQLAlchemy Database Manager for Healthians AI
Handles async DB connection, ORM schema definition, and seeding of mock data.
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select

# Path to the SQLite database file
DB_PATH = Path(__file__).parent / "healthians.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# SQLAlchemy Async Setup
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Package(Base):
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    test_count = Column(Integer)
    price = Column(Integer)
    mrp = Column(Integer)
    tat = Column(String)  # Turnaround time
    category = Column(String)  # "full_body", "diabetes", "heart", etc.
    is_active = Column(Boolean, default=True)
    popular = Column(Boolean, default=False)  # For "top recommendations"

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    data = Column(Text, nullable=True) # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    report_id = Column(String, unique=True, nullable=False)
    date = Column(String, nullable=False)
    package = Column(String, nullable=False)
    status = Column(String, nullable=False)
    key_findings = Column(Text, nullable=False) # JSON string
    download_link = Column(String, nullable=False)

class Appointment(Base):
    __tablename__ = "appointments"

    booking_id = Column(String, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    city = Column(String, nullable=False)
    date = Column(String, nullable=False)
    test_or_package = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Escalation(Base):
    __tablename__ = "escalations"

    ticket_id = Column(String, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(String, nullable=False)
    estimated_callback = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class FAQ(Base):
    __tablename__ = "faqs"

    keyword = Column(String, primary_key=True)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    related_questions = Column(Text, nullable=False) # JSON string

class City(Base):
    __tablename__ = "cities"

    name = Column(String, primary_key=True)

# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

async def init_db():
    """Initialize database tables and seed mock data if empty (Async)."""
    
    # 1. Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed Mock Data
    async with AsyncSessionLocal() as session:
        # Seed Packages
        result = await session.execute(select(Package))
        if not result.scalars().first():
            packages = [
                ("Smart Full Body Checkup", 90, 1199, 5000, "24-48 hrs", "full_body", True),
                ("Good Health Package", 65, 799, 3500, "24-48 hrs", "full_body", False),
                ("Diabetes Care Package", 45, 699, 2800, "24-48 hrs", "diabetes", True),
                ("Heart Care Package", 40, 899, 3200, "24-48 hrs", "heart", True),
                ("Thyroid Care Package", 30, 599, 2000, "24-48 hrs", "thyroid", False),
                ("Women's Health Package", 70, 1299, 5500, "24-48 hrs", "women", True),
                ("Senior Citizen Package", 80, 1499, 6000, "24-48 hrs", "senior", True),
            ]
            for name, count, price, mrp, tat, category, popular in packages:
                session.add(Package(name=name, test_count=count, price=price, mrp=mrp, tat=tat, category=category, popular=popular))

        # Seed FAQs
        result = await session.execute(select(FAQ))
        if not result.scalars().first():
            faqs = [
                ("fasting", "Do I need to fast before my blood test?", "Yes, for tests like Fasting Blood Sugar, Lipid Profile, and some liver tests, you need to fast for 8-12 hours before the sample collection. You can drink plain water during fasting. Our phlebotomist will confirm specific requirements when they call you.", ["What can I eat before blood test?", "How long to fast for lipid profile?"]),
                ("report", "When will I get my reports?", "Most test reports are delivered within 24-48 hours after sample collection. Some specialized tests (like culture tests, genetic tests) may take 3-7 days. You'll receive an SMS/email notification as soon as your report is ready. You can also check the Healthians app.", ["How to download my report?", "Can I get printed report?"]),
                ("home sample", "How does home sample collection work?", "It's simple! 1) Book your test online or through our AI assistant. 2) Our trained phlebotomist visits your home at the scheduled time (usually 7-10 AM). 3) Sample is collected hygienically with disposable equipment. 4) Reports are delivered digitally within 24-48 hours. The entire process takes just 5-10 minutes!", ["Is home collection safe?", "What areas do you cover?"]),
                ("payment", "What payment methods are accepted?", "We accept all major payment methods: UPI (GPay, PhonePe, Paytm), credit/debit cards, net banking, wallets, and cash on collection. You can pay online while booking or pay the phlebotomist directly.", ["Do you accept insurance?", "Any EMI options?"]),
                ("cancel", "How do I cancel or reschedule my appointment?", "You can cancel or reschedule your appointment through the Healthians app, website, or by calling our helpline at 9555-900-900. Cancellation is free if done 2 hours before the scheduled time. Full refund is processed within 5-7 business days.", ["Is there a cancellation fee?", "Can I change the date?"]),
                ("accuracy", "How accurate are your test results?", "Healthians is NABL accredited and follows strict quality protocols. Our labs use advanced automated analyzers and every sample goes through quality checks. We partner with top NABL-certified labs across India to ensure 99.9% accuracy.", ["Are your labs certified?", "What equipment do you use?"]),
                ("covid", "Do you offer COVID-19 tests?", "Yes, we offer RT-PCR and Rapid Antigen tests for COVID-19 with home sample collection. Results are available within 24 hours for RT-PCR and 30 minutes for Rapid Antigen. Reports are ICMR compliant and can be used for travel.", ["COVID test cost?", "Is home collection available for COVID?"]),
                ("pregnancy", "What tests are recommended during pregnancy?", "We have a comprehensive Pregnancy Care Package that includes: CBC, Blood Group, HIV, HBsAg, VDRL, Thyroid Profile, Blood Sugar, Urine Routine, and more. Regular monitoring is essential — consult your gynecologist for a personalized test schedule.", ["Pregnancy package cost?", "When to do first trimester screening?"])
            ]
            for kw, q, a, rel in faqs:
                session.add(FAQ(keyword=kw, question=q, answer=a, related_questions=json.dumps(rel)))

        # Seed Patients & Reports
        result = await session.execute(select(Patient))
        if not result.scalars().first():
            p1 = Patient(phone="9876543210", name="John Doe")
            p2 = Patient(phone="9123456789", name="Jane Doe")
            session.add_all([p1, p2])
            await session.commit()
            
            reports = [
                (p1.id, "RPT-001", "05 June 2026", "Smart Full Body Checkup", "completed", [
                    {"test": "HbA1c", "value": 5.4, "unit": "%", "status": "normal"},
                    {"test": "Vitamin D", "value": 18.5, "unit": "ng/mL", "status": "low"},
                    {"test": "Total Cholesterol", "value": 215, "unit": "mg/dL", "status": "borderline_high"},
                    {"test": "TSH", "value": 3.2, "unit": "mIU/L", "status": "normal"}
                ], "https://reports.healthians.com/mock/RPT-001.pdf"),
                (p1.id, "RPT-002", "10 March 2026", "Thyroid Care Package", "completed", [
                    {"test": "TSH", "value": 6.8, "unit": "mIU/L", "status": "high"},
                    {"test": "Free T4", "value": 0.7, "unit": "ng/dL", "status": "low"},
                    {"test": "Free T3", "value": 2.1, "unit": "pg/mL", "status": "low"}
                ], "https://reports.healthians.com/mock/RPT-002.pdf"),
                (p2.id, "RPT-003", "01 June 2026", "Diabetes Care Package", "completed", [
                    {"test": "HbA1c", "value": 7.2, "unit": "%", "status": "high"},
                    {"test": "Fasting Blood Sugar", "value": 142, "unit": "mg/dL", "status": "high"}
                ], "https://reports.healthians.com/mock/RPT-003.pdf")
            ]
            for pid, rid, date, pkg, status, findings, link in reports:
                session.add(Report(patient_id=pid, report_id=rid, date=date, package=pkg, status=status, key_findings=json.dumps(findings), download_link=link))

        # Seed Cities (Fallback if empty)
        result = await session.execute(select(City))
        if not result.scalars().first():
            cities = ["Delhi", "Gurgaon", "Noida", "Mumbai", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh"]
            for city in cities:
                session.add(City(name=city))

        await session.commit()

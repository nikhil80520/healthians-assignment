"""
streamlit_app.py — Streamlit Chat UI for Healthians AI
A premium, modern chat interface that directly integrates with the AI agent.

Run:
    venv\\Scripts\\streamlit.exe run streamlit_app.py
"""

import uuid
import streamlit as st
from agent import process_message


# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Healthians AI Assistant",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — Premium Healthians Theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ---------- Google Font ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ---------- Root Variables ---------- */
:root {
    --healthians-primary: #00A86B;
    --healthians-primary-dark: #008C59;
    --healthians-gradient: linear-gradient(135deg, #00A86B 0%, #00C9A7 50%, #00D4AA 100%);
    --bg-dark: #0E1117;
    --bg-card: #1A1D23;
    --bg-card-hover: #22262E;
    --text-primary: #FAFAFA;
    --text-secondary: #9CA3AF;
    --text-muted: #6B7280;
    --border-color: #2D3139;
    --user-bubble: linear-gradient(135deg, #00A86B, #00C9A7);
    --ai-bubble: #1E2128;
    --accent-red: #EF4444;
    --accent-yellow: #F59E0B;
    --accent-blue: #3B82F6;
}

/* ---------- Global ---------- */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background-color: var(--bg-dark);
}

/* ---------- Hide Streamlit Defaults ---------- */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F1318 0%, #141820 100%);
    border-right: 1px solid var(--border-color);
}

[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--text-primary);
}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

/* ---------- Header Banner ---------- */
.header-banner {
    background: var(--healthians-gradient);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 8px 32px rgba(0, 168, 107, 0.2);
}

.header-banner h1 {
    color: white;
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
}

.header-banner p {
    color: rgba(255,255,255,0.85);
    font-size: 0.9rem;
    margin: 4px 0 0 0;
}

.header-logo {
    font-size: 2.5rem;
    line-height: 1;
}

/* ---------- Chat Messages ---------- */
.chat-container {
    max-width: 780px;
    margin: 0 auto;
}

.user-msg {
    background: var(--user-bubble);
    color: white;
    padding: 14px 18px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0;
    margin-left: 15%;
    font-size: 0.95rem;
    line-height: 1.6;
    box-shadow: 0 2px 12px rgba(0, 168, 107, 0.15);
}

.ai-msg {
    background: var(--ai-bubble);
    color: var(--text-primary);
    padding: 16px 20px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 0;
    margin-right: 10%;
    font-size: 0.95rem;
    line-height: 1.7;
    border: 1px solid var(--border-color);
}

.ai-msg strong { color: #00D4AA; }
.ai-msg a { color: #00C9A7; text-decoration: none; }
.ai-msg code { background: #2a2e35; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }

/* ---------- Intent Badge ---------- */
.intent-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}

.intent-explain_report { background: rgba(59,130,246,0.15); color: #60A5FA; }
.intent-book_appointment { background: rgba(0,168,107,0.15); color: #00D4AA; }
.intent-fetch_reports { background: rgba(139,92,246,0.15); color: #A78BFA; }
.intent-answer_faq { background: rgba(245,158,11,0.15); color: #FBBF24; }
.intent-escalate_to_doctor { background: rgba(239,68,68,0.15); color: #F87171; }
.intent-test_suggestion { background: rgba(20,184,166,0.15); color: #2DD4BF; }
.intent-general_chat { background: rgba(156,163,175,0.1); color: #9CA3AF; }
.intent-error { background: rgba(239,68,68,0.15); color: #F87171; }

/* ---------- Data Card ---------- */
.data-card {
    background: #1A1F2B;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    margin-top: 10px;
    font-size: 0.85rem;
}

.data-card .data-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(45,49,57,0.5);
}

.data-card .data-row:last-child { border-bottom: none; }
.data-card .data-key { color: var(--text-muted); }
.data-card .data-val { color: var(--text-primary); font-weight: 500; }

/* ---------- Status Indicators ---------- */
.status-normal { color: #22C55E; }
.status-low, .status-high, .status-critical { color: #EF4444; }
.status-borderline { color: #F59E0B; }

/* ---------- Followup Buttons ---------- */
.stButton > button {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    border-radius: 24px;
    padding: 6px 16px;
    font-size: 0.82rem;
    font-family: 'Inter', sans-serif;
    transition: all 0.2s ease;
    cursor: pointer;
}

.stButton > button:hover {
    border-color: var(--healthians-primary);
    color: var(--healthians-primary);
    background: rgba(0,168,107,0.08);
}

/* ---------- Chat Input ---------- */
[data-testid="stChatInput"] {
    border-top: 1px solid var(--border-color);
}

[data-testid="stChatInput"] textarea {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
}

/* ---------- Expander (Data details) ---------- */
.streamlit-expanderHeader {
    font-size: 0.85rem;
    color: var(--text-muted);
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session State Init
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "phone" not in st.session_state:
    st.session_state.phone = ""

if "language" not in st.session_state:
    st.session_state.language = "auto"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🏥 Healthians AI")
    st.markdown("---")

    st.markdown("### Settings")
    st.session_state.phone = st.text_input(
        "📱 Phone Number",
        value=st.session_state.phone,
        placeholder="10-digit number",
        max_chars=10,
        help="Enter your registered phone number to fetch reports",
    )

    st.session_state.language = st.selectbox(
        "🌐 Language",
        options=["auto", "en", "hi"],
        format_func=lambda x: {"auto": "Auto-detect", "en": "English", "hi": "Hindi"}[x],
        help="Choose your preferred response language",
    )

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Try asking:")
    examples = [
        "My HbA1c is 6.8, what does it mean?",
        "Book a full body checkup in Delhi",
        "Do I need to fast before blood test?",
        "What health packages do you offer?",
        "Mera Vitamin D 15 hai, normal hai?",
    ]
    for ex in examples:
        st.markdown(f"- _{ex}_")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#6B7280; font-size:0.75rem;'>"
        "Powered by AWS Bedrock + Claude<br>"
        f"Session: <code>{st.session_state.session_id[:8]}...</code>"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="header-banner">
        <div class="header-logo">🏥</div>
        <div>
            <h1>Healthians AI Assistant</h1>
            <p>Your trusted at-home diagnostics companion — ask about reports, book tests, and more.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper: Render a single message
# ---------------------------------------------------------------------------
def render_intent_badge(intent: str) -> str:
    """Return an HTML intent badge."""
    labels = {
        "explain_report": "📊 Report",
        "book_appointment": "📅 Booking",
        "fetch_reports": "📋 Reports",
        "answer_faq": "❓ FAQ",
        "escalate_to_doctor": "🚨 Escalation",
        "test_suggestion": "💡 Suggestion",
        "general_chat": "💬 Chat",
        "error": "⚠️ Error",
    }
    label = labels.get(intent, intent)
    return f'<span class="intent-badge intent-{intent}">{label}</span>'


def render_data_card(data: dict) -> str:
    """Render structured data as a styled card."""
    if not data:
        return ""

    # Pick interesting keys to show (skip long text fields)
    skip_keys = {"explanation", "recommendation", "disclaimer", "answer", "message", "related_questions", "download_link", "popular_tests"}
    rows = []
    for k, v in data.items():
        if k in skip_keys:
            continue
        if isinstance(v, list):
            if len(v) > 0 and isinstance(v[0], dict):
                continue  # Skip nested lists of dicts
            v = ", ".join(str(i) for i in v)
        if isinstance(v, dict):
            continue

        display_key = k.replace("_", " ").title()

        # Add status coloring
        if k == "status" and isinstance(v, str):
            css_class = f"status-{v}"
            v_html = f'<span class="{css_class}">{v.upper()}</span>'
        else:
            v_html = str(v)

        rows.append(f'<div class="data-row"><span class="data-key">{display_key}</span><span class="data-val">{v_html}</span></div>')

    if not rows:
        return ""

    return '<div class="data-card">' + "".join(rows) + "</div>"


# ---------------------------------------------------------------------------
# Display Chat History
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        intent = msg.get("intent", "general_chat")
        badge = render_intent_badge(intent)
        data_card = render_data_card(msg.get("data"))

        ai_html = f"""
        <div class="ai-msg">
            {badge}
            <div>{msg["content"]}</div>
            {data_card}
        </div>
        """
        st.markdown(ai_html, unsafe_allow_html=True)

        # Followup suggestion buttons
        followups = msg.get("followups", [])
        if followups:
            cols = st.columns(min(len(followups), 3))
            for i, fup in enumerate(followups[:3]):
                with cols[i]:
                    if st.button(fup, key=f"fup_{msg.get('idx', 0)}_{i}"):
                        st.session_state.pending_followup = fup
                        st.rerun()


# ---------------------------------------------------------------------------
# Chat Input
# ---------------------------------------------------------------------------
# Check if a followup was clicked
user_input = None
if "pending_followup" in st.session_state:
    user_input = st.session_state.pending_followup
    del st.session_state.pending_followup

chat_input = st.chat_input("Type your health question here...")
if chat_input:
    user_input = chat_input

if user_input:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
    })

    # Show user message immediately
    st.markdown(f'<div class="user-msg">{user_input}</div>', unsafe_allow_html=True)

    # Call the AI agent
    with st.spinner("🤔 Thinking..."):
        phone = st.session_state.phone if len(st.session_state.phone) == 10 else None
        
        import asyncio
        response = asyncio.run(process_message(
            user_message=user_input,
            session_id=st.session_state.session_id,
            phone=phone,
            language=st.session_state.language,
        ))

    # Add AI response to history
    msg_idx = len(st.session_state.messages)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response.reply,
        "intent": response.intent,
        "data": response.data,
        "followups": response.suggested_followups,
        "idx": msg_idx,
    })

    st.rerun()


# ---------------------------------------------------------------------------
# Empty State
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    st.markdown(
        """
        <div style="text-align: center; padding: 60px 20px; color: #6B7280;">
            <div style="font-size: 3.5rem; margin-bottom: 16px;">💬</div>
            <h3 style="color: #9CA3AF; font-weight: 500;">Start a conversation</h3>
            <p style="font-size: 0.9rem; max-width: 400px; margin: 0 auto;">
                Ask me about your lab reports, book a health checkup,
                or get answers to your health questions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

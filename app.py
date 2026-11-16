import html
import io
import json
import random
import time
from datetime import datetime

import docx
import groq
import streamlit as st
from groq import Groq
from pypdf import PdfReader

st.set_page_config(page_title="Interview Coach", page_icon="🎯", layout="wide")

# ---------- Config ----------
CHAT_MODEL = "openai/gpt-oss-20b"     # fast model for the live interview and hints
EVAL_MODEL = "openai/gpt-oss-120b"    # stronger model for grading

POSITIONS = ["Software Engineer", "Data Scientist", "Product Manager", "Designer", "Other"]
LEVELS = ["Intern", "Junior", "Mid", "Senior", "Lead"]
INTERVIEWER_NAME = "Jon"
MINUTES_PER_QUESTION = 2
SETUP_TITLES = [
    "Your rehearsal room is ready",
    "Practice today, nail it tomorrow",
    "Your next offer starts here",
]

INTERVIEW_TYPES = {
    "Behavioral": "Focus on behavioral questions about past experiences, teamwork, conflict, "
                  "and motivation. Encourage answers in the STAR format.",
    "Technical": "Focus on conceptual technical questions about the skills and knowledge the "
                 "role requires, including problem-solving and practical scenarios, answered "
                 "verbally without writing code.",
    "Mixed": "Mix behavioral and technical questions.",
}
COMMON_SKILLS = [
    "Python", "SQL", "Java", "JavaScript", "TypeScript", "React", "Node.js", "C++", "Git",
    "Machine learning", "Data analysis", "Statistics", "Excel", "Power BI", "Tableau",
    "AWS", "Docker", "Figma", "Communication", "Leadership", "Problem solving", "Teamwork",
]
SCORE_CATEGORIES = {
    "communication": ("Communication", "🗣️"),
    "technical_depth": ("Technical depth", "🧠"),
    "relevance": ("Relevance", "🎯"),
    "confidence": ("Confidence", "💪"),
}
MAX_ANSWER_CHARS = 1500
MAX_JD_CHARS = 3000
MAX_CV_CHARS = 12000
AVATARS = {"assistant": "🧑‍💼", "user": "🙋"}

KICKOFF_MESSAGE = {
    "role": "user",
    "content": "[The candidate has joined. Greet them by name, briefly explain the interview, "
               "and ask your first question.]",
}
FINAL_NOTE = {
    "role": "system",
    "content": "That was the candidate's final answer. Briefly acknowledge it, thank them, and "
               "close the interview. Do not ask another question.",
}

# ---------- Styling ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --ink: #0F172A; --muted: #64748B; --line: #E2E8F0; --soft: #F8FAFC;
    --primary: #2563EB; --primary-soft: #EFF6FF; --primary-line: #BFDBFE;
}
html, body, [class*="css"], .stMarkdown, button, input, textarea {
    font-family: 'Inter', sans-serif !important;
}
.stApp { background: #F6F8FB; }
header[data-testid="stHeader"] { display: none; }
.block-container { max-width: 1120px; padding: 5.2rem 1.5rem 4rem; }

/* Top nav */
.topnav {
    position: fixed; top: 0; left: 0; right: 0; height: 56px; z-index: 999990;
    background: #fff; border-bottom: 1px solid var(--line);
}
.topnav .inner {
    max-width: 1120px; margin: 0 auto; height: 100%; padding: 0 1.5rem;
    display: flex; align-items: center; gap: 1.6rem;
}
.brand { display: flex; align-items: center; gap: .55rem; font-weight: 700; color: var(--ink); }
.brand .logo {
    width: 26px; height: 26px; border-radius: 7px; background: var(--primary); color: #fff;
    display: grid; place-items: center; font-size: .8rem;
}
.navlinks { display: flex; gap: .3rem; }
.navlinks span { padding: 6px 10px; border-radius: 7px; font-size: .86rem; color: #475569; }
.navlinks span.on { background: var(--primary-soft); color: var(--primary); font-weight: 600; }
.navlinks span.off { color: #94A3B8; cursor: default; }

/* Page header */
.crumbs { font-size: .78rem; color: var(--muted); margin-bottom: .55rem; }
.page-title { font-size: 1.65rem; font-weight: 800; color: var(--ink); margin: 0 0 .25rem; }
.page-sub { color: #475569; font-size: .92rem; margin-bottom: 1.4rem; }

/* Cards */
[class*="st-key-card"] {
    background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 1.4rem 1.5rem;
}
.rail {
    background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: .45rem;
}
.rstep { display: flex; gap: .7rem; padding: .65rem .7rem; border-radius: 9px; align-items: flex-start; }
.rstep .n {
    width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0; display: grid; place-items: center;
    font-size: .72rem; font-weight: 700; border: 1px solid #CBD5E1; color: #475569; background: #fff;
}
.rstep b { display: block; font-size: .86rem; color: var(--ink); }
.rstep small { font-size: .76rem; color: var(--muted); }
.rstep.on { background: var(--primary-soft); }
.rstep.on .n { background: var(--primary); border-color: var(--primary); color: #fff; }
.rstep.done .n { background: #DCFCE7; border-color: #86EFAC; color: #15803D; }
.tipcard {
    margin: .45rem .25rem .25rem; padding: .75rem .8rem; border-radius: 9px;
    background: var(--soft); border: 1px solid var(--line); font-size: .78rem; color: #475569;
    line-height: 1.5;
}
.tipcard b { display: block; color: var(--ink); font-size: .82rem; margin-bottom: .25rem; }
.tipcard .k { color: var(--muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .05em; }
.tipcard .v { color: var(--ink); font-weight: 600; font-size: .84rem; margin-bottom: .4rem; }

.section-h { font-size: 1rem; font-weight: 700; color: var(--ink); margin: 0 0 .2rem; }
.split { border: 0; border-top: 1px solid var(--line); margin: .6rem -1.5rem 1rem; }

/* Inputs */
label p { font-size: .82rem !important; font-weight: 600 !important; color: #1E293B; }
.stTextInput input, .stTextArea textarea, .stNumberInput input,
div[data-baseweb="select"] > div { border-radius: 8px !important; background: #fff !important; }
.stMultiSelect [data-baseweb="tag"] {
    background: var(--primary-soft) !important; border: 1px solid var(--primary-line);
}
.stMultiSelect [data-baseweb="tag"] span, .stMultiSelect [data-baseweb="tag"] svg {
    color: #1D4ED8 !important; fill: #1D4ED8 !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: var(--soft); border: 1px dashed #CBD5E1; border-radius: 10px; padding: .7rem 1rem;
}

/* Level segmented control: full width, solid active state */
[data-testid="stButtonGroup"], [data-testid="stButtonGroup"] > div { width: 100% !important; }
[data-testid="stButtonGroup"] button { flex: 1; background: #fff; padding: .35rem .25rem; min-width: 0; }
[data-testid="stButtonGroup"] button p { font-size: .82rem; }
[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
    background: var(--primary) !important; border-color: var(--primary) !important;
}
[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] p { color: #fff !important; }

/* Question type: radio rows as cards */
.st-key-qtype .stRadio, .st-key-qtype .stRadio > div { width: 100% !important; }
.st-key-qtype div[role="radiogroup"] {
    flex-direction: column; gap: .5rem; width: 100% !important; align-items: stretch !important;
}
.st-key-qtype div[role="radiogroup"] > label {
    width: 100%; margin: 0; padding: .6rem .8rem; border: 1px solid var(--line);
    border-radius: 8px; background: #fff;
}
.st-key-qtype div[role="radiogroup"] > label:has(input:checked) {
    border-color: var(--primary); background: var(--primary-soft);
}

.summary-box {
    margin-top: .35rem; padding: .7rem .85rem; border-radius: 8px; font-size: .8rem; color: #475569;
    background: var(--soft); border: 1px solid var(--line); line-height: 1.5;
}
.summary-box b { color: var(--ink); }

/* Card footer band */
.st-key-footer {
    background: var(--soft); border-top: 1px solid var(--line);
    margin: .6rem -1.5rem -1.4rem; padding: .85rem 1.5rem; border-radius: 0 0 12px 12px;
    width: calc(100% + 3rem) !important; max-width: none !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 600; }
.stButton > button:disabled { opacity: .5; }

/* Chips */
.chips { display: flex; gap: .4rem; flex-wrap: wrap; margin-bottom: .8rem; }
.chip { padding: 3px 10px; border-radius: 999px; font-size: .78rem; font-weight: 500;
    background: var(--soft); border: 1px solid var(--line); color: #334155; }
.chip.accent { background: var(--primary-soft); border-color: var(--primary-line); color: var(--primary); }

/* Chat */
div[data-testid="stChatMessage"] {
    border-radius: 12px; padding: .75rem .95rem; margin-bottom: .5rem;
    background: #fff; border: 1px solid var(--line);
}
div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]),
div[data-testid="stChatMessage"][aria-label="Chat message from user"] {
    background: var(--primary-soft); border-color: var(--primary-line);
}

/* Score ring */
.score-wrap { display: flex; align-items: center; gap: 1.6rem; flex-wrap: wrap; }
.ring {
    --size: 140px; width: var(--size); height: var(--size); border-radius: 50%; flex-shrink: 0;
    display: grid; place-items: center;
    background: conic-gradient(var(--c) calc(var(--p) * 1%), #E2E8F0 0);
}
.ring .inner {
    width: calc(var(--size) - 20px); height: calc(var(--size) - 20px); border-radius: 50%;
    background: #fff; display: grid; place-items: center; text-align: center;
}
.ring .num { font-size: 2.3rem; font-weight: 800; line-height: 1; color: var(--ink); }
.ring .den { font-size: .8rem; color: var(--muted); }
.verdict { font-size: 1.25rem; font-weight: 700; margin-bottom: .3rem; }
.summary { color: #475569; line-height: 1.55; }

/* Category bars */
.cat { margin-bottom: .85rem; }
.cat .top { display: flex; justify-content: space-between; font-size: .88rem; margin-bottom: .3rem; }
.cat .top .val { font-weight: 700; }
.bar { height: 8px; border-radius: 999px; background: #E2E8F0; overflow: hidden; }
.bar > span { display: block; height: 100%; border-radius: 999px; }

/* Stat tiles */
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; margin: .8rem 0; }
.stat { padding: .8rem; border-radius: 12px; text-align: center; background: #fff; border: 1px solid var(--line); }
.stat .v { font-size: 1.3rem; font-weight: 700; color: var(--ink); }
.stat .l { font-size: .76rem; color: var(--muted); margin-top: .15rem; }

/* Lists */
.pill-list { list-style: none; padding: 0; margin: 0; }
.pill-list li { padding: .55rem .75rem; border-radius: 8px; margin-bottom: .45rem; font-size: .9rem;
    line-height: 1.45; background: var(--soft); border-left: 3px solid var(--c); color: #334155; }

.gap { height: .8rem; }

@media (max-width: 640px) {
    .block-container { padding: 4.6rem 1rem 3rem; }
    .navlinks span.off { display: none; }
    .stats { gap: .4rem; }
    .ring { --size: 116px; }
    .split { margin-left: -1rem; margin-right: -1rem; }
    [class*="st-key-card"] { padding: 1.1rem 1rem; }
    .st-key-footer { margin: .6rem -1rem -1.1rem; padding: .8rem 1rem; width: calc(100% + 2rem) !important; }
}
</style>
""",
    unsafe_allow_html=True,
)


def esc(text):
    return html.escape(str(text))


def html_block(markup):
    st.markdown(markup, unsafe_allow_html=True)


def top_nav():
    html_block(
        """
<div class="topnav"><div class="inner">
  <div class="brand"><span class="logo">☰</span>Interview Coach</div>
  <div class="navlinks">
    <span class="on">Practice</span>
    <span class="off" title="Coming soon">History</span>
    <span class="off" title="Coming soon">Resources</span>
  </div>
</div></div>
"""
    )


def page_header(crumb, title, subtitle):
    html_block(
        f'<div class="crumbs">Practice / {esc(crumb)}</div>'
        f'<div class="page-title">{esc(title)}</div>'
        f'<div class="page-sub">{esc(subtitle)}</div>'
    )


RAIL_STEPS = [("Setup", "Profile and role"), ("Interview", "Answer questions"),
              ("Feedback", "Scores and tips")]


def step_rail(active, extra=""):
    parts = []
    for i, (name, sub) in enumerate(RAIL_STEPS):
        state = "on" if i == active else "done" if i < active else ""
        mark = "✓" if i < active else str(i + 1)
        parts.append(f'<div class="rstep {state}"><span class="n">{mark}</span>'
                     f'<div><b>{name}</b><small>{sub}</small></div></div>')
    html_block(f'<div class="rail">{"".join(parts)}{extra}</div>')


STAR_CARD = ('<div class="tipcard"><b>STAR method</b>Situation, Task, Action, Result. '
             'Use it for every behavioral answer.</div>')


def section_h(text):
    html_block(f'<div class="section-h">{esc(text)}</div>')


def split():
    html_block('<hr class="split">')


def score_color(score):
    if score >= 8:
        return "#16A34A"
    if score >= 6:
        return "#2563EB"
    if score >= 4:
        return "#D97706"
    return "#DC2626"


def verdict(score):
    if score >= 8:
        return "Excellent performance 🚀"
    if score >= 6:
        return "Solid interview 👍"
    if score >= 4:
        return "Getting there 🛠️"
    return "Keep practicing 🌱"


def fmt_duration(seconds):
    seconds = int(max(0, seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


top_nav()


# ---------- API client ----------
def get_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = None
    if not api_key:
        st.error(
            "No Groq API key found. Add `GROQ_API_KEY` to `.streamlit/secrets.toml` "
            "(or to your app's Secrets on Streamlit Cloud) and reload the page."
        )
        st.stop()
    return Groq(api_key=api_key)


client = get_client()


def friendly_error(err):
    if isinstance(err, groq.AuthenticationError):
        return "The Groq API key is invalid. Check `GROQ_API_KEY` in your secrets."
    if isinstance(err, groq.RateLimitError):
        return "Too many requests right now. Wait a moment and try again."
    if isinstance(err, groq.APIConnectionError):
        return "Couldn't reach the AI service. Check your internet connection and try again."
    return "Something went wrong while contacting the AI service. Please try again."


# ---------- Session state ----------
defaults = {
    "setup_complete": False,
    "feedback_shown": False,
    "chat_complete": False,
    "ended_early": False,
    "messages": [],
    "answer_count": 0,
    "profile": {},
    "feedback": None,
    "started_at": None,
    "ended_at": None,
    "hint": None,
    "cv_status": None,
    
    "w_level": "Junior",
    "w_skills": [],
    "w_interview_type": "Mixed",
    "w_num_questions": 5,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def position_title(ss):
    return ss.w_custom_position.strip() if ss.w_position == "Other" else ss.w_position


def complete_setup():
    ss = st.session_state
    ss.profile = {
        "name": ss.w_name.strip(),
        "experience": ss.w_experience.strip(),
        "skills": ", ".join(ss.w_skills),
        "grad_year": ss.w_grad_year,
        "position": position_title(ss),
        "level": ss.w_level,
        "company": ss.w_company.strip(),
        "interview_type": ss.w_interview_type or "Mixed",
        "num_questions": ss.w_num_questions,
        "job_description": ss.w_job_description.strip()[:MAX_JD_CHARS],
    }
    ss.setup_complete = True
    ss.started_at = time.time()


# ---------- CV autofill ----------
CV_PROMPT = (
    "You extract candidate details from a CV/resume. Respond with JSON only, in exactly this "
    "structure:\n"
    "{\n"
    '  "name": "<full name, or empty string>",\n'
    '  "experience": "<2-4 sentence summary of work experience and notable projects, '
    'under 450 characters>",\n'
    '  "skills": ["<skill>", ...],\n'
    '  "grad_year": <graduation year as an integer, or null>,\n'
    f'  "position": "<one of: {", ".join(POSITIONS)}>",\n'
    '  "custom_position": "<job title if position is Other, else empty string>",\n'
    f'  "level": "<one of: {", ".join(LEVELS)}>"\n'
    "}\n"
    "List at most 12 of the most relevant skills that the CV explicitly mentions, each a "
    "short name; don't add skills that aren't written in the CV. "
    "Infer position and level from the most recent roles and years of experience. "
    "Use only information in the CV; leave a field empty if it isn't there."
)


def cv_text(uploaded):
    data = uploaded.getvalue()
    name = uploaded.name.lower()
    if name.endswith(".pdf"):
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    elif name.endswith(".docx"):
        text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
    else:
        text = data.decode("utf-8", errors="ignore")
    return text.strip()[:MAX_CV_CHARS]


def autofill_from_cv():
    """Runs as the uploader's on_change callback, so it may set widget values."""
    ss = st.session_state
    ss.cv_status = None
    uploaded = ss.w_cv
    if uploaded is None:
        return
    try:
        text = cv_text(uploaded)
    except Exception:
        ss.cv_status = ("error", "Couldn't read that file. Try a PDF, Word (.docx), or text file.")
        return
    if len(text) < 50:
        ss.cv_status = ("error", "No readable text found in that file. If it's a scanned PDF, "
                                 "try a text-based PDF or a Word file.")
        return
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": CV_PROMPT}, {"role": "user", "content": text}],
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        ss.cv_status = ("error", "Couldn't understand the CV details. Please try again.")
        return
    except Exception as err:
        ss.cv_status = ("error", friendly_error(err))
        return

    filled = []
    for key, field, limit in [("name", "w_name", 50), ("experience", "w_experience", 500)]:
        value = str(data.get(key) or "").strip()
        if value:
            ss[field] = value[:limit]
            filled.append(key)
    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = skills.split(",")
    skills = list(dict.fromkeys(str(s).strip()[:40] for s in skills if str(s).strip()))[:12]
    if skills:
        ss.w_skills = skills
        filled.append("skills")
    try:
        year = int(data.get("grad_year"))
        if 1970 <= year <= 2035:
            ss.w_grad_year = year
            filled.append("graduation year")
    except (TypeError, ValueError):
        pass
    if data.get("position") in POSITIONS:
        ss.w_position = data["position"]
        if data["position"] == "Other":
            ss.w_custom_position = str(data.get("custom_position") or "").strip()[:60]
        filled.append("position")
    if data.get("level") in LEVELS:
        ss.w_level = data["level"]
        filled.append("level")

    if filled:
        ss.cv_status = ("success", f"Filled in from your CV: {', '.join(filled)}. "
                                   "Review and edit anything below.")
    else:
        ss.cv_status = ("warning", "Couldn't find profile details in that file.")


def show_feedback():
    st.session_state.feedback_shown = True


def end_early():
    ss = st.session_state
    ss.chat_complete = True
    ss.ended_early = True
    ss.ended_at = time.time()
    ss.feedback_shown = True


def retry_feedback():
    st.session_state.feedback = None


def restart():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------- Prompts ----------
def interviewer_prompt(p):
    background = [
        f"Experience: {p['experience']}",
        f"Skills: {p['skills']}",
    ]
    if p["grad_year"]:
        background.append(f"Graduation year: {p['grad_year']}")
    jd = f"\n\nJob description:\n{p['job_description']}" if p["job_description"] else ""
    return (
        f"You are {INTERVIEWER_NAME}, an experienced interviewer at {p['company']}, conducting a "
        f"{p['interview_type'].lower()} interview with {p['name']} for the {p['level']} "
        f"{p['position']} role.\n\n"
        "Candidate background:\n" + "\n".join(background) + jd + "\n\n"
        "Rules:\n"
        f"- When introducing yourself, use the name {INTERVIEWER_NAME}. Never use placeholders "
        "like [Interviewer Name] or [Company] - always use the real names given here.\n"
        f"- {INTERVIEW_TYPES[p['interview_type']]}\n"
        "- Never ask coding questions: do not ask the candidate to write, read, debug, or "
        "complete code, pseudocode, SQL, or algorithms. Technical questions must be "
        "conceptual and answerable verbally (explain a concept, compare approaches, walk "
        "through how you would design or troubleshoot something).\n"
        f"- Ask exactly {p['num_questions']} questions in total, one at a time. The session "
        f"lasts about {p['num_questions'] * MINUTES_PER_QUESTION} minutes; if you mention its "
        "length, use that.\n"
        f"- Match the difficulty to a {p['level']} level candidate.\n"
        "- Briefly acknowledge each answer before the next question. Do not give scores or "
        "detailed feedback during the interview.\n"
        "- Keep each reply under 80 words.\n"
        "- Stay in your role as interviewer. If the candidate goes off topic, politely steer "
        "back to the interview."
    )


def evaluator_prompt(p):
    return (
        "You are an expert interview evaluator. Below is the transcript of a "
        f"{p['interview_type'].lower()} interview for a {p['level']} {p['position']} role at "
        f"{p['company']}. Evaluate only the Candidate's answers, calibrated to the {p['level']} "
        "level. Be honest and specific: short, vague, or off-topic answers should score low.\n\n"
        "Respond with JSON only, in exactly this structure:\n"
        "{\n"
        '  "overall_score": <integer 1-10>,\n'
        '  "summary": "<2-3 sentence overall assessment>",\n'
        '  "scores": {"communication": <1-10>, "technical_depth": <1-10>, '
        '"relevance": <1-10>, "confidence": <1-10>},\n'
        '  "strengths": ["<strength>", ...],\n'
        '  "improvements": ["<concrete thing to improve>", ...],\n'
        '  "questions": [\n'
        '    {"question": "<interviewer question>", "feedback": "<feedback on the answer>", '
        '"better_answer": "<a short example of a stronger answer>"}\n'
        "  ]\n"
        "}\n"
        "Include one entry in \"questions\" for every question the candidate answered."
    )


HINT_PROMPT = (
    "You are a friendly interview coach helping a candidate during a practice interview. "
    "Given the interviewer's latest message, give 2-3 short bullet-point tips on how to "
    "structure a strong answer (what to mention, which framework to use, what to avoid). "
    "Do NOT write the answer for them. Keep it under 60 words. Use markdown bullets."
)


def api_messages(final_answer=False):
    msgs = [{"role": "system", "content": interviewer_prompt(st.session_state.profile)}, KICKOFF_MESSAGE]
    msgs += st.session_state.messages
    if final_answer:
        msgs.append(FINAL_NOTE)
    return msgs


def stream_reply(messages):
    stream = client.chat.completions.create(
        model=CHAT_MODEL, messages=messages, stream=True, reasoning_effort="low",
    )
    return st.write_stream(chunk.choices[0].delta.content or "" for chunk in stream)


def get_hint():
    p = st.session_state.profile
    question = st.session_state.messages[-1]["content"]
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": HINT_PROMPT},
            {"role": "user", "content": f"Role: {p['level']} {p['position']} at {p['company']}\n\n"
                                        f"Interviewer said:\n{question}"},
        ],
        reasoning_effort="low",
    )
    return response.choices[0].message.content.strip()


def transcript_text():
    return "\n\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
        for m in st.session_state.messages
    )


def answer_stats():
    answers = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    words = [len(a.split()) for a in answers]
    avg = round(sum(words) / len(words)) if words else 0
    start = st.session_state.started_at or time.time()
    end = st.session_state.ended_at or time.time()
    return len(answers), avg, end - start


def clamp_score(value):
    try:
        return max(1, min(10, int(round(float(value)))))
    except (TypeError, ValueError):
        return 1


def parse_feedback(raw):
    data = json.loads(raw)
    return {
        "overall_score": clamp_score(data.get("overall_score")),
        "summary": str(data.get("summary", "")),
        "scores": {k: clamp_score(data.get("scores", {}).get(k)) for k in SCORE_CATEGORIES},
        "strengths": [str(s) for s in data.get("strengths", [])],
        "improvements": [str(s) for s in data.get("improvements", [])],
        "questions": [q for q in data.get("questions", []) if isinstance(q, dict)],
    }


def build_report(p, fb):
    answered, avg_words, duration = answer_stats()
    lines = [
        f"# Interview Report: {p['name']}",
        "",
        f"- **Role:** {p['level']} {p['position']} at {p['company']}",
        f"- **Interview type:** {p['interview_type']}",
        f"- **Date:** {datetime.now():%Y-%m-%d %H:%M}",
        f"- **Questions answered:** {answered} of {p['num_questions']}",
        f"- **Duration:** {fmt_duration(duration)}",
        f"- **Average answer length:** {avg_words} words",
        "",
        f"## Overall score: {fb['overall_score']}/10",
        "",
        fb["summary"],
        "",
        "## Scores",
    ]
    lines += [f"- {label}: {fb['scores'][k]}/10" for k, (label, _) in SCORE_CATEGORIES.items()]
    lines += ["", "## Strengths"] + [f"- {s}" for s in fb["strengths"]]
    lines += ["", "## Areas to improve"] + [f"- {s}" for s in fb["improvements"]]
    lines += ["", "## Question-by-question feedback"]
    for i, q in enumerate(fb["questions"], 1):
        lines += [
            "",
            f"### {i}. {q.get('question', '')}",
            "",
            f"**Feedback:** {q.get('feedback', '')}",
            "",
            f"**Stronger answer:** {q.get('better_answer', '')}",
        ]
    lines += ["", "## Transcript", "", transcript_text()]
    return "\n".join(lines)


def session_card(p):
    ss = st.session_state
    elapsed = (ss.ended_at or time.time()) - ss.started_at
    return (
        '<div class="tipcard">'
        f'<div class="k">Candidate</div><div class="v">{esc(p["name"])}</div>'
        f'<div class="k">Role</div><div class="v">{esc(p["level"])} {esc(p["position"])}</div>'
        f'<div class="k">Company</div><div class="v">{esc(p["company"])}</div>'
        f'<div class="k">Format</div><div class="v">{esc(p["interview_type"])} · '
        f'{p["num_questions"]} questions</div>'
        f'<div class="k">Time</div><div class="v" style="margin-bottom:0">⏱️ {fmt_duration(elapsed)}</div>'
        '</div>'
    )


# =====================================================================
# ---------- Setup ----------
# =====================================================================
if not st.session_state.setup_complete:
    if "setup_title" not in st.session_state:  
        st.session_state.setup_title = random.choice(SETUP_TITLES)
    page_header("New interview", st.session_state.setup_title,
                "Configure your session. Questions are generated from your profile and target role.")
    rail_col, main_col = st.columns([1, 3.1], gap="medium")
    with rail_col:
        step_rail(0, STAR_CARD)

    with main_col, st.container(key="card_setup"):
        ss = st.session_state

        # Your profile
        section_h("Your profile")
        st.file_uploader("Autofill from CV · :gray[Optional]", type=["pdf", "docx", "txt"],
                         key="w_cv", on_change=autofill_from_cv,
                         help="Upload your CV and we'll fill in your name, experience, skills, "
                              "graduation year, position and level. You can edit everything after.")
        if ss.cv_status:
            kind, msg = ss.cv_status
            getattr(st, kind)(msg)

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Full name", key="w_name", max_chars=50, placeholder="Ahmed Ismail")
        with c2:
            st.number_input("Graduation year · :gray[Optional]", key="w_grad_year",
                            min_value=1970, max_value=2035, value=None, step=1, placeholder="2024")
        st.text_area("Experience", key="w_experience", max_chars=500, height=90,
                     placeholder="2 years as a data analyst at a fintech startup; built KPI dashboards...")
        st.multiselect("Skills", sorted(set(COMMON_SKILLS) | set(ss.w_skills), key=str.lower),
                       key="w_skills", accept_new_options=True, max_selections=15,
                       placeholder="Add skill...")

        split()

        # Target role
        section_h("Target role")
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Position", POSITIONS, key="w_position")
            if ss.w_position == "Other":
                st.text_input("Position title", key="w_custom_position", max_chars=60,
                              placeholder="e.g. DevOps Engineer")
            else:
                ss.w_custom_position = ""
        with c2:
            st.segmented_control("Level", LEVELS, key="w_level", selection_mode="single",
                                 width="stretch")
            st.text_input("Company", key="w_company", max_chars=100, placeholder="e.g. Google")

        c1, c2 = st.columns(2)
        with c1, st.container(key="qtype"):
            st.radio("Question type", list(INTERVIEW_TYPES), key="w_interview_type", width="stretch",
                     format_func=lambda t: f"{t}  :blue-badge[Recommended]" if t == "Mixed" else t)
        with c2:
            st.selectbox("Length", list(range(3, 11)), key="w_num_questions",
                         format_func=lambda n: f"{n} questions · ~{n * MINUTES_PER_QUESTION} min")
            n = ss.w_num_questions
            role = position_title(ss) or "custom role"
            html_block(
                f'<div class="summary-box">Your session: <b>{esc(ss.w_level or "")} {esc(role)}</b>, '
                f'{esc(ss.w_interview_type.lower())} questions, about '
                f'{n * MINUTES_PER_QUESTION} minutes.</div>'
            )

        with st.expander("Job description · Optional"):
            st.text_area("Job description", key="w_job_description", max_chars=MAX_JD_CHARS,
                         height=110, label_visibility="collapsed",
                         placeholder="Paste the job posting so questions match the real role")

        missing = [
            label for label, ok in [
                ("full name", ss.w_name.strip()), ("experience", ss.w_experience.strip()),
                ("skills", ss.w_skills), ("level", ss.w_level), ("company", ss.w_company.strip()),
                ("position title", ss.w_position != "Other" or ss.w_custom_position.strip()),
            ] if not ok
        ]
        with st.container(key="footer"):
            f1, f2, f3 = st.columns([5, 1.2, 1.8], vertical_alignment="center")
            with f1:
                if missing:
                    st.caption("Still needed: " + ", ".join(missing))
            with f2:
                st.button("Cancel", on_click=restart, width="stretch", help="Clear the form")
            with f3:
                st.button("Start interview", on_click=complete_setup, type="primary",
                          disabled=bool(missing), width="stretch")

# =====================================================================
# ---------- Interview ----------
# =====================================================================
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    p = st.session_state.profile
    total = p["num_questions"]
    page_header("Interview", f"{p['level']} {p['position']} interview",
                f"Answer one question at a time. {INTERVIEWER_NAME} will ask {total} questions.")
    rail_col, main_col = st.columns([1, 3.1], gap="medium")

    with rail_col:
        step_rail(1, session_card(p) + STAR_CARD)
        html_block('<div class="gap"></div>')
        if not st.session_state.chat_complete and st.session_state.answer_count >= 1:
            st.button("End & get feedback", on_click=end_early, width="stretch",
                      help="Finish now and get feedback on the questions you've answered.")
        st.button("Start over", on_click=restart, width="stretch")

    with main_col, st.container(key="card_chat"):
        html_block(
            f'<div class="chips"><span class="chip accent">{esc(p["level"])} {esc(p["position"])}</span>'
            f'<span class="chip">🏢 {esc(p["company"])}</span>'
            f'<span class="chip">{esc(p["interview_type"])} interview</span></div>'
        )
        answered = st.session_state.answer_count
        st.progress(answered / total, text=f"Question {min(answered + 1, total)} of {total}"
                    if not st.session_state.chat_complete else f"All {total} questions answered")

        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
                st.markdown(message["content"])

        # Interviewer opens the conversation
        if not st.session_state.messages:
            with st.chat_message("assistant", avatar=AVATARS["assistant"]):
                try:
                    reply = stream_reply(api_messages())
                except Exception as err:
                    st.error(friendly_error(err))
                    st.button("Try again")
                    st.stop()
            st.session_state.messages.append({"role": "assistant", "content": reply})

        if not st.session_state.chat_complete:
            hint = st.session_state.hint
            if hint and hint[0] == st.session_state.answer_count:
                st.info(hint[1], icon="💡")
            elif st.button("💡 Need a hint?", help="Get coaching tips for this question without the answer."):
                with st.spinner("Thinking of some tips..."):
                    try:
                        st.session_state.hint = (st.session_state.answer_count, get_hint())
                        st.rerun()
                    except Exception as err:
                        st.error(friendly_error(err))

            if prompt := st.chat_input("Type your answer...", max_chars=MAX_ANSWER_CHARS):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user", avatar=AVATARS["user"]):
                    st.markdown(prompt)

                is_final = st.session_state.answer_count + 1 >= total
                with st.chat_message("assistant", avatar=AVATARS["assistant"]):
                    try:
                        reply = stream_reply(api_messages(final_answer=is_final))
                    except Exception as err:
                        st.session_state.messages.pop()  # let the user resend the answer
                        st.error(friendly_error(err) + " Your answer wasn't sent, so please submit it again.")
                        st.stop()

                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.session_state.answer_count += 1
                if is_final:
                    st.session_state.chat_complete = True
                    st.session_state.ended_at = time.time()
                st.rerun()

        if st.session_state.chat_complete:
            st.success("Interview complete! Great job making it through. 🎉")
            st.button("Get my feedback", on_click=show_feedback, type="primary", width="stretch")

# =====================================================================
# ---------- Feedback ----------
# =====================================================================
if st.session_state.feedback_shown:
    p = st.session_state.profile
    page_header("Feedback", "Your interview feedback",
                f"{p['level']} {p['position']} at {p['company']} · {p['interview_type']} interview")
    rail_col, main_col = st.columns([1, 3.1], gap="medium")
    with rail_col:
        step_rail(2, session_card(p))
        html_block('<div class="gap"></div>')
        st.button("New interview", on_click=restart, width="stretch")

    with main_col:
        if st.session_state.feedback is None:
            with st.spinner("Evaluating your interview... this takes a few seconds."):
                transcript = transcript_text()
                if st.session_state.ended_early:
                    transcript += ("\n\n[The candidate ended the interview early. Ignore any final "
                                   "interviewer question that has no answer.]")
                try:
                    response = client.chat.completions.create(
                        model=EVAL_MODEL,
                        messages=[
                            {"role": "system", "content": evaluator_prompt(p)},
                            {"role": "user", "content": transcript},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.3,
                    )
                    st.session_state.feedback = parse_feedback(response.choices[0].message.content)
                except (json.JSONDecodeError, AttributeError):
                    st.error("The evaluation came back in an unexpected format.")
                except Exception as err:
                    st.error(friendly_error(err))
            if st.session_state.feedback is None:
                st.button("Try again", on_click=retry_feedback, type="primary")
                st.stop()

        fb = st.session_state.feedback
        overall = fb["overall_score"]
        color = score_color(overall)

        # Overall score
        with st.container(key="card_score"):
            html_block(
                f"""
<div class="score-wrap">
  <div class="ring" style="--p:{overall * 10}; --c:{color};">
    <div class="inner"><div><div class="num">{overall}</div><div class="den">out of 10</div></div></div>
  </div>
  <div style="flex:1; min-width:220px;">
    <div class="verdict" style="color:{color}">{verdict(overall)}</div>
    <div class="summary">{esc(fb['summary'])}</div>
  </div>
</div>
"""
            )

        # Stats
        answered, avg_words, duration = answer_stats()
        html_block(
            f"""
<div class="stats">
  <div class="stat"><div class="v">{answered}/{p['num_questions']}</div><div class="l">Questions answered</div></div>
  <div class="stat"><div class="v">{fmt_duration(duration)}</div><div class="l">Total time</div></div>
  <div class="stat"><div class="v">{avg_words}</div><div class="l">Avg. words / answer</div></div>
</div>
"""
        )

        # Category breakdown
        with st.container(key="card_breakdown"):
            section_h("Score breakdown")
            bars = []
            for key, (label, icon) in SCORE_CATEGORIES.items():
                score = fb["scores"][key]
                c = score_color(score)
                bars.append(
                    f'<div class="cat"><div class="top"><span>{icon} {label}</span>'
                    f'<span class="val" style="color:{c}">{score}/10</span></div>'
                    f'<div class="bar"><span style="width:{score * 10}%; background:{c}"></span></div></div>'
                )
            html_block("".join(bars))
        html_block('<div class="gap"></div>')

        # Strengths / improvements
        def pill_list(items, c):
            items = items or ["None identified."]
            lis = "".join(f"<li>{esc(s)}</li>" for s in items)
            return f'<ul class="pill-list" style="--c:{c}">{lis}</ul>'

        col_s, col_i = st.columns(2)
        with col_s, st.container(key="card_strengths"):
            section_h("✅ Strengths")
            html_block(pill_list(fb["strengths"], "#16A34A"))
        with col_i, st.container(key="card_improve"):
            section_h("📈 Areas to improve")
            html_block(pill_list(fb["improvements"], "#D97706"))
        html_block('<div class="gap"></div>')

        if fb["questions"]:
            with st.container(key="card_questions"):
                section_h("Question-by-question")
                for i, q in enumerate(fb["questions"], 1):
                    with st.expander(f"**Q{i}.** {q.get('question', 'Question')}"):
                        st.markdown(f"**📝 Feedback**\n\n{q.get('feedback', '')}")
                        st.success(f"**✨ Stronger answer**\n\n{q.get('better_answer', '')}")
            html_block('<div class="gap"></div>')

        with st.expander("💬 Full transcript"):
            for m in st.session_state.messages:
                with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
                    st.markdown(m["content"])

        safe_name = "".join(c for c in p["name"] if c.isalnum() or c in " -_").strip().replace(" ", "_") or "candidate"
        col_d, col_j = st.columns(2)
        with col_d:
            st.download_button(
                "⬇️ Report (.md)",
                data=build_report(p, fb),
                file_name=f"interview_report_{safe_name}.md",
                mime="text/markdown",
                type="primary",
                width="stretch",
            )
        with col_j:
            st.download_button(
                "⬇️ Data (.json)",
                data=json.dumps({"profile": p, "feedback": fb, "transcript": st.session_state.messages},
                                indent=2, default=str),
                file_name=f"interview_{safe_name}.json",
                mime="application/json",
                width="stretch",
            )

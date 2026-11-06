import html
import json
import time
from datetime import datetime

import groq
import streamlit as st
from groq import Groq

st.set_page_config(page_title="HR Chatbot · Interview Coach", page_icon="🎯", layout="centered")

# ---------- Config ----------
CHAT_MODEL = "openai/gpt-oss-20b"     # fast model for the live interview and hints
EVAL_MODEL = "openai/gpt-oss-120b"    # stronger model for grading

POSITIONS = ["Software Engineer", "Data Scientist", "Product Manager", "Designer", "Other"]
LEVELS = ["Intern", "Junior", "Mid", "Senior", "Lead"]
INTERVIEWER_NAME = "Jon"

INTERVIEW_TYPES = {
    "Behavioral": "Focus on behavioral questions about past experiences, teamwork, conflict, "
                  "and motivation. Encourage answers in the STAR format.",
    "Technical": "Focus on conceptual technical questions about the skills and knowledge the "
                 "role requires, including problem-solving and practical scenarios, answered "
                 "verbally without writing code.",
    "Mixed": "Mix behavioral and technical questions.",
}
SCORE_CATEGORIES = {
    "communication": ("Communication", "🗣️"),
    "technical_depth": ("Technical depth", "🧠"),
    "relevance": ("Relevance", "🎯"),
    "confidence": ("Confidence", "💪"),
}
MAX_ANSWER_CHARS = 1500
MAX_JD_CHARS = 3000
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

html, body, [class*="css"], .stMarkdown, button, input, textarea {
    font-family: 'Inter', sans-serif !important;
}
.stApp {
    background:
        radial-gradient(900px 500px at 10% -10%, rgba(139, 92, 246, 0.18), transparent 60%),
        radial-gradient(800px 500px at 110% 10%, rgba(34, 211, 238, 0.12), transparent 60%),
        #0B0F1A;
}
.block-container { padding-top: 2.2rem; padding-bottom: 6rem; }
header[data-testid="stHeader"] { background: transparent; }

/* Hero */
.hero { text-align: center; margin-bottom: 1.4rem; }
.hero .badge {
    display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 0.78rem;
    font-weight: 600; letter-spacing: .04em; color: #C4B5FD;
    background: rgba(139, 92, 246, 0.14); border: 1px solid rgba(139, 92, 246, 0.35);
}
.hero h1 {
    font-size: 2.6rem; font-weight: 800; margin: .6rem 0 .3rem; line-height: 1.15;
    background: linear-gradient(90deg, #A78BFA 0%, #60A5FA 50%, #22D3EE 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { color: #9AA3B8; font-size: 1.02rem; margin: 0; }

/* Stepper */
.stepper { display: flex; justify-content: center; gap: .5rem; margin: 0 0 1.6rem; flex-wrap: wrap; }
.step {
    display: flex; align-items: center; gap: .45rem; padding: 6px 14px; border-radius: 999px;
    font-size: .85rem; color: #6B7280; background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
}
.step .dot {
    width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
    font-size: .72rem; font-weight: 700; background: rgba(255,255,255,0.06);
}
.step.active { color: #EDE9FE; border-color: rgba(139,92,246,.55); background: rgba(139,92,246,.16); }
.step.active .dot { background: #8B5CF6; color: white; }
.step.done { color: #A7F3D0; }
.step.done .dot { background: rgba(52, 211, 153, .25); color: #34D399; }

/* Cards and containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(21, 27, 44, 0.65);
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(6px);
}
.section-title { display: flex; align-items: center; gap: .55rem; font-weight: 700;
    font-size: 1.05rem; margin: .2rem 0 .6rem; color: #E6E8F0; }
.section-title .icon { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
    background: linear-gradient(135deg, rgba(139,92,246,.35), rgba(34,211,238,.25)); }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
div[data-baseweb="select"] > div {
    border-radius: 10px !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: 10px; font-weight: 600; transition: transform .08s ease, box-shadow .2s ease;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: linear-gradient(90deg, #8B5CF6, #6366F1); border: none;
    box-shadow: 0 6px 20px rgba(139, 92, 246, .35);
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    transform: translateY(-1px); box-shadow: 0 10px 26px rgba(139, 92, 246, .5);
}
.stButton > button:disabled { box-shadow: none !important; opacity: .45; }

/* Role chips */
.chips { display: flex; gap: .45rem; flex-wrap: wrap; margin-bottom: .8rem; }
.chip { padding: 4px 11px; border-radius: 999px; font-size: .8rem; font-weight: 500;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09); color: #CBD2E1; }
.chip.accent { background: rgba(139,92,246,.16); border-color: rgba(139,92,246,.4); color: #DDD6FE; }

/* Chat */
div[data-testid="stChatMessage"] {
    border-radius: 16px; padding: .8rem 1rem; margin-bottom: .55rem;
    background: rgba(21, 27, 44, 0.75); border: 1px solid rgba(255,255,255,0.06);
}
div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]),
div[data-testid="stChatMessage"][aria-label="Chat message from user"] {
    background: linear-gradient(135deg, rgba(139,92,246,.18), rgba(99,102,241,.12));
    border-color: rgba(139,92,246,.3);
}
div[data-testid="stChatInput"] { border-radius: 14px; }

/* Progress bars */
div[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, #8B5CF6, #22D3EE) !important;
}

/* Score ring */
.score-wrap { display: flex; align-items: center; gap: 1.6rem; flex-wrap: wrap; }
.ring {
    --size: 150px; width: var(--size); height: var(--size); border-radius: 50%; flex-shrink: 0;
    display: grid; place-items: center;
    background: conic-gradient(var(--c) calc(var(--p) * 1%), rgba(255,255,255,0.07) 0);
}
.ring .inner {
    width: calc(var(--size) - 22px); height: calc(var(--size) - 22px); border-radius: 50%;
    background: #111727; display: grid; place-items: center; text-align: center;
}
.ring .num { font-size: 2.4rem; font-weight: 800; line-height: 1; color: #F3F4F6; }
.ring .den { font-size: .85rem; color: #8B93A7; }
.verdict { font-size: 1.35rem; font-weight: 700; margin-bottom: .3rem; }
.summary { color: #B6BED0; line-height: 1.55; }

/* Category bars */
.cat { margin-bottom: .85rem; }
.cat .top { display: flex; justify-content: space-between; font-size: .9rem; margin-bottom: .3rem; }
.cat .top .val { font-weight: 700; }
.bar { height: 9px; border-radius: 999px; background: rgba(255,255,255,0.07); overflow: hidden; }
.bar > span { display: block; height: 100%; border-radius: 999px; }

/* Stat tiles */
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; margin: .4rem 0 1rem; }
.stat { padding: .8rem; border-radius: 14px; text-align: center;
    background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07); }
.stat .v { font-size: 1.35rem; font-weight: 700; color: #F3F4F6; }
.stat .l { font-size: .78rem; color: #8B93A7; margin-top: .15rem; }

/* Lists */
.pill-list { list-style: none; padding: 0; margin: 0; }
.pill-list li { padding: .55rem .75rem; border-radius: 10px; margin-bottom: .45rem; font-size: .93rem;
    line-height: 1.45; background: rgba(255,255,255,0.035); border-left: 3px solid var(--c); }

/* Sidebar */
section[data-testid="stSidebar"] { background: #0E1322; border-right: 1px solid rgba(255,255,255,0.06); }
.side-card { padding: .85rem; border-radius: 12px; margin-bottom: .8rem;
    background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07); font-size: .9rem; }
.side-card .k { color: #8B93A7; font-size: .76rem; text-transform: uppercase; letter-spacing: .05em; }
.side-card .v { color: #E6E8F0; font-weight: 600; margin-bottom: .45rem; }

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .stats { grid-template-columns: 1fr 1fr 1fr; gap: .4rem; }
    .ring { --size: 120px; }
}
</style>
""",
    unsafe_allow_html=True,
)


def esc(text):
    return html.escape(str(text))


def hero():
    st.markdown(
        """
<div class="hero">
  <span class="badge">AI INTERVIEW COACH</span>
  <h1>Ace your next interview</h1>
  <p>Practice with a realistic AI interviewer, then get scored, actionable feedback.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def stepper(active):
    steps = ["Setup", "Interview", "Feedback"]
    parts = []
    for i, name in enumerate(steps):
        state = "active" if i == active else "done" if i < active else ""
        mark = "✓" if i < active else str(i + 1)
        parts.append(f'<div class="step {state}"><span class="dot">{mark}</span>{name}</div>')
    st.markdown(f'<div class="stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def section_title(icon, text):
    st.markdown(f'<div class="section-title"><span class="icon">{icon}</span>{esc(text)}</div>',
                unsafe_allow_html=True)


def score_color(score):
    if score >= 8:
        return "#34D399"
    if score >= 6:
        return "#A78BFA"
    if score >= 4:
        return "#FBBF24"
    return "#F87171"


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


# ---------- API client ----------
def get_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = None
    if not api_key:
        hero()
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
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def complete_setup():
    ss = st.session_state
    position = ss.w_custom_position.strip() if ss.w_position == "Other" else ss.w_position
    ss.profile = {
        "name": ss.w_name.strip(),
        "experience": ss.w_experience.strip(),
        "skills": ss.w_skills.strip(),
        "grad_year": ss.w_grad_year,
        "position": position,
        "level": ss.w_level,
        "company": ss.w_company.strip(),
        "interview_type": ss.w_interview_type or "Mixed",
        "num_questions": ss.w_num_questions,
        "job_description": ss.w_job_description.strip()[:MAX_JD_CHARS],
    }
    ss.setup_complete = True
    ss.started_at = time.time()


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
        f"- Ask exactly {p['num_questions']} questions in total, one at a time.\n"
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


# ---------- Sidebar ----------
def sidebar():
    ss = st.session_state
    with st.sidebar:
        st.markdown("### 🎯 Interview Coach")
        if ss.setup_complete:
            p = ss.profile
            elapsed = (ss.ended_at or time.time()) - ss.started_at
            st.markdown(
                f"""
<div class="side-card">
  <div class="k">Candidate</div><div class="v">{esc(p['name'])}</div>
  <div class="k">Role</div><div class="v">{esc(p['level'])} {esc(p['position'])}</div>
  <div class="k">Company</div><div class="v">{esc(p['company'])}</div>
  <div class="k">Format</div><div class="v">{esc(p['interview_type'])} · {p['num_questions']} questions</div>
  <div class="k">Time</div><div class="v" style="margin-bottom:0">⏱️ {fmt_duration(elapsed)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            if not ss.chat_complete and ss.answer_count >= 1:
                st.button("⏹️ End & get feedback", on_click=end_early, width="stretch",
                          help="Finish now and get feedback on the questions you've answered.")
            st.button("🔄 Start over", on_click=restart, width="stretch")
        else:
            st.caption("Fill in your details to start a tailored mock interview.")

        st.markdown("---")
        with st.expander("⭐ The STAR method", expanded=not ss.setup_complete):
            st.markdown(
                "- **Situation** — set the scene briefly\n"
                "- **Task** — what you were responsible for\n"
                "- **Action** — what *you* did, step by step\n"
                "- **Result** — the outcome, with numbers if possible"
            )
        with st.expander("💡 Interview tips"):
            st.markdown(
                "- Aim for 1–2 minute answers (≈100–250 words)\n"
                "- Use concrete examples, not generalities\n"
                "- Quantify impact: %, time saved, users, revenue\n"
                "- It's fine to ask a clarifying question\n"
                "- Stuck? Use the **Hint** button for guidance"
            )


sidebar()
hero()

# ---------- Setup form ----------
if not st.session_state.setup_complete:
    stepper(0)

    with st.container(border=True):
        section_title("👤", "About you")
        st.text_input("Name *", key="w_name", max_chars=50, placeholder="e.g. Ahmed Ismail")
        st.text_area("Experience *", key="w_experience", max_chars=500, height=100,
                     placeholder="e.g. 2 years as a data analyst at a fintech startup, built dashboards...")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.text_input("Skills *", key="w_skills", max_chars=300,
                          placeholder="e.g. Python, SQL, machine learning, communication")
        with col_b:
            st.number_input("Graduation year", key="w_grad_year", min_value=1970,
                            max_value=2035, value=None, step=1, placeholder="Optional")

    with st.container(border=True):
        section_title("💼", "The role")
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Position *", POSITIONS, key="w_position")
        with col2:
            st.selectbox("Level *", LEVELS, key="w_level", index=1)
        if st.session_state.w_position == "Other":
            st.text_input("Position title *", key="w_custom_position", max_chars=60,
                          placeholder="e.g. DevOps Engineer")
        else:
            st.session_state.w_custom_position = ""
        st.text_input("Company *", key="w_company", max_chars=100, placeholder="e.g. Google")
        st.text_area("Job description (optional)", key="w_job_description", max_chars=MAX_JD_CHARS,
                     height=100, placeholder="Paste the job posting so questions match the real role")

    with st.container(border=True):
        section_title("⚙️", "Interview settings")
        st.segmented_control("Interview type", list(INTERVIEW_TYPES), key="w_interview_type",
                             default="Mixed", selection_mode="single")
        st.slider("Number of questions", 3, 10, 5, key="w_num_questions")

    ss = st.session_state
    missing = [
        label for label, value in [
            ("name", ss.w_name), ("experience", ss.w_experience), ("skills", ss.w_skills),
            ("company", ss.w_company),
            ("position title", ss.w_custom_position if ss.w_position == "Other" else "x"),
        ] if not value.strip()
    ]
    st.button("🚀 Start interview", on_click=complete_setup, type="primary",
              disabled=bool(missing), width="stretch")
    if missing:
        st.caption("Fill in required fields: " + ", ".join(missing))

# ---------- Interview ----------
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    stepper(1)
    p = st.session_state.profile
    total = p["num_questions"]
    st.markdown(
        f"""
<div class="chips">
  <span class="chip accent">{esc(p['level'])} {esc(p['position'])}</span>
  <span class="chip">🏢 {esc(p['company'])}</span>
  <span class="chip">{esc(p['interview_type'])} interview</span>
</div>
""",
        unsafe_allow_html=True,
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
        st.button("📊 Get my feedback", on_click=show_feedback, type="primary",
                  width="stretch")

# ---------- Feedback ----------
if st.session_state.feedback_shown:
    stepper(2)
    p = st.session_state.profile

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
            st.button("Restart interview", on_click=restart)
            st.stop()

    fb = st.session_state.feedback
    overall = fb["overall_score"]
    color = score_color(overall)

    # Overall score
    with st.container(border=True):
        st.markdown(
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
""",
            unsafe_allow_html=True,
        )

    # Stats
    answered, avg_words, duration = answer_stats()
    st.markdown(
        f"""
<div class="stats">
  <div class="stat"><div class="v">{answered}/{p['num_questions']}</div><div class="l">Questions answered</div></div>
  <div class="stat"><div class="v">{fmt_duration(duration)}</div><div class="l">Total time</div></div>
  <div class="stat"><div class="v">{avg_words}</div><div class="l">Avg. words / answer</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Category breakdown
    with st.container(border=True):
        section_title("📊", "Score breakdown")
        bars = []
        for key, (label, icon) in SCORE_CATEGORIES.items():
            score = fb["scores"][key]
            c = score_color(score)
            bars.append(
                f'<div class="cat"><div class="top"><span>{icon} {label}</span>'
                f'<span class="val" style="color:{c}">{score}/10</span></div>'
                f'<div class="bar"><span style="width:{score * 10}%; background:{c}"></span></div></div>'
            )
        st.markdown("".join(bars), unsafe_allow_html=True)

    # Strengths / improvements
    def pill_list(items, c):
        items = items or ["None identified."]
        lis = "".join(f"<li>{esc(s)}</li>" for s in items)
        return f'<ul class="pill-list" style="--c:{c}">{lis}</ul>'

    col_s, col_i = st.columns(2)
    with col_s:
        with st.container(border=True):
            section_title("✅", "Strengths")
            st.markdown(pill_list(fb["strengths"], "#34D399"), unsafe_allow_html=True)
    with col_i:
        with st.container(border=True):
            section_title("📈", "Areas to improve")
            st.markdown(pill_list(fb["improvements"], "#FBBF24"), unsafe_allow_html=True)

    if fb["questions"]:
        with st.container(border=True):
            section_title("🔍", "Question-by-question")
            for i, q in enumerate(fb["questions"], 1):
                with st.expander(f"**Q{i}.** {q.get('question', 'Question')}"):
                    st.markdown(f"**📝 Feedback**\n\n{q.get('feedback', '')}")
                    st.success(f"**✨ Stronger answer**\n\n{q.get('better_answer', '')}")

    with st.expander("💬 Full transcript"):
        for m in st.session_state.messages:
            with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
                st.markdown(m["content"])

    safe_name = "".join(c for c in p["name"] if c.isalnum() or c in " -_").strip().replace(" ", "_") or "candidate"
    col_d, col_j, col_r = st.columns(3)
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
    with col_r:
        st.button("🔁 New interview", on_click=restart, width="stretch")

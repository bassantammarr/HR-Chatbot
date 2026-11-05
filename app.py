import json
from datetime import datetime

import groq
import streamlit as st
from groq import Groq

st.set_page_config(page_title="HR Chatbot", page_icon="🤖")
st.title("HR Chatbot")
st.caption("Practice job interviews with an AI interviewer and get detailed feedback.")

# ---------- Config ----------
CHAT_MODEL = "openai/gpt-oss-20b"     # fast model for the live interview
EVAL_MODEL = "openai/gpt-oss-120b"    # stronger model for grading

POSITIONS = ["Software Engineer", "Data Scientist", "Product Manager", "Designer", "Other"]
LEVELS = ["Intern", "Junior", "Mid", "Senior", "Lead"]
INTERVIEW_TYPES = {
    "Behavioral": "Focus on behavioral questions about past experiences, teamwork, conflict, "
                  "and motivation. Encourage answers in the STAR format.",
    "Technical": "Focus on technical questions about the skills and knowledge the role requires, "
                 "including problem-solving and practical scenarios.",
    "Mixed": "Mix behavioral and technical questions.",
}
SCORE_CATEGORIES = {
    "communication": "Communication",
    "technical_depth": "Technical depth",
    "relevance": "Relevance",
    "confidence": "Confidence",
}
MAX_ANSWER_CHARS = 1500
MAX_JD_CHARS = 3000

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
    "messages": [],       
    "answer_count": 0,
    "profile": {},
    "feedback": None,
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
        "interview_type": ss.w_interview_type,
        "num_questions": ss.w_num_questions,
        "job_description": ss.w_job_description.strip()[:MAX_JD_CHARS],
    }
    ss.setup_complete = True


def show_feedback():
    st.session_state.feedback_shown = True


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
        f"You are an experienced interviewer at {p['company']}, conducting a "
        f"{p['interview_type'].lower()} interview with {p['name']} for the {p['level']} "
        f"{p['position']} role.\n\n"
        "Candidate background:\n" + "\n".join(background) + jd + "\n\n"
        "Rules:\n"
        f"- {INTERVIEW_TYPES[p['interview_type']]}\n"
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
        "Include one entry in \"questions\" for every question the interviewer asked."
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


def transcript_text():
    return "\n\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
        for m in st.session_state.messages
    )


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
    lines = [
        f"# Interview Report: {p['name']}",
        "",
        f"- **Role:** {p['level']} {p['position']} at {p['company']}",
        f"- **Interview type:** {p['interview_type']}",
        f"- **Date:** {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"## Overall score: {fb['overall_score']}/10",
        "",
        fb["summary"],
        "",
        "## Scores",
    ]
    lines += [f"- {label}: {fb['scores'][k]}/10" for k, label in SCORE_CATEGORIES.items()]
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


# ---------- Setup form ----------
if not st.session_state.setup_complete:
    st.subheader("About you")
    st.text_input("Name *", key="w_name", max_chars=50, placeholder="e.g. Sara Ahmed")
    st.text_area("Experience *", key="w_experience", max_chars=500,
                 placeholder="e.g. 2 years as a data analyst at a fintech startup, built dashboards...")
    st.text_area("Skills *", key="w_skills", max_chars=300,
                 placeholder="e.g. Python, SQL, machine learning, communication")
    st.number_input("Graduation year (optional)", key="w_grad_year", min_value=1970,
                    max_value=2035, value=None, step=1, placeholder="e.g. 2023")

    st.subheader("The role")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Position *", POSITIONS, key="w_position")
        if st.session_state.w_position == "Other":
            st.text_input("Position title *", key="w_custom_position", max_chars=60,
                          placeholder="e.g. DevOps Engineer")
        else:
            st.session_state.w_custom_position = ""
    with col2:
        st.selectbox("Level *", LEVELS, key="w_level", index=1)
    st.text_input("Company *", key="w_company", max_chars=100, placeholder="e.g. Google")
    st.text_area("Job description (optional)", key="w_job_description", max_chars=MAX_JD_CHARS,
                 placeholder="Paste the job posting so questions match the real role")

    st.subheader("Interview settings")
    col3, col4 = st.columns(2)
    with col3:
        st.radio("Interview type", list(INTERVIEW_TYPES), key="w_interview_type",
                 index=2, horizontal=True)
    with col4:
        st.slider("Number of questions", 3, 10, 5, key="w_num_questions")

    ss = st.session_state
    missing = [
        label for label, value in [
            ("name", ss.w_name), ("experience", ss.w_experience), ("skills", ss.w_skills),
            ("company", ss.w_company),
            ("position title", ss.w_custom_position if ss.w_position == "Other" else "x"),
        ] if not value.strip()
    ]
    st.button("Start interview", on_click=complete_setup, type="primary", disabled=bool(missing))
    if missing:
        st.caption("Fill in required fields: " + ", ".join(missing))

# ---------- Interview ----------
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    p = st.session_state.profile
    total = p["num_questions"]
    st.markdown(f"**{p['level']} {p['position']}** at **{p['company']}** · {p['interview_type']} interview")
    answered = st.session_state.answer_count
    st.progress(answered / total, text=f"Answered {answered} of {total} questions")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Interviewer opens the conversation
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            try:
                reply = stream_reply(api_messages())
            except Exception as err:
                st.error(friendly_error(err))
                st.button("Try again")
                st.stop()
        st.session_state.messages.append({"role": "assistant", "content": reply})

    if not st.session_state.chat_complete:
        if prompt := st.chat_input("Type your answer", max_chars=MAX_ANSWER_CHARS):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            is_final = st.session_state.answer_count + 1 >= total
            with st.chat_message("assistant"):
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
            st.rerun()

    if st.session_state.chat_complete:
        st.success("Interview complete!")
        st.button("Get feedback", on_click=show_feedback, type="primary")

# ---------- Feedback ----------
if st.session_state.feedback_shown:
    p = st.session_state.profile
    st.subheader("Your interview feedback")

    if st.session_state.feedback is None:
        with st.spinner("Evaluating your interview..."):
            try:
                response = client.chat.completions.create(
                    model=EVAL_MODEL,
                    messages=[
                        {"role": "system", "content": evaluator_prompt(p)},
                        {"role": "user", "content": transcript_text()},
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

    st.metric("Overall score", f"{fb['overall_score']}/10")
    if fb["summary"]:
        st.write(fb["summary"])

    cols = st.columns(len(SCORE_CATEGORIES))
    for col, (key, label) in zip(cols, SCORE_CATEGORIES.items()):
        with col:
            score = fb["scores"][key]
            st.markdown(f"**{label}**")
            st.progress(score / 10, text=f"{score}/10")

    col_s, col_i = st.columns(2)
    with col_s:
        st.markdown("#### ✅ Strengths")
        for s in fb["strengths"] or ["None identified."]:
            st.markdown(f"- {s}")
    with col_i:
        st.markdown("#### 📈 Areas to improve")
        for s in fb["improvements"] or ["None identified."]:
            st.markdown(f"- {s}")

    if fb["questions"]:
        st.markdown("#### Question-by-question")
        for i, q in enumerate(fb["questions"], 1):
            with st.expander(f"{i}. {q.get('question', 'Question')}"):
                st.markdown(f"**Feedback:** {q.get('feedback', '')}")
                st.markdown(f"**Stronger answer:** {q.get('better_answer', '')}")

    with st.expander("Full transcript"):
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

    safe_name = "".join(c for c in p["name"] if c.isalnum() or c in " -_").strip().replace(" ", "_") or "candidate"
    col_d, col_r = st.columns(2)
    with col_d:
        st.download_button(
            "Download report",
            data=build_report(p, fb),
            file_name=f"interview_report_{safe_name}.md",
            mime="text/markdown",
            type="primary",
        )
    with col_r:
        st.button("Start a new interview", on_click=restart)

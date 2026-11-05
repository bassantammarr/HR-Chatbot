import streamlit as st
from groq import Groq

st.set_page_config(page_title="HR Chatbot", page_icon="🤖")
st.title("HR Chatbot")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODEL = "llama-3.1-8b-instant"
MAX_USER_MESSAGES = 5

POSITIONS = ["Software Engineer", "Data Scientist", "Product Manager", "Designer"]
LEVELS = ["Intern", "Junior", "Mid", "Senior", "Lead"]

# ---------- Session state ----------
defaults = {
    "setup_complete": False,
    "user_message_count": 0,
    "feedback_shown": False,
    "chat_complete": False,
    "messages": [],
    "feedback": None,
    "name": "",
    "experience": "",
    "skills": "",
    "grad_year": 2024,
    "position": "Data Scientist",
    "level": "Junior",
    "company_name": "Amazon",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def complete_setup():
    st.session_state.setup_complete = True


def show_feedback():
    st.session_state.feedback_shown = True


def restart():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------- Setup form ----------
if not st.session_state.setup_complete:
    st.subheader("Personal information", divider="rainbow")

    st.session_state.name = st.text_input(
        "Name", value=st.session_state.name, max_chars=50,
        placeholder="Enter your name here",
    )
    st.session_state.experience = st.text_area(
        "Experience", value=st.session_state.experience, max_chars=200,
        placeholder="Describe your experience here",
    )
    st.session_state.skills = st.text_area(
        "Skills", value=st.session_state.skills, max_chars=200,
        placeholder="List your skills here",
    )
    st.session_state.grad_year = st.number_input(
        "Graduation year", min_value=1970, max_value=2035,
        value=st.session_state.grad_year, step=1,
    )

    st.subheader("Position and company details", divider="rainbow")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.position = st.selectbox(
            "Position", POSITIONS,
            index=POSITIONS.index(st.session_state.position),
        )
    with col2:
        st.session_state.level = st.radio(
            "Level", LEVELS,
            index=LEVELS.index(st.session_state.level),
        )

    st.session_state.company_name = st.text_input(
        "Company name", value=st.session_state.company_name, max_chars=100,
        placeholder="Enter the company name here",
    )

    st.button(
        "Start interview",
        on_click=complete_setup,
        disabled=not st.session_state.name.strip(),
    )

# ---------- Interview ----------
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    if not st.session_state.messages:
        st.session_state.messages = [{
            "role": "system",
            "content": (
                f"You are an HR executive interviewing a candidate named {st.session_state.name}. "
                f"Their experience: {st.session_state.experience}. "
                f"Their skills: {st.session_state.skills}. "
                f"They graduated in {st.session_state.grad_year}. "
                f"You are interviewing them for the {st.session_state.level} "
                f"{st.session_state.position} position at {st.session_state.company_name}. "
                "Ask one question at a time and keep your replies concise."
            ),
        }]

    st.info("Start by introducing yourself.")

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if not st.session_state.chat_complete:
        if prompt := st.chat_input("Your answer"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.user_message_count += 1

            # Show the user's message right away
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model=MODEL,
                    messages=st.session_state.messages,
                    stream=True,
                )
                reply = st.write_stream(
                    chunk.choices[0].delta.content or "" for chunk in stream
                )

            st.session_state.messages.append({"role": "assistant", "content": reply})

            if st.session_state.user_message_count >= MAX_USER_MESSAGES:
                st.session_state.chat_complete = True
                st.rerun()

    if st.session_state.chat_complete:
        st.button("Get feedback", on_click=show_feedback, type="primary")

# ---------- Feedback ----------
if st.session_state.feedback_shown:
    st.subheader("Feedback")

    if st.session_state.feedback is None:
        transcript = "\n".join(
            f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
            for m in st.session_state.messages
            if m["role"] != "system"
        )
        with st.spinner("Evaluating your interview..."):
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an interview evaluator. The transcript below is an interview "
                            f"for a {st.session_state.level} {st.session_state.position} role at "
                            f"{st.session_state.company_name}. Evaluate only the Candidate's answers.\n"
                            "Give a score from 1 to 10 and short feedback.\n"
                            "Format:\n"
                            "Overall Score: X/10\n"
                            "Feedback: ..."
                        ),
                    },
                    {"role": "user", "content": transcript},
                ],
            )
        st.session_state.feedback = response.choices[0].message.content

    st.write(st.session_state.feedback)

    st.button("Restart interview", on_click=restart)
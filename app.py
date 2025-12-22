from openai import OpenAI
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from groq import Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="HR Chatbot", page_icon="🤖")
st.title("HR Chatbot")

if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False
if "messages" not in st.session_state:
    st.session_state.messages = []


def complete_setup():
    st.session_state.setup_complete = True
def show_feedback():
    st.session_state.feedback_shown = True

if not st.session_state.setup_complete:

    st.subheader('personal information' , divider='rainbow')

    if'name' not in st.session_state:
        st.session_state['name'] = ''
    if'experience' not in st.session_state:
        st.session_state['experience'] = '' 
    if'skills' not in st.session_state:
        st.session_state['skills'] = ''





    st.session_state['name'] = st.text_input(label="Name" ,value=st.session_state['name'], max_chars=50 , placeholder="Enter your name here")
    st.session_state['experience'] = st.text_area(label="experience" , value=st.session_state['experience'] ,max_chars=200 , placeholder="Describe your experience here")
    st.session_state['skills'] = st.text_area(label="Skills" ,value=st.session_state['skills'] ,max_chars=200 , placeholder="List your skills here")
    st.session_state["Graduation Year"] = st.date_input("Graduation Year")


    st.subheader("position and company details" , divider='rainbow')
       
    if "level" not in st.session_state:
        st.session_state["level"] = "Junior"
    if "position" not in st.session_state:
        st.session_state["position"] = "Data Scientist"
    if "company_name" not in st.session_state:
        st.session_state["company_name"] = "Amazon"



    col1 , col2 = st.columns(2)
    with col1:
        position = st.selectbox(
        "Position",
        ("Software Engineer", "Data Scientist", "Product Manager", "Designer"))
            
        
    with col2:
        level = st.radio(
        "Level",
        key="visibility",
        options=["Intern", "Junior", "Mid", "Senior", "Lead"],

        )

    st.session_state["company_name"] = st.text_input(label="Company Name" , max_chars=100 , placeholder="Enter the company name here")




    if st.button(" Start Interviewing" , on_click=complete_setup):
        st.write("Setup Complete! You can now start the interview.")



if st.session_state.setup_complete and not st.session_state.feedback_shown and not st.session_state.chat_complete:
    st.info("start by introducing yourself.")
    

    

    if not st.session_state.messages:
        st.session_state.messages = [{
            "role": "system",
            "content": (f"You are an HR executive that interviews an interviewee called {st.session_state['name']} "
                        f"with experience {st.session_state['experience']} and skills {st.session_state['skills']}. "
                        f"You should interview him for the position {st.session_state['level']} {st.session_state['position']} "
                        f"with graduation year {st.session_state['Graduation Year']} "
                        f"at the company {st.session_state['company_name']}")
        }]      

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


    if not st.session_state.chat_complete:
        prompt = st.chat_input("Enter your message:")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.user_message_count += 1

        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=st.session_state.messages,
            )

            assistant_reply = response.choices[0].message.content
            st.markdown(assistant_reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_reply}
        )

        

        if st.session_state.user_message_count >= 5:
            st.session_state.chat_complete = True


if st.session_state.chat_complete and not st.session_state.feedback_shown:
    if st.button("Get Feedback"):
        st.session_state.feedback_shown = True

if st.session_state.feedback_shown:
    st.subheader("Feedback")

    conversation_history = "\n".join(
        [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
    )

    feedback = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an interview evaluator.\n"
                    "Give a score from 1 to 10 and short feedback.\n"
                    "Format:\n"
                    "Overall Score: X/10\n"
                    "Feedback: ..."
                )
            },
            {
                "role": "user",
                "content": conversation_history
            }
        ]
    )

    st.write(feedback.choices[0].message.content)

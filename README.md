# HR Chatbot: AI Interview Practice

Practice job interviews with an AI interviewer, then get a detailed, scored evaluation of your answers.

Built with [Streamlit](https://streamlit.io) and [Groq](https://groq.com) (open-source Qwen and GPT-OSS models).


## Features

- **Personalized interviews.** Tailored to your experience, skills, target role, level, and company.
- **Job description matching.** Paste a real job posting and the questions follow it.
- **Interview types.** Behavioral, technical, or mixed, with 3–10 questions.
- **Realistic flow.** The interviewer greets you, asks one question at a time, and closes the interview.
- **Detailed feedback.** An overall score, scores for communication, technical depth, relevance and confidence, strengths, areas to improve, and a stronger example answer for every question.
- **Downloadable report.** Save the feedback and full transcript as a Markdown file.

## How it works

1. Fill in your background and the role you're preparing for.
2. Answer the interviewer's questions in the chat.
3. Click **Get feedback** to see your evaluation, then download the report.

The live interview uses `qwen/qwen3.8-27b` for fast replies. The evaluation uses `openai/gpt-oss-120b` for more accurate grading.


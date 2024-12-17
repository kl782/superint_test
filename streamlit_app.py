import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from openai import OpenAI
import requests
import json
import asyncio
import websockets
import base64
from assemblyai import Transcriber
import assemblyai as aai
import openai
import time


# --- API Keys ---
openai_client = OpenAI(api_key = st.secrets["openai_api_key"])
# Configure AssemblyAI API
aai.settings.api_key = st.secrets["assemblyai_api_key"]
transcriber = aai.RealtimeTranscriber()

QUESTIONS = [
    "What is today's (imagined) date?",
"Is there anything about your existing work processes that you've wished could be transformed/reimagined? Any ideas yet for how?",
    "Of the tasks you did at work this week using AI, which felt most effective? Which felt least? Explicitly state the tools used for each.",
    "What are two tasks you spent the most time on this week that you didn't use AI to help with? Why didn't you use AI",
    "What are your most important work activities or goals right now, regardles of whether you used AI?",
]

WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/17695527/2sxkro8/"

# --- Names and Emails ---
NAMES = ["ADRIAN", "ALEX", "ALLISON", "ANDREW", "DANNY", "EDWARD", "ELLIS", 
         "HANNAH", "ISAIAH", "JACQUES", "JEN", "JOAQUIM", "JON", "JUAN", 
         "KARLO", "KAZ", "KRISTI", "LACEY", "MINH", "NLW", "NUFAR", "RICH", 
         "RYAN", "SCOTT"]
EMAILS = [f"{name.lower()}@besuper.ai" for name in NAMES]

def send_to_openai(text, prompt):
    """Call OpenAI API to convert text to markdown."""
    response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
         messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},])
    return response.choices[0].message.content

def send_to_webhook(data):
    """Send data to the webhook endpoint."""
    response = requests.post(WEBHOOK_URL, json=data)
    return response.status_code == 200

# Main Logic
def main():
    # --- Login ---
    st.title("AI Use Case Documentation")
    user_name = st.selectbox("Choose Your Name", NAMES)
    user_email = st.selectbox("Choose Your Email", EMAILS)
    st.success(f"Welcome, **{user_name}** ({user_email})!")

    # --- Session State Initialization ---
    if "current_question_idx" not in st.session_state:
        st.session_state.current_question_idx = 0
    if "raw_answer" not in st.session_state:
        st.session_state.raw_answer = ""
    if "markdown" not in st.session_state:
        st.session_state.markdown = ""

    current_idx = st.session_state.current_question_idx
    current_question = QUESTIONS[current_idx]

    # --- Display Current Question ---
    st.subheader(f"Question {current_idx + 1}: {current_question}")

    # --- Real-Time STT (AssemblyAI) ---
    st.info("Press 'Record' to start speaking.")
    transcriber = aai.RealtimeTranscriber()

    if st.button("Record"):
        st.write("Recording... Speak now!")
        stream = transcriber.start_stream()
        transcript = ""

        for msg in stream:
            if msg.event == "transcript":
                transcript += " " + msg.text
                st.session_state.raw_answer = transcript
                st.text_area("Live Transcript:", value=transcript, height=150)

            # Stop streaming condition
            if not st.button("Stop"):
                break
        stream.close()

    # Allow User to Edit Answer
    st.session_state.raw_answer = st.text_area("Edit Your Answer:", value=st.session_state.raw_answer, height=150)

    # --- Convert to Markdown ---
    if st.button("Convert to Markdown"):
        with st.spinner("Generating Markdown..."):
            st.session_state.markdown = send_to_openai(
                st.session_state.raw_answer,
                "Convert the following answer into a clean and professional markdown format."
            )
        st.success("Markdown Generated!")
        st.text_area("Markdown:", value=st.session_state.markdown, height=150)

    # --- Submit Response ---
    if st.button("Submit"):
        with st.spinner("Submitting your response..."):
            data = {
                "name": user_name,
                "email": user_email,
                "question": current_question,
                "raw_answer": st.session_state.raw_answer,
                "markdown": st.session_state.markdown,
            }
            success = send_to_webhook(data)

            if success:
                st.success("Response submitted successfully!")
                # Move to the next question
                st.session_state.current_question_idx += 1
                st.session_state.raw_answer = ""
                st.session_state.markdown = ""
                if st.session_state.current_question_idx >= len(QUESTIONS):
                    st.balloons()
                    st.success("All questions completed. Thank you!")
                    st.stop()
                else:
                    st.experimental_rerun()
            else:
                st.error("Failed to submit. Please try again.")

if __name__ == "__main__":
    main()








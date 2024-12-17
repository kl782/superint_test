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

QUESTIONS = [
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
selected_date = st.date_input("Select a Date")


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

def on_data_handler(data):
    st.session_state.transcribed_text += data.text + " "  # Append incoming data

def on_error_handler(error):
    st.error(f"Error during transcription: {error}")

# Create the RealtimeTranscriber instance
transcriber = aai.RealtimeTranscriber(
    on_data=on_data_handler,
    on_error=on_error_handler,
    sample_rate=16000  # Standard sample rate
)

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
    if "recording" not in st.session_state:
        st.session_state.recording = False

    current_idx = st.session_state.current_question_idx
    current_question = QUESTIONS[current_idx]

    # --- Display Current Question ---
    st.subheader(f"Question {current_idx + 1}: {current_question}")

    # --- Real-Time STT with AssemblyAI ---
    st.info("Press 'Start Recording' to begin speaking, and 'Stop' when done.")
    
    # Start/Stop Recording Buttons
    if st.button("Start Recording"):
        st.session_state.recording = True
        st.session_state.raw_answer = ""  # Clear previous answers
        st.session_state.transcribed_text = ""  # AssemblyAI output container

        # Define handlers for AssemblyAI
        def on_data_handler(data):
            st.session_state.transcribed_text += data.text + " "

        def on_error_handler(error):
            st.error(f"Error during transcription: {error}")

        # Create the transcriber
        st.session_state.transcriber = aai.RealtimeTranscriber(
            on_data=on_data_handler,
            on_error=on_error_handler,
            sample_rate=16000
        )
        st.session_state.transcriber.start()
        st.info("Recording... Speak now!")

    if st.button("Stop Recording"):
        if st.session_state.recording:
            st.session_state.transcriber.close()
            st.session_state.recording = False
            st.session_state.raw_answer = st.session_state.transcribed_text
            st.success("Recording stopped. Edit the answer if needed.")
        else:
            st.warning("Recording is not active.")

    # Display live transcription or editable answer
    if st.session_state.recording:
        st.text_area("Live Transcript:", value=st.session_state.transcribed_text, height=150)
    else:
        st.session_state.raw_answer = st.text_area("Edit Your Answer:", value=st.session_state.raw_answer, height=150)

    # --- Convert to Markdown ---
    if st.button("Convert to Markdown"):
        if st.session_state.raw_answer.strip():
            with st.spinner("Generating Markdown..."):
                st.session_state.markdown = send_to_openai(
                    st.session_state.raw_answer,
                    "Convert the following answer into a clean and professional markdown format."
                )
            st.success("Markdown Generated!")
            st.text_area("Markdown:", value=st.session_state.markdown, height=150)
        else:
            st.warning("Please provide an answer before converting to markdown.")

    # --- Submit Response ---
    if st.button("Submit"):
        if st.session_state.markdown.strip():
            with st.spinner("Submitting your response..."):
                data = {
                    "name": user_name,
                    "email": user_email,
                    "question": current_question,
                    "raw_answer": st.session_state.raw_answer,
                    "markdown": st.session_state.markdown,
                    "date": selected_date.strftime("%Y-%m-%d"),
                }
                success = send_to_webhook(data)

                if success:
                    st.success("Response submitted successfully!")
                    # Move to the next question
                    st.session_state.current_question_idx += 1
                    st.session_state.raw_answer = ""
                    st.session_state.markdown = ""
                    st.session_state.transcribed_text = ""

                    if st.session_state.current_question_idx >= len(QUESTIONS):
                        st.balloons()
                        st.success("All questions completed. Thank you!")
                        st.stop()
                    else:
                        st.experimental_rerun()
                else:
                    st.error("Failed to submit. Please try again.")
        else:
            st.warning("Generate Markdown before submitting.")

if __name__ == "__main__":
    main()









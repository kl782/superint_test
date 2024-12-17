import streamlit as st
import whisper
from io import BytesIO
from pydub import AudioSegment
from openai import OpenAI
import requests
import json

# --- API Keys ---
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])
WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/17695527/2sxkro8/"

QUESTIONS = [
    "Is there anything about your existing work processes that you've wished could be transformed/reimagined? Any ideas yet for how?",
    "Of the tasks you did at work this week using AI, which felt most effective? Which felt least? Explicitly state the tools used for each.",
    "What are two tasks you spent the most time on this week that you didn't use AI to help with? Why didn't you use AI",
    "What are your most important work activities or goals right now, regardless of whether you used AI?",
]

# --- Names and Emails ---
NAMES = ["ADRIAN", "ALEX", "ALLISON", "ANDREW", "DANNY", "EDWARD", "ELLIS",
         "HANNAH", "ISAIAH", "JACQUES", "JEN", "JOAQUIM", "JON", "JUAN",
         "KARLO", "KAZ", "KRISTI", "LACEY", "MINH", "NLW", "NUFAR", "RICH",
         "RYAN", "SCOTT"]
EMAILS = [f"{name.lower()}@besuper.ai" for name in NAMES]

# --- Load Whisper Model ---
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

model = load_whisper_model()

def send_to_openai(text, prompt):
    """Call OpenAI API to convert text to markdown."""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ]
    )
    return response.choices[0].message.content

def send_to_webhook(data):
    """Send data to the webhook endpoint."""
    response = requests.post(WEBHOOK_URL, json=data)
    return response.status_code == 200

# --- Main Function ---
def main():
    st.title("AI Use Case Documentation")

    # --- Login ---
    selected_date = st.date_input("Select a Date", key="selected_date")
    user_name = st.selectbox("Choose Your Name", NAMES, key="name_select")
    user_email = st.selectbox("Choose Your Email", EMAILS, key="email_select")
    st.success(f"Welcome, **{user_name}** ({user_email})!")

    # --- Session State Initialization ---
    if "current_question_idx" not in st.session_state:
        st.session_state.current_question_idx = 0
    if "transcribed_text" not in st.session_state:
        st.session_state.transcribed_text = ""
    if "raw_answer" not in st.session_state:
        st.session_state.raw_answer = ""
    if "markdown" not in st.session_state:
        st.session_state.markdown = ""

    # --- Display Question ---
    current_idx = st.session_state.current_question_idx
    if current_idx >= len(QUESTIONS):
        st.success("All questions completed. Thank you!")
        st.balloons()
        st.stop()
    current_question = QUESTIONS[current_idx]
    st.subheader(f"Question {current_idx + 1}: {current_question}")

    # --- Audio Recording and Transcription ---
    st.info("Record your response and upload it for transcription.")
    audio_file = st.file_uploader("Upload an audio file or record your answer.", type=["wav", "mp3", "m4a"])
    
    if audio_file:
        st.audio(audio_file, format="audio/wav", start_time=0)
        
        # Convert audio to WAV format using pydub
        audio = AudioSegment.from_file(BytesIO(audio_file.read()))
        wav_io = BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)

        # Transcribe audio using Whisper
        with st.spinner("Transcribing audio..."):
            result = model.transcribe(wav_io)
            st.session_state.transcribed_text = result["text"]
            st.success("Transcription completed!")

    # --- Transcription Display ---
    st.text_area("Transcription:", value=st.session_state.transcribed_text, height=150, key="transcription_display")

    # --- Edit Answer ---
    st.session_state.raw_answer = st.text_area(
        "Edit Your Answer:",
        value=st.session_state.transcribed_text if not st.session_state.raw_answer else st.session_state.raw_answer,
        height=150,
        key="editable_answer"
    )

    # --- Convert to Markdown ---
    if st.button("Convert to Markdown", key="convert_markdown"):
        if st.session_state.raw_answer.strip():
            with st.spinner("Generating Markdown..."):
                st.session_state.markdown = send_to_openai(
                    st.session_state.raw_answer,
                    "Convert the transcript into clear, clean markdown. Capture work tasks with great detail. If any personal details are captured, generalize them."
                )
            st.success("Markdown Generated!")
            st.text_area("Markdown:", value=st.session_state.markdown, height=150, key="markdown_output")
        else:
            st.warning("Please provide an answer before converting to markdown.")

    # --- Submit Response ---
    if st.button("Submit", key="submit_response"):
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
                    st.session_state.current_question_idx += 1
                    st.session_state.transcribed_text = ""
                    st.session_state.raw_answer = ""
                    st.session_state.markdown = ""
                    st.experimental_rerun()
                else:
                    st.error("Failed to submit. Please try again.")
        else:
            st.warning("Generate Markdown before submitting.")

if __name__ == "__main__":
    main()

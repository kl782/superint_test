import streamlit as st
import pandas as pd
import openai
import tempfile
import os
from pathlib import Path

from streamlit_webrtc import WebRtcMode, webrtc_streamer

# Set OpenAI API key
openai.api_key = st.secrets["openai_api_key"]  

# Placeholder Names and Emails
NAMES = ["ADRIAN", "ALEX", "ALLISON","ANDREW","DANNY","EDWARD","ELLIS","HANNAH","ISAIAH","JACQUES","JEN","JOAQUIM","JON","JUAN","KARLO","KAZ","KRISTI","LACEY","MINH","NLW","NUFAR","RICH","RYAN","SCOTT"]
EMAILS = [f"{name.lower()}@besuper.ai" for name in NAMES]

# ----- Function to Send to OpenAI -----
def send_to_openai(text, prompt_placeholder):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt_placeholder},
            {"role": "user", "content": text},
        ]
    )
    return response["choices"][0]["message"]["content"]

# ----- Main App Logic -----
def main():
    # ----- LOGIN PAGE -----
    st.title("AI Use Case Documentation")
    st.subheader("Log In")
    user_name = st.selectbox("Choose Your Name", NAMES)
    user_email = st.selectbox("Choose Your Email", EMAILS)
    st.success(f"Welcome, {user_name} ({user_email})!")

    # Store Responses
    session = st.session_state
    if "responses" not in session:
        session["responses"] = []

    st.write("---")

    # ----- SPEECH-TO-TEXT SECTION -----
    st.header("Real-Time Speech-to-Text")
    transcript = st.text_area("Edit your transcript:", key="transcript_area")

    # Real-Time Speech-to-Text
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": False, "audio": True},
    )
    
    # Update transcript live
    st.markdown("**Respond, and the text will appear below:**")
    transcript_box = st.empty()
    if webrtc_ctx.state.playing:
        import numpy as np
        import pydub
        from deepspeech import Model

        # Load Model (Modify for actual STT service like Deepgram)
        model_path = "path/to/deepspeech-model.pbmm"  # Update to your actual path
        model = Model(model_path)
        stream = model.createStream()

        while webrtc_ctx.state.playing:
            audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
            sound_chunk = pydub.AudioSegment.empty()
            for audio_frame in audio_frames:
                sound = pydub.AudioSegment(
                    data=audio_frame.to_ndarray().tobytes(),
                    sample_width=audio_frame.format.bytes,
                    frame_rate=audio_frame.sample_rate,
                    channels=len(audio_frame.layout.channels),
                )
                sound_chunk += sound

            if len(sound_chunk) > 0:
                buffer = np.array(sound_chunk.set_channels(1).get_array_of_samples())
                stream.feedAudioContent(buffer)
                text = stream.intermediateDecode()
                transcript_box.markdown(f"**Text:** {text}")
                session["transcript"] = text

    # Allow user to save or edit
    st.write("---")

    # ----- OPENAI API CALL -----
    if st.button("Generate Markdown"):
        st.info("Sending to OpenAI for Markdown generation...")
        markdown_response = send_to_openai(session["transcript"], "Create markdown")
        st.success("Markdown Output:")
        st.code(markdown_response)

        # Save response
        session["responses"].append({"Markdown": markdown_response})

    if st.button("Generate TSV"):
        st.info("Sending to OpenAI for TSV generation...")
        tsv_response = send_to_openai(session["transcript"], "Create a TSV")
        tsv_path = Path("transcript_output.tsv")

        # Save TSV output
        with open(tsv_path, "w") as f:
            f.write(tsv_response)
        st.success("TSV Output Saved:")
        st.download_button("Download TSV", data=tsv_path.read_text(), file_name="output.tsv")

        # Save response
        session["responses"].append({"TSV": tsv_response})

    st.write("---")

    # ----- QUESTION NAVIGATION -----
    st.header("Answer Questions")
    questions = ["What specific tasks or activities did you use AI for at work this week? Explicitly state the tools and workflows you used.", "Were you using AI to make work faster, cheaper, better or some combination?", "Which AI use felt most effective to you?","What are two tasks or activities that you spent the most time on this week, that you didn't use AI to help with?","Why didn't you use AI to help?","Regardless of whether you're using AI for them, what are your most important work activities or goals right now?"]
    current_question_idx = session.get("current_question_idx", 0)
    
    st.subheader(questions[current_question_idx])
    answer = st.text_area("Your Answer:")
    
    if st.button("Next Question"):
        if answer:
            session["responses"].append({questions[current_question_idx]: answer})
        session["current_question_idx"] = (current_question_idx + 1) % len(questions)
        st.experimental_rerun()

    st.write("---")

    # Final responses
    if st.button("Finish"):
        st.success("Your responses:")
        st.write(pd.DataFrame(session["responses"]))

if __name__ == "__main__":
    main()

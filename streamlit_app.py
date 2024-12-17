import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
import openai

# Set OpenAI API key
openai.api_key = st.secrets["openai_api_key"]

# Names and Emails
NAMES = ["ADRIAN", "ALEX", "ALLISON", "ANDREW", "DANNY", "EDWARD", "ELLIS", 
         "HANNAH", "ISAIAH", "JACQUES", "JEN", "JOAQUIM", "JON", "JUAN", 
         "KARLO", "KAZ", "KRISTI", "LACEY", "MINH", "NLW", "NUFAR", "RICH", 
         "RYAN", "SCOTT"]
EMAILS = [f"{name.lower()}@besuper.ai" for name in NAMES]

# Function to call OpenAI
def send_to_openai(text, prompt_placeholder):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt_placeholder},
            {"role": "user", "content": text},
        ]
    )
    return response["choices"][0]["message"]["content"]

# Main App Logic
def main():
    # --- Login ---
    st.title("AI Use Case Documentation")
    user_name = st.selectbox("Choose Your Name", NAMES)
    user_email = st.selectbox("Choose Your Email", EMAILS)
    st.success(f"Welcome, {user_name} ({user_email})!")

    st.write("---")

    # --- Real-Time Speech-to-Text Section ---
    st.header("Real-Time Speech-to-Text")
    st.write("Start speaking, and we'll transcribe your speech in real-time!")
    
    # Use provided STT CODE for streaming transcription
    from pathlib import Path
    from collections import deque
    import numpy as np
    import pydub
    import time
    import queue

    HERE = Path(__file__).parent
    MODEL_URL = "https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.pbmm"
    LANG_MODEL_URL = "https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.scorer"

    # Real-time STT
    from deepspeech import Model
    model_path = HERE / "models/deepspeech-0.9.3-models.pbmm"
    lang_model_path = HERE / "models/deepspeech-0.9.3-models.scorer"

    # Download if not present
    if not model_path.exists() or not lang_model_path.exists():
        st.warning("Downloading model files. Please wait...")
        download_file(MODEL_URL, model_path)
        download_file(LANG_MODEL_URL, lang_model_path)

    # Load DeepSpeech
    model = Model(str(model_path))
    model.enableExternalScorer(str(lang_model_path))

    # Start Streaming
    st.info("Listening... Speak now!")
    webrtc_ctx = webrtc_streamer(
        key="stt-demo",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"audio": True, "video": False},
    )

    transcript = st.text_area("Transcript:", "", height=200)

    if webrtc_ctx.state.playing:
        stream = model.createStream()
        while True:
            try:
                audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
                sound_chunk = pydub.AudioSegment.empty()
                for audio_frame in audio_frames:
                    sound = pydub.AudioSegment(
                        data=audio_frame.to_ndarray().tobytes(),
                        sample_width=audio_frame.format.bytes,
                        frame_rate=audio_frame.sample_rate,
                        channels=1,
                    )
                    sound_chunk += sound

                # Feed into DeepSpeech
                if len(sound_chunk) > 0:
                    buffer = np.array(sound_chunk.get_array_of_samples())
                    stream.feedAudioContent(buffer)
                    text = stream.intermediateDecode()
                    transcript = text  # Update transcript
                    st.text_area("Transcript:", transcript, height=200)

            except queue.Empty:
                continue

    # --- Send Transcript to OpenAI ---
    if st.button("Generate Markdown"):
        st.info("Sending to OpenAI...")
        markdown_output = send_to_openai(transcript, "Create markdown from this transcript")
        st.success("Markdown Output:")
        st.code(markdown_output)

    if st.button("Generate TSV"):
        st.info("Sending to OpenAI...")
        tsv_output = send_to_openai(transcript, "Convert this transcript into a .tsv file")
        tsv_path = "transcript_output.tsv"

        # Save TSV
        with open(tsv_path, "w") as f:
            f.write(tsv_output)

        st.success("TSV Ready:")
        st.download_button("Download TSV", data=tsv_output, file_name="transcript_output.tsv")

if __name__ == "__main__":
    main()

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
import openai
import requests
import json
import asyncio
import websockets
import base64

# --- API Keys ---
openai.api_key = st.secrets["openai_api_key"]
ASSEMBLYAI_API_KEY = st.secrets["assemblyai_api_key"]
ASSEMBLYAI_WS_URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

# --- Names and Emails ---
NAMES = ["ADRIAN", "ALEX", "ALLISON", "ANDREW", "DANNY", "EDWARD", "ELLIS", 
         "HANNAH", "ISAIAH", "JACQUES", "JEN", "JOAQUIM", "JON", "JUAN", 
         "KARLO", "KAZ", "KRISTI", "LACEY", "MINH", "NLW", "NUFAR", "RICH", 
         "RYAN", "SCOTT"]
EMAILS = [f"{name.lower()}@besuper.ai" for name in NAMES]

# --- OpenAI Function ---
def send_to_openai(text, prompt_placeholder):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt_placeholder},
            {"role": "user", "content": text},
        ],
    )
    return response["choices"][0]["message"]["content"]

# --- Send TSV to Webhook ---
def send_to_webhook(data, webhook_url):
    response = requests.post(webhook_url, json={"tsv_data": data})
    return response.status_code

# --- Real-Time AssemblyAI Streaming ---
async def assemblyai_stream(ws, audio_receiver, transcript_container):
    while True:
        try:
            audio_frames = audio_receiver.get_frames(timeout=1)
            for frame in audio_frames:
                audio_bytes = frame.to_ndarray().tobytes()
                encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
                await ws.send(json.dumps({"audio_data": encoded_audio}))

                # Receive and display transcription
                result = await ws.recv()
                result_json = json.loads(result)
                if "text" in result_json:
                    transcript_container.text_area(
                        "Transcript (Real-time):", result_json["text"], height=200
                    )
        except Exception:
            break

# --- Main App Logic ---
def main():
    st.title("AI Use Case Documentation")
    user_name = st.selectbox("Choose Your Name", NAMES)
    user_email = st.selectbox("Choose Your Email", EMAILS)
    st.success(f"Welcome, {user_name} ({user_email})!")

    st.write("---")
    st.header("Real-Time Speech-to-Text with Editable Markdown")

    # --- Toggle Questions ---
    question_option = st.radio("Select Task", ["Summarize as Markdown", "Create a Report Outline"])
    prompt_placeholder = (
        "Summarize this into clean and formatted markdown."
        if question_option == "Summarize as Markdown"
        else "Create a detailed report outline for the following text."
    )

    # --- Transcription ---
    st.subheader("Real-Time Transcription")
    transcript_container = st.empty()
    webrtc_ctx = webrtc_streamer(
        key="assemblyai-live",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"audio": True, "video": False},
    )

    # Real-time transcription using AssemblyAI
    if webrtc_ctx.state.playing:
        st.info("Streaming... Start speaking!")
        asyncio.run(assemblyai_realtime_transcription(transcript_container, webrtc_ctx))

    # --- Generate Markdown ---
    if st.button("Generate Markdown"):
        st.info("Sending to OpenAI...")
        transcript = transcript_container.text_area("Transcript:", height=200)
        markdown_output = send_to_openai(transcript, prompt_placeholder)

        # Editable Markdown Text Area
        st.success("Markdown Output:")
        edited_markdown = st.text_area("Edit Markdown:", markdown_output, height=300)

        # Confirmation Step
        if st.button("Confirm and Generate TSV"):
            st.info("Generating TSV...")
            tsv_output = send_to_openai(edited_markdown, "Convert this markdown into TSV format.")

            st.success("TSV Ready!")
            st.code(tsv_output)

            # Send TSV to Webhook
            webhook_url = st.text_input("Webhook URL:")
            if st.button("Send TSV to Webhook"):
                response_code = send_to_webhook(tsv_output, webhook_url)
                if response_code == 200:
                    st.success("TSV successfully sent to webhook!")
                else:
                    st.error(f"Failed to send TSV. Status code: {response_code}")

# Real-Time Transcription Function
async def assemblyai_realtime_transcription(transcript_container, webrtc_ctx):
    async with websockets.connect(
        ASSEMBLYAI_WS_URL, extra_headers={"Authorization": ASSEMBLYAI_API_KEY}
    ) as ws:
        await ws.recv()  # Initial acknowledgment
        await assemblyai_stream(ws, webrtc_ctx.audio_receiver, transcript_container)

if __name__ == "__main__":
    main()

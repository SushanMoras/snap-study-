import io
import smtplib
from email.message import EmailMessage
import streamlit as st
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT

# ---------------------------------------------------------
# Page Configuration & Visual Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="SnapStudy - AI Vision Study Buddy",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #6B7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .profile-card {
        background: #F3F4F6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4F46E5;
        margin-bottom: 1.2rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Cached Gemini Client
# ---------------------------------------------------------
@st.cache_resource
def get_gemini_client():
    """Initializes and caches the Google GenAI Client."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        return None
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------
# Email Sending Utility via Gmail SMTP
# ---------------------------------------------------------
def send_email_summary(to_email: str, student_name: str, summary_content: str):
    """Sends study notes to the student's email using Gmail SMTP SSL."""
    gmail_address = st.secrets.get("GMAIL_ADDRESS")
    gmail_password = st.secrets.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password or gmail_address == "your-email@gmail.com":
        raise ValueError(
            "Gmail credentials are not configured. Please set GMAIL_ADDRESS and "
            "GMAIL_APP_PASSWORD in `.streamlit/secrets.toml`."
        )

    msg = EmailMessage()
    msg["Subject"] = f"🎓 SnapStudy Notes & Study Summary - {student_name}"
    msg["From"] = f"SnapStudy Buddy <{gmail_address}>"
    msg["To"] = to_email
    msg.set_content(summary_content)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.send_message(msg)


# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_email" not in st.session_state:
    st.session_state.student_email = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


# ---------------------------------------------------------
# Step 1: Onboarding View
# ---------------------------------------------------------
if not st.session_state.onboarded:
    st.markdown('<div class="main-header">🎓 SnapStudy</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Your intelligent AI Vision study partner powered by Gemini & Streamlit.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("👋 Let's Get Started!")
            st.write("Enter your details below so SnapStudy can personalize your explanations and email you study summaries.")

            with st.form("onboarding_form", clear_on_submit=False):
                name_input = st.text_input("Your Name", placeholder="e.g. Alex", help="What should your study buddy call you?")
                email_input = st.text_input("Your Email Address", placeholder="e.g. alex@example.com", help="Where should we send your study summaries?")
                submit_btn = st.form_submit_button("🚀 Start Studying", use_container_width=True, type="primary")

                if submit_btn:
                    if not name_input.strip():
                        st.error("Please enter your name.")
                    elif not email_input.strip() or "@" not in email_input or "." not in email_input:
                        st.error("Please provide a valid email address.")
                    else:
                        st.session_state.student_name = name_input.strip()
                        st.session_state.student_email = email_input.strip()
                        st.session_state.onboarded = True

                        # Welcome message from SnapStudy
                        welcome_msg = WELCOME_MESSAGE_TEMPLATE.format(
                            name=st.session_state.student_name,
                            email=st.session_state.student_email
                        )
                        st.session_state.messages = [
                            {"role": "assistant", "content": welcome_msg, "image_bytes": None, "mime_type": None}
                        ]
                        st.rerun()

    # Inform about secrets if not set
    client = get_gemini_client()
    if client is None:
        st.info("💡 **Developer Notice:** Make sure to set your `GEMINI_API_KEY`, `GMAIL_ADDRESS`, and `GMAIL_APP_PASSWORD` in `.streamlit/secrets.toml`.")
    st.stop()


# ---------------------------------------------------------
# Step 2: Main Application (Chat & Vision)
# ---------------------------------------------------------
client = get_gemini_client()

# Header
st.markdown('<div class="main-header">🎓 SnapStudy Buddy</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Studying with **{st.session_state.student_name}** • Snap a problem or ask a question!</div>', unsafe_allow_html=True)

if client is None:
    st.error("⚠️ **Missing Gemini API Key!** Please configure `GEMINI_API_KEY` in `.streamlit/secrets.toml`.")
    st.stop()

# ---------------------------------------------------------
# Sidebar: Controls & Actions
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
    <div class="profile-card">
        <strong>🧑‍🎓 Student:</strong> {st.session_state.student_name}<br>
        <strong>📬 Email:</strong> {st.session_state.student_email}
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📷 Attach Study Material")
    uploaded_image = st.file_uploader(
        "Upload or snap a problem/notes photo",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"image_uploader_{st.session_state.uploader_key}",
        help="Upload diagrams, textbook pages, math formulas, or handwritten notes."
    )

    if uploaded_image is not None:
        st.image(uploaded_image, caption="Attached Image Preview", use_container_width=True)

    st.divider()

    st.subheader("📝 Session Actions")
    # Check if user has engaged in conversation (more than just the welcome message)
    has_chat_history = any(m["role"] == "user" for m in st.session_state.messages)

    email_button = st.button(
        "📧 Email Study Summary",
        disabled=not has_chat_history,
        use_container_width=True,
        type="primary",
        help="Summarize all topics and problem explanations discussed and send them to your email."
    )

    if email_button:
        with st.status("Generating and sending your study summary...", expanded=True) as status:
            st.write("🔍 Analyzing study session notes with Gemini...")
            try:
                # Build contents for summary generation
                summary_contents = []
                for msg in st.session_state.messages:
                    parts = []
                    if msg.get("image_bytes") and msg.get("mime_type"):
                        parts.append(types.Part.from_bytes(data=msg["image_bytes"], mime_type=msg["mime_type"]))
                    if msg.get("content"):
                        role_label = "Student" if msg["role"] == "user" else "SnapStudy Buddy"
                        parts.append(types.Part.from_text(text=f"{role_label}: {msg['content']}"))
                    if parts:
                        summary_contents.append(
                            types.Content(role="user" if msg["role"] == "user" else "model", parts=parts)
                        )

                # Append the summary request
                summary_contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=SUMMARY_REQUEST_PROMPT)])
                )

                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=summary_contents,
                )
                summary_text = response.text

                st.write(f"📨 Dispatching email to **{st.session_state.student_email}**...")
                send_email_summary(
                    to_email=st.session_state.student_email,
                    student_name=st.session_state.student_name,
                    summary_content=summary_text
                )
                status.update(label="✅ Study summary sent successfully!", state="complete", expanded=False)
                st.toast(f"Summary sent to {st.session_state.student_email}!", icon="🎉")
                st.success(f"📬 Summary sent to **{st.session_state.student_email}**!")
            except Exception as e:
                status.update(label="❌ Failed to send summary", state="error", expanded=True)
                st.error(f"Error: {str(e)}")

    if st.button("🔄 Reset Study Session", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE_TEMPLATE.format(
                    name=st.session_state.student_name,
                    email=st.session_state.student_email
                ),
                "image_bytes": None,
                "mime_type": None
            }
        ]
        st.session_state.uploader_key += 1
        st.rerun()

    if st.button("🚪 Change Student Profile", use_container_width=True):
        st.session_state.onboarded = False
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.rerun()


# ---------------------------------------------------------
# Chat Message Stream & History
# ---------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🎓" if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg.get("image_bytes"):
            st.image(msg["image_bytes"], caption="Attached Study Material", use_container_width=True)
        st.markdown(msg["content"])


# ---------------------------------------------------------
# Chat Input & AI Generation
# ---------------------------------------------------------
user_prompt = st.chat_input("Ask a question, explain a step, or discuss the attached image...")

if user_prompt:
    image_bytes = None
    image_mime = None
    if uploaded_image is not None:
        image_bytes = uploaded_image.getvalue()
        image_mime = uploaded_image.type

    # 1. Append user message to state and display
    user_msg_entry = {
        "role": "user",
        "content": user_prompt,
        "image_bytes": image_bytes,
        "mime_type": image_mime
    }
    st.session_state.messages.append(user_msg_entry)

    with st.chat_message("user", avatar="🧑‍🎓"):
        if image_bytes:
            st.image(image_bytes, caption="Attached Study Material", use_container_width=True)
        st.markdown(user_prompt)

    # 2. Build contents payload for Gemini API
    api_contents = []
    for msg in st.session_state.messages:
        parts = []
        if msg.get("image_bytes") and msg.get("mime_type"):
            parts.append(types.Part.from_bytes(data=msg["image_bytes"], mime_type=msg["mime_type"]))
        if msg.get("content"):
            parts.append(types.Part.from_text(text=msg["content"]))
        if parts:
            api_contents.append(
                types.Content(role="user" if msg["role"] == "user" else "model", parts=parts)
            )

    # 3. Stream assistant response
    with st.chat_message("assistant", avatar="🎓"):
        try:
            response_stream = client.models.generate_content_stream(
                model="gemini-3.5-flash-lite",
                contents=api_contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                )
            )

            full_reply = st.write_stream(
                chunk.text for chunk in response_stream if chunk.text
            )

            # Store assistant response in history
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_reply,
                "image_bytes": None,
                "mime_type": None
            })

            # Clear file uploader after sending image
            if uploaded_image is not None:
                st.session_state.uploader_key += 1
                st.rerun()

        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
